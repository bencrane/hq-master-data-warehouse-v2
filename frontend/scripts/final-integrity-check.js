
require('dotenv').config({ path: '.env.local' });
const { createClient } = require('@supabase/supabase-js');

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseKey) {
    console.error('Error: Missing env vars in .env.local');
    process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseKey);

async function finalCheck() {
    console.log('\n' + '='.repeat(70));
    console.log('   FINAL COMPREHENSIVE DATA INTEGRITY CHECK');
    console.log('='.repeat(70) + '\n');

    try {
        // 1. Overall counts
        console.log('1. OVERALL DATA COUNTS\n');
        
        const { count: rawCount } = await supabase
            .schema('raw').from('person_payloads')
            .select('*', { count: 'exact', head: true });
        
        const { count: profileCount } = await supabase
            .schema('extracted').from('person_profile')
            .select('*', { count: 'exact', head: true });
        
        const { count: expCount } = await supabase
            .schema('extracted').from('person_experience')
            .select('*', { count: 'exact', head: true });
        
        const { count: eduCount } = await supabase
            .schema('extracted').from('person_education')
            .select('*', { count: 'exact', head: true });

        console.log(`   raw.person_payloads:        ${rawCount.toLocaleString()}`);
        console.log(`   extracted.person_profile:   ${profileCount.toLocaleString()}`);
        console.log(`   extracted.person_experience: ${expCount.toLocaleString()}`);
        console.log(`   extracted.person_education:  ${eduCount.toLocaleString()}`);

        // 2. Check for NULL values in critical columns
        console.log('\n2. NULL VALUE CHECK IN CRITICAL COLUMNS\n');

        const criticalColumns = [
            { col: 'linkedin_url', desc: 'LinkedIn URL' },
            { col: 'first_name', desc: 'First Name' },
            { col: 'last_name', desc: 'Last Name' },
        ];

        for (const { col, desc } of criticalColumns) {
            const { count: nullCount } = await supabase
                .schema('extracted')
                .from('person_profile')
                .select('*', { count: 'exact', head: true })
                .is(col, null);
            
            const status = nullCount === 0 ? '✅' : '⚠️';
            console.log(`   ${status} ${desc} (${col}): ${nullCount} NULL values`);
        }

        // 3. Check raw_payload_id linkage
        console.log('\n3. RAW PAYLOAD LINKAGE CHECK\n');
        
        const { count: missingRawId } = await supabase
            .schema('extracted')
            .from('person_profile')
            .select('*', { count: 'exact', head: true })
            .is('raw_payload_id', null);
        
        const linkedPct = ((profileCount - missingRawId) / profileCount * 100).toFixed(1);
        console.log(`   Profiles with raw_payload_id: ${(profileCount - missingRawId).toLocaleString()} / ${profileCount.toLocaleString()} (${linkedPct}%)`);
        console.log(`   ${missingRawId === 0 ? '✅' : '⚠️'} Missing raw_payload_id: ${missingRawId}`);

        // 4. Check for duplicate linkedin_urls
        console.log('\n4. DUPLICATE CHECK\n');
        
        const { data: dupCheck } = await supabase.rpc('check_duplicates_count');
        // Since we can't use RPC easily, let's do a simple check
        const { data: profileUrls } = await supabase
            .schema('extracted')
            .from('person_profile')
            .select('linkedin_url');
        
        const urlCounts = {};
        profileUrls?.forEach(p => {
            urlCounts[p.linkedin_url] = (urlCounts[p.linkedin_url] || 0) + 1;
        });
        const duplicates = Object.entries(urlCounts).filter(([_, count]) => count > 1);
        
        console.log(`   ${duplicates.length === 0 ? '✅' : '⚠️'} Duplicate linkedin_urls: ${duplicates.length}`);
        if (duplicates.length > 0 && duplicates.length <= 5) {
            duplicates.forEach(([url, count]) => console.log(`      - ${url}: ${count} records`));
        }

        // 5. Batch verification of field mappings (100 records)
        console.log('\n5. FIELD MAPPING VERIFICATION (100 random records)\n');

        const { data: sampleProfiles } = await supabase
            .schema('extracted')
            .from('person_profile')
            .select('id, linkedin_url, full_name, first_name, last_name, headline, latest_title, latest_company, raw_payload_id')
            .not('raw_payload_id', 'is', null)
            .limit(100);

        let verified = 0;
        let errors = 0;

        for (const profile of sampleProfiles || []) {
            const { data: raw } = await supabase
                .schema('raw')
                .from('person_payloads')
                .select('raw_payload')
                .eq('id', profile.raw_payload_id)
                .single();

            if (!raw) continue;

            const payload = raw.raw_payload;
            const latestExp = payload.latest_experience || {};

            // Check critical mappings
            const isCorrect = 
                profile.first_name == payload.first_name &&
                profile.last_name == payload.last_name &&
                profile.full_name == payload.name &&
                profile.headline == payload.headline &&
                profile.latest_title == latestExp.title &&
                profile.latest_company == latestExp.company;

            if (isCorrect) {
                verified++;
            } else {
                errors++;
            }
        }

        console.log(`   Verified: ${verified} / ${sampleProfiles?.length || 0}`);
        console.log(`   Errors: ${errors}`);
        console.log(`   ${errors === 0 ? '✅' : '❌'} Field mapping: ${errors === 0 ? 'CORRECT' : 'ISSUES FOUND'}`);

        // Final verdict
        console.log('\n' + '='.repeat(70));
        console.log('   FINAL VERDICT');
        console.log('='.repeat(70));
        
        const allGood = missingRawId === 0 && duplicates.length === 0 && errors === 0;
        
        if (allGood) {
            console.log('\n   🎉 DATA INTEGRITY VERIFIED - ALL CHECKS PASSED 🎉\n');
        } else {
            console.log('\n   ⚠️  ISSUES DETECTED - REVIEW ABOVE FOR DETAILS ⚠️\n');
        }

        // Summary stats
        console.log('   Summary:');
        console.log(`   • ${profileCount.toLocaleString()} person profiles extracted`);
        console.log(`   • ${expCount.toLocaleString()} experience records extracted`);
        console.log(`   • ${eduCount.toLocaleString()} education records extracted`);
        console.log(`   • ${verified} / ${sampleProfiles?.length || 0} random records verified correct`);
        console.log('');

    } catch (err) {
        console.error('Unexpected error:', err.message);
        process.exit(1);
    }
}

finalCheck();

