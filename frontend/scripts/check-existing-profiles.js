
require('dotenv').config({ path: '.env.local' });
const { createClient } = require('@supabase/supabase-js');

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseKey) {
    console.error('Error: Missing env vars in .env.local');
    process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseKey);

const ORPHANED_URLS = [
    'https://www.linkedin.com/in/liberty-landes-005528213/',
    'https://www.linkedin.com/in/zebankaiser/',
    'https://www.linkedin.com/in/patricia-vaughan-cpa-a1305013/',
    'https://www.linkedin.com/in/dandrehart/',
    'https://www.linkedin.com/in/sydney-russell-a50723191/',
    'https://www.linkedin.com/in/matthew-keeling-04a17614/',
    'https://www.linkedin.com/in/robbie-payton-031354a6/',
    'https://www.linkedin.com/in/matt-ladrech-a9a853b8/',
    'https://www.linkedin.com/in/madison-noland-462585197/',
    'https://www.linkedin.com/in/josue-d-086614186/',
    'https://www.linkedin.com/in/rayfield-golden-jr-cnp-0412a2103/',
    'https://www.linkedin.com/in/ronald-stephen-young/',
    'https://www.linkedin.com/in/tprouhana/',
    'https://www.linkedin.com/in/📸alejandro-gonzalez-313b9916a/',
    'https://www.linkedin.com/in/jackson-peterson-91789a18b/',
    'https://www.linkedin.com/in/marla-szczepaniec-086a4514/',
];

async function check() {
    console.log('\n=== Checking if "Orphaned" URLs Have Existing Profiles ===\n');

    try {
        let existingCount = 0;
        let trueOrphans = [];

        for (const url of ORPHANED_URLS) {
            const { data: profile, error } = await supabase
                .schema('extracted')
                .from('person_profile')
                .select('id, linkedin_url, full_name, source_last_refresh, created_at, updated_at')
                .eq('linkedin_url', url)
                .maybeSingle();

            if (error) {
                console.log(`  Error checking ${url}: ${error.message}`);
                continue;
            }

            if (profile) {
                existingCount++;
                console.log(`✅ PROFILE EXISTS: ${url}`);
                console.log(`   Name: ${profile.full_name}`);
                console.log(`   Created: ${profile.created_at}`);
                console.log(`   Updated: ${profile.updated_at}`);
                console.log(`   source_last_refresh: ${profile.source_last_refresh}`);
                console.log('');
            } else {
                trueOrphans.push(url);
                console.log(`❌ NO PROFILE: ${url}`);
            }
        }

        console.log('\n=== SUMMARY ===');
        console.log(`URLs checked: ${ORPHANED_URLS.length}`);
        console.log(`Profiles already exist (not orphans): ${existingCount}`);
        console.log(`True orphans (no profile at all): ${trueOrphans.length}`);
        
        if (trueOrphans.length > 0) {
            console.log('\nTrue orphans:');
            trueOrphans.forEach(url => console.log(`  - ${url}`));
        }

    } catch (err) {
        console.error('Unexpected error:', err.message);
        process.exit(1);
    }
}

check();

