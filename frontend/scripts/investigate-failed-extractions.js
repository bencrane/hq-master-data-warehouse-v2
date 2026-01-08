
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

async function investigate() {
    console.log('\n=== Investigating Failed Extractions ===\n');

    try {
        for (const url of ORPHANED_URLS) {
            console.log(`\n--- ${url} ---`);
            
            // Get raw payload
            const { data: rawRecords, error: rawError } = await supabase
                .schema('raw')
                .from('person_payloads')
                .select('id, linkedin_url, workflow_slug, raw_payload, created_at')
                .eq('linkedin_url', url)
                .order('created_at', { ascending: false })
                .limit(1);

            if (rawError) {
                console.log(`  Error fetching: ${rawError.message}`);
                continue;
            }

            if (!rawRecords || rawRecords.length === 0) {
                console.log(`  No raw payload found`);
                continue;
            }

            const raw = rawRecords[0];
            const payload = raw.raw_payload;

            console.log(`  Raw ID: ${raw.id}`);
            console.log(`  Created: ${raw.created_at}`);
            
            // Check key fields that extraction needs
            const keyFields = [
                'slug',
                'profile_id', 
                'first_name',
                'last_name',
                'name',
                'headline',
                'summary',
                'country',
                'location_name',
                'connections',
                'num_followers',
                'picture_url_orig',
                'picture_url_copy',
                'jobs_count',
                'latest_experience',
                'experience',
                'education',
                'last_refresh',
            ];

            console.log(`  \n  Key field analysis:`);
            for (const field of keyFields) {
                const value = payload[field];
                const valueType = value === null ? 'NULL' : 
                                  value === undefined ? 'UNDEFINED' :
                                  Array.isArray(value) ? `Array(${value.length})` :
                                  typeof value === 'object' ? 'Object' :
                                  typeof value;
                const preview = value === null ? 'null' :
                               value === undefined ? 'undefined' :
                               Array.isArray(value) ? `[${value.length} items]` :
                               typeof value === 'object' ? JSON.stringify(value).substring(0, 50) + '...' :
                               String(value).substring(0, 50);
                
                // Flag potential issues
                const issue = (value === null || value === undefined) ? ' ⚠️' : '';
                console.log(`    ${field}: ${valueType}${issue} = ${preview}`);
            }

            // Check if latest_experience has required fields
            if (payload.latest_experience) {
                console.log(`  \n  latest_experience details:`);
                const le = payload.latest_experience;
                ['title', 'company', 'company_domain', 'url', 'org_id', 'locality', 'start_date', 'is_current'].forEach(f => {
                    const v = le[f];
                    const issue = (v === null || v === undefined) ? ' ⚠️' : '';
                    console.log(`    ${f}: ${v === null ? 'NULL' : v === undefined ? 'UNDEFINED' : v}${issue}`);
                });
            }
        }

    } catch (err) {
        console.error('Unexpected error:', err.message);
        process.exit(1);
    }
}

investigate();

