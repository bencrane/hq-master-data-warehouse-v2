
require('dotenv').config({ path: '.env.local' });
const { createClient } = require('@supabase/supabase-js');

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseKey) {
    console.error('Error: Missing env vars in .env.local');
    process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseKey);

async function investigate() {
    console.log('\n=== Investigating Person Data ===\n');

    try {
        // Check raw.person_payloads
        console.log('--- raw.person_payloads ---');
        const { data: rawPayloads, error: rawError } = await supabase
            .schema('raw')
            .from('person_payloads')
            .select('id, linkedin_url, workflow_slug, created_at')
            .order('created_at', { ascending: false })
            .limit(20);

        if (rawError) {
            console.error('Error:', rawError);
        } else {
            console.log(`Found ${rawPayloads?.length || 0} recent raw payloads:`);
            rawPayloads?.forEach(r => {
                console.log(`  - ${r.linkedin_url} | ${r.workflow_slug} | ${r.created_at}`);
            });
        }

        // Check extracted.person_profile
        console.log('\n--- extracted.person_profile ---');
        const { data: profiles, error: profileError } = await supabase
            .schema('extracted')
            .from('person_profile')
            .select('id, linkedin_url, full_name, created_at, updated_at')
            .order('updated_at', { ascending: false })
            .limit(20);

        if (profileError) {
            console.error('Error:', profileError);
        } else {
            console.log(`Found ${profiles?.length || 0} recent profiles:`);
            profiles?.forEach(r => {
                console.log(`  - ${r.full_name || 'N/A'} | ${r.linkedin_url} | updated: ${r.updated_at}`);
            });
        }

        // Total counts
        console.log('\n--- Total Counts ---');
        const { count: rawCount } = await supabase
            .schema('raw')
            .from('person_payloads')
            .select('*', { count: 'exact', head: true });
        console.log(`Total raw.person_payloads: ${rawCount}`);

        const { count: profileCount } = await supabase
            .schema('extracted')
            .from('person_profile')
            .select('*', { count: 'exact', head: true });
        console.log(`Total extracted.person_profile: ${profileCount}`);

        const { count: expCount } = await supabase
            .schema('extracted')
            .from('person_experience')
            .select('*', { count: 'exact', head: true });
        console.log(`Total extracted.person_experience: ${expCount}`);

        const { count: eduCount } = await supabase
            .schema('extracted')
            .from('person_education')
            .select('*', { count: 'exact', head: true });
        console.log(`Total extracted.person_education: ${eduCount}`);

    } catch (err) {
        console.error('Unexpected error:', err.message);
        process.exit(1);
    }
}

investigate();

