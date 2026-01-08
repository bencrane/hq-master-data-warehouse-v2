
require('dotenv').config({ path: '.env.local' });
const { createClient } = require('@supabase/supabase-js');

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseKey) {
    console.error('Error: Missing env vars in .env.local');
    process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseKey);

async function checkOrphans() {
    console.log('\n=== Checking for Orphaned Records ===\n');

    try {
        // Get all raw payloads
        const { data: rawPayloads, error: rawError } = await supabase
            .schema('raw')
            .from('person_payloads')
            .select('id, linkedin_url, created_at')
            .order('created_at', { ascending: true });

        if (rawError) {
            console.error('Error fetching raw payloads:', rawError);
            return;
        }

        // Get all extracted profiles
        const { data: profiles, error: profileError } = await supabase
            .schema('extracted')
            .from('person_profile')
            .select('id, linkedin_url, raw_payload_id, created_at');

        if (profileError) {
            console.error('Error fetching profiles:', profileError);
            return;
        }

        // Create a set of linkedin_urls that have extracted profiles
        const profileLinkedInUrls = new Set(profiles.map(p => p.linkedin_url));
        const profileRawPayloadIds = new Set(profiles.map(p => p.raw_payload_id).filter(Boolean));

        // Find orphaned raw payloads (no corresponding extracted profile)
        const orphanedByUrl = rawPayloads.filter(r => !profileLinkedInUrls.has(r.linkedin_url));
        const orphanedByRawId = rawPayloads.filter(r => !profileRawPayloadIds.has(r.id));

        console.log(`Total raw payloads: ${rawPayloads.length}`);
        console.log(`Total extracted profiles: ${profiles.length}`);
        console.log(`\nOrphaned raw payloads (no matching linkedin_url in profiles): ${orphanedByUrl.length}`);
        
        if (orphanedByUrl.length > 0) {
            console.log('\nOrphaned records by linkedin_url:');
            orphanedByUrl.forEach(r => {
                console.log(`  - ${r.linkedin_url} | created: ${r.created_at}`);
            });

            // Show time range of orphaned records
            const timestamps = orphanedByUrl.map(r => new Date(r.created_at));
            const earliest = new Date(Math.min(...timestamps));
            const latest = new Date(Math.max(...timestamps));
            console.log(`\nOrphaned records time range:`);
            console.log(`  Earliest: ${earliest.toISOString()}`);
            console.log(`  Latest: ${latest.toISOString()}`);
        }

        // Show earliest and latest records overall
        if (rawPayloads.length > 0) {
            console.log('\n--- Overall Data Timeline ---');
            console.log(`First record: ${rawPayloads[0].linkedin_url} | ${rawPayloads[0].created_at}`);
            console.log(`Last record: ${rawPayloads[rawPayloads.length - 1].linkedin_url} | ${rawPayloads[rawPayloads.length - 1].created_at}`);
        }

        // Check for Douglas Hanna specifically
        console.log('\n--- Checking for Douglas Hanna ---');
        const douglasRaw = rawPayloads.filter(r => r.linkedin_url.toLowerCase().includes('douglas') || r.linkedin_url.toLowerCase().includes('hanna'));
        const douglasProfile = profiles.filter(p => p.linkedin_url.toLowerCase().includes('douglas') || p.linkedin_url.toLowerCase().includes('hanna'));
        
        console.log(`Douglas Hanna in raw payloads: ${douglasRaw.length}`);
        if (douglasRaw.length > 0) {
            douglasRaw.forEach(r => console.log(`  - ${r.linkedin_url} | ${r.created_at}`));
        }
        
        console.log(`Douglas Hanna in profiles: ${douglasProfile.length}`);
        if (douglasProfile.length > 0) {
            douglasProfile.forEach(p => console.log(`  - ${p.linkedin_url} | ${p.created_at}`));
        }

    } catch (err) {
        console.error('Unexpected error:', err.message);
        process.exit(1);
    }
}

checkOrphans();

