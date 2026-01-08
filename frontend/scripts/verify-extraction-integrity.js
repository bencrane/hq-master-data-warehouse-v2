
require('dotenv').config({ path: '.env.local' });
const { createClient } = require('@supabase/supabase-js');

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseKey) {
    console.error('Error: Missing env vars in .env.local');
    process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseKey);

async function verifyExtraction() {
    console.log('\n=== MISSION CRITICAL: Verifying Extraction Data Integrity ===\n');

    try {
        // Get recent successful extractions from today
        const todayStart = '2026-01-07T00:00:00.000Z';
        
        const { data: recentProfiles, error: profileError } = await supabase
            .schema('extracted')
            .from('person_profile')
            .select('*')
            .gte('updated_at', todayStart)
            .order('updated_at', { ascending: false })
            .limit(20);

        if (profileError) {
            console.error('Error fetching profiles:', profileError);
            return;
        }

        console.log(`Checking ${recentProfiles.length} recently extracted profiles...\n`);

        let passCount = 0;
        let failCount = 0;
        const failures = [];

        for (const profile of recentProfiles) {
            // Get the raw payload for this profile
            const { data: rawRecords, error: rawError } = await supabase
                .schema('raw')
                .from('person_payloads')
                .select('raw_payload')
                .eq('id', profile.raw_payload_id)
                .maybeSingle();

            if (rawError || !rawRecords) {
                console.log(`⚠️  Cannot find raw payload for profile: ${profile.linkedin_url}`);
                continue;
            }

            const payload = rawRecords.raw_payload;
            const latestExp = payload.latest_experience || {};

            // Define field mappings: [profile_column, expected_value_from_payload]
            const checks = [
                ['linkedin_url', profile.linkedin_url, payload.linkedin_url || profile.linkedin_url],
                ['linkedin_slug', profile.linkedin_slug, payload.slug],
                ['linkedin_profile_id', profile.linkedin_profile_id, payload.profile_id],
                ['first_name', profile.first_name, payload.first_name],
                ['last_name', profile.last_name, payload.last_name],
                ['full_name', profile.full_name, payload.name],
                ['headline', profile.headline, payload.headline],
                ['summary', profile.summary, payload.summary],
                ['country', profile.country, payload.country],
                ['location_name', profile.location_name, payload.location_name],
                ['connections', profile.connections, payload.connections],
                ['num_followers', profile.num_followers, payload.num_followers],
                ['picture_url', profile.picture_url, payload.picture_url_orig || payload.picture_url_copy],
                ['jobs_count', profile.jobs_count, payload.jobs_count],
                // Latest experience fields
                ['latest_title', profile.latest_title, latestExp.title],
                ['latest_company', profile.latest_company, latestExp.company],
                ['latest_company_domain', profile.latest_company_domain, latestExp.company_domain],
                ['latest_company_linkedin_url', profile.latest_company_linkedin_url, latestExp.url],
                ['latest_company_org_id', profile.latest_company_org_id, latestExp.org_id],
                ['latest_locality', profile.latest_locality, latestExp.locality],
                ['latest_is_current', profile.latest_is_current, latestExp.is_current],
            ];

            let profilePassed = true;
            const profileFailures = [];

            for (const [column, actual, expected] of checks) {
                // Normalize for comparison (handle null/undefined, trim strings)
                const normalizedActual = actual === null || actual === undefined ? null : actual;
                const normalizedExpected = expected === null || expected === undefined ? null : expected;

                // Compare (be lenient with type coercion for numbers)
                let match = normalizedActual == normalizedExpected;
                
                // Special handling for strings - trim and compare
                if (typeof normalizedActual === 'string' && typeof normalizedExpected === 'string') {
                    match = normalizedActual.trim() === normalizedExpected.trim();
                }

                if (!match) {
                    profilePassed = false;
                    profileFailures.push({
                        column,
                        actual: normalizedActual,
                        expected: normalizedExpected
                    });
                }
            }

            if (profilePassed) {
                passCount++;
                console.log(`✅ PASS: ${profile.full_name} (${profile.linkedin_url})`);
            } else {
                failCount++;
                console.log(`❌ FAIL: ${profile.full_name} (${profile.linkedin_url})`);
                profileFailures.forEach(f => {
                    console.log(`   ${f.column}: got "${f.actual}" | expected "${f.expected}"`);
                });
                failures.push({ profile: profile.linkedin_url, failures: profileFailures });
            }
        }

        // Verify experience records
        console.log('\n=== Verifying Experience Records ===\n');
        
        const sampleProfile = recentProfiles[0];
        if (sampleProfile) {
            const { data: rawForExp } = await supabase
                .schema('raw')
                .from('person_payloads')
                .select('raw_payload')
                .eq('id', sampleProfile.raw_payload_id)
                .single();

            const { data: experiences } = await supabase
                .schema('extracted')
                .from('person_experience')
                .select('*')
                .eq('linkedin_url', sampleProfile.linkedin_url)
                .order('experience_order', { ascending: true });

            const payloadExperiences = rawForExp?.raw_payload?.experience || [];

            console.log(`Sample: ${sampleProfile.full_name}`);
            console.log(`  Raw payload experiences: ${payloadExperiences.length}`);
            console.log(`  Extracted experiences: ${experiences?.length || 0}`);

            if (payloadExperiences.length === experiences?.length) {
                console.log('  ✅ Experience count matches');
                
                // Spot check first experience
                if (experiences.length > 0 && payloadExperiences.length > 0) {
                    const exp = experiences[0];
                    const rawExp = payloadExperiences[0];
                    console.log(`\n  First experience comparison:`);
                    console.log(`    Title: "${exp.title}" vs "${rawExp.title}" → ${exp.title === rawExp.title ? '✅' : '❌'}`);
                    console.log(`    Company: "${exp.company}" vs "${rawExp.company}" → ${exp.company === rawExp.company ? '✅' : '❌'}`);
                    console.log(`    is_current: ${exp.is_current} vs ${rawExp.is_current} → ${exp.is_current === rawExp.is_current ? '✅' : '❌'}`);
                }
            } else {
                console.log('  ❌ Experience count MISMATCH');
            }
        }

        // Verify education records
        console.log('\n=== Verifying Education Records ===\n');
        
        if (sampleProfile) {
            const { data: rawForEdu } = await supabase
                .schema('raw')
                .from('person_payloads')
                .select('raw_payload')
                .eq('id', sampleProfile.raw_payload_id)
                .single();

            const { data: educations } = await supabase
                .schema('extracted')
                .from('person_education')
                .select('*')
                .eq('linkedin_url', sampleProfile.linkedin_url)
                .order('education_order', { ascending: true });

            const payloadEducations = rawForEdu?.raw_payload?.education || [];

            console.log(`Sample: ${sampleProfile.full_name}`);
            console.log(`  Raw payload educations: ${payloadEducations.length}`);
            console.log(`  Extracted educations: ${educations?.length || 0}`);

            if (payloadEducations.length === educations?.length) {
                console.log('  ✅ Education count matches');
                
                // Spot check first education
                if (educations.length > 0 && payloadEducations.length > 0) {
                    const edu = educations[0];
                    const rawEdu = payloadEducations[0];
                    console.log(`\n  First education comparison:`);
                    console.log(`    School: "${edu.school_name}" vs "${rawEdu.school_name}" → ${edu.school_name === rawEdu.school_name ? '✅' : '❌'}`);
                    console.log(`    Degree: "${edu.degree}" vs "${rawEdu.degree}" → ${edu.degree === rawEdu.degree ? '✅' : '❌'}`);
                }
            } else {
                console.log('  ❌ Education count MISMATCH');
            }
        }

        // Final summary
        console.log('\n' + '='.repeat(60));
        console.log('FINAL SUMMARY');
        console.log('='.repeat(60));
        console.log(`Profiles checked: ${recentProfiles.length}`);
        console.log(`✅ Passed: ${passCount}`);
        console.log(`❌ Failed: ${failCount}`);
        
        if (failCount === 0) {
            console.log('\n🎉 ALL EXTRACTIONS VERIFIED CORRECT 🎉');
        } else {
            console.log('\n⚠️  EXTRACTION ISSUES DETECTED - SEE ABOVE FOR DETAILS');
        }

    } catch (err) {
        console.error('Unexpected error:', err.message);
        process.exit(1);
    }
}

verifyExtraction();

