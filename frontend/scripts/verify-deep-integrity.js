
require('dotenv').config({ path: '.env.local' });
const { createClient } = require('@supabase/supabase-js');

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseKey) {
    console.error('Error: Missing env vars in .env.local');
    process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseKey);

async function deepVerify() {
    console.log('\n=== DEEP INTEGRITY VERIFICATION ===\n');

    try {
        // Get random sample from entire dataset
        const { data: allProfiles, error: profileError } = await supabase
            .schema('extracted')
            .from('person_profile')
            .select('id, linkedin_url, full_name, raw_payload_id, created_at')
            .not('raw_payload_id', 'is', null)
            .limit(100);

        if (profileError) {
            console.error('Error:', profileError);
            return;
        }

        // Randomly sample 30 profiles
        const shuffled = allProfiles.sort(() => 0.5 - Math.random());
        const sample = shuffled.slice(0, 30);

        console.log(`Deep checking ${sample.length} random profiles across all data...\n`);

        let passCount = 0;
        let failCount = 0;
        let criticalFailures = [];

        for (const profile of sample) {
            // Get full profile
            const { data: fullProfile } = await supabase
                .schema('extracted')
                .from('person_profile')
                .select('*')
                .eq('id', profile.id)
                .single();

            // Get raw payload
            const { data: rawRecord } = await supabase
                .schema('raw')
                .from('person_payloads')
                .select('raw_payload, linkedin_url')
                .eq('id', fullProfile.raw_payload_id)
                .single();

            if (!rawRecord) {
                console.log(`⚠️  Missing raw payload for ${fullProfile.linkedin_url}`);
                continue;
            }

            const payload = rawRecord.raw_payload;
            const latestExp = payload.latest_experience || {};

            // Critical field checks
            const criticalChecks = [
                { name: 'first_name', profile: fullProfile.first_name, payload: payload.first_name },
                { name: 'last_name', profile: fullProfile.last_name, payload: payload.last_name },
                { name: 'full_name', profile: fullProfile.full_name, payload: payload.name },
                { name: 'headline', profile: fullProfile.headline, payload: payload.headline },
                { name: 'country', profile: fullProfile.country, payload: payload.country },
                { name: 'location_name', profile: fullProfile.location_name, payload: payload.location_name },
                { name: 'latest_title', profile: fullProfile.latest_title, payload: latestExp.title },
                { name: 'latest_company', profile: fullProfile.latest_company, payload: latestExp.company },
            ];

            let allMatch = true;
            const mismatches = [];

            for (const check of criticalChecks) {
                const pVal = check.profile === null || check.profile === undefined ? null : check.profile;
                const rVal = check.payload === null || check.payload === undefined ? null : check.payload;
                
                if (pVal != rVal) {
                    allMatch = false;
                    mismatches.push(`${check.name}: "${pVal}" ≠ "${rVal}"`);
                }
            }

            if (allMatch) {
                passCount++;
                console.log(`✅ ${fullProfile.full_name}`);
            } else {
                failCount++;
                console.log(`❌ ${fullProfile.full_name}`);
                mismatches.forEach(m => console.log(`   ${m}`));
                criticalFailures.push({ name: fullProfile.full_name, mismatches });
            }
        }

        // Verify experience counts across sample
        console.log('\n=== Experience Count Verification ===\n');
        
        let expMatchCount = 0;
        let expMismatchCount = 0;

        for (const profile of sample.slice(0, 10)) {
            const { data: fullProfile } = await supabase
                .schema('extracted')
                .from('person_profile')
                .select('linkedin_url, full_name, raw_payload_id')
                .eq('id', profile.id)
                .single();

            const { data: rawRecord } = await supabase
                .schema('raw')
                .from('person_payloads')
                .select('raw_payload')
                .eq('id', fullProfile.raw_payload_id)
                .single();

            const { count: expCount } = await supabase
                .schema('extracted')
                .from('person_experience')
                .select('*', { count: 'exact', head: true })
                .eq('linkedin_url', fullProfile.linkedin_url);

            const payloadExpCount = rawRecord?.raw_payload?.experience?.length || 0;

            if (expCount === payloadExpCount) {
                expMatchCount++;
                console.log(`✅ ${fullProfile.full_name}: ${expCount} experiences`);
            } else {
                expMismatchCount++;
                console.log(`❌ ${fullProfile.full_name}: extracted ${expCount} vs raw ${payloadExpCount}`);
            }
        }

        // Final summary
        console.log('\n' + '='.repeat(60));
        console.log('DEEP VERIFICATION SUMMARY');
        console.log('='.repeat(60));
        console.log(`\nProfile Field Mapping:`);
        console.log(`  Checked: ${passCount + failCount}`);
        console.log(`  ✅ Correct: ${passCount}`);
        console.log(`  ❌ Mismatched: ${failCount}`);
        
        console.log(`\nExperience Record Counts:`);
        console.log(`  Checked: ${expMatchCount + expMismatchCount}`);
        console.log(`  ✅ Correct: ${expMatchCount}`);
        console.log(`  ❌ Mismatched: ${expMismatchCount}`);

        if (failCount === 0 && expMismatchCount === 0) {
            console.log('\n🎉 DEEP VERIFICATION PASSED - DATA INTEGRITY CONFIRMED 🎉');
        } else {
            console.log('\n⚠️  ISSUES DETECTED - INVESTIGATE IMMEDIATELY');
            if (criticalFailures.length > 0) {
                console.log('\nCritical failures:');
                criticalFailures.forEach(f => {
                    console.log(`  - ${f.name}: ${f.mismatches.join(', ')}`);
                });
            }
        }

    } catch (err) {
        console.error('Unexpected error:', err.message);
        process.exit(1);
    }
}

deepVerify();

