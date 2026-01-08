
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
    console.log('\n=== Investigating Recent Person Profile Ingest ===\n');
    console.log(`Current time: ${new Date().toISOString()}\n`);

    try {
        // Get total counts
        const { count: totalRawCount } = await supabase
            .schema('raw')
            .from('person_payloads')
            .select('*', { count: 'exact', head: true });

        const { count: totalProfileCount } = await supabase
            .schema('extracted')
            .from('person_profile')
            .select('*', { count: 'exact', head: true });

        const { count: totalExpCount } = await supabase
            .schema('extracted')
            .from('person_experience')
            .select('*', { count: 'exact', head: true });

        const { count: totalEduCount } = await supabase
            .schema('extracted')
            .from('person_education')
            .select('*', { count: 'exact', head: true });

        console.log('=== TOTAL COUNTS ===');
        console.log(`raw.person_payloads: ${totalRawCount}`);
        console.log(`extracted.person_profile: ${totalProfileCount}`);
        console.log(`extracted.person_experience: ${totalExpCount}`);
        console.log(`extracted.person_education: ${totalEduCount}`);

        // Get records from today (Jan 7, 2026)
        const todayStart = '2026-01-07T00:00:00.000Z';
        
        const { data: recentRaw, error: rawError } = await supabase
            .schema('raw')
            .from('person_payloads')
            .select('id, linkedin_url, created_at')
            .gte('created_at', todayStart)
            .order('created_at', { ascending: false });

        if (rawError) {
            console.error('Error fetching recent raw:', rawError);
            return;
        }

        const { data: recentProfiles, error: profileError } = await supabase
            .schema('extracted')
            .from('person_profile')
            .select('id, linkedin_url, full_name, raw_payload_id, created_at, updated_at')
            .gte('updated_at', todayStart)
            .order('updated_at', { ascending: false });

        if (profileError) {
            console.error('Error fetching recent profiles:', profileError);
            return;
        }

        console.log(`\n=== RECORDS FROM TODAY (${todayStart}) ===`);
        console.log(`New raw payloads today: ${recentRaw?.length || 0}`);
        console.log(`Profiles created/updated today: ${recentProfiles?.length || 0}`);

        if (recentRaw && recentRaw.length > 0) {
            console.log(`\nFirst 10 recent raw payloads:`);
            recentRaw.slice(0, 10).forEach(r => {
                console.log(`  - ${r.linkedin_url} | ${r.created_at}`);
            });
            
            if (recentRaw.length > 10) {
                console.log(`  ... and ${recentRaw.length - 10} more`);
            }

            // Time range
            const timestamps = recentRaw.map(r => new Date(r.created_at));
            const earliest = new Date(Math.min(...timestamps));
            const latest = new Date(Math.max(...timestamps));
            console.log(`\nTime range of today's raw payloads:`);
            console.log(`  Earliest: ${earliest.toISOString()}`);
            console.log(`  Latest: ${latest.toISOString()}`);
        }

        // Check for orphans in today's data
        if (recentRaw && recentRaw.length > 0) {
            const recentRawUrls = new Set(recentRaw.map(r => r.linkedin_url));
            const recentProfileUrls = new Set(recentProfiles?.map(p => p.linkedin_url) || []);
            
            const todayOrphans = [...recentRawUrls].filter(url => !recentProfileUrls.has(url));
            
            console.log(`\n=== ORPHAN CHECK (Today's Records) ===`);
            console.log(`Raw payloads without extracted profiles: ${todayOrphans.length}`);
            
            if (todayOrphans.length > 0 && todayOrphans.length <= 20) {
                console.log(`Orphaned URLs:`);
                todayOrphans.forEach(url => console.log(`  - ${url}`));
            } else if (todayOrphans.length > 20) {
                console.log(`First 20 orphaned URLs:`);
                todayOrphans.slice(0, 20).forEach(url => console.log(`  - ${url}`));
                console.log(`  ... and ${todayOrphans.length - 20} more`);
            }
        }

        // Overall orphan check
        console.log(`\n=== OVERALL ORPHAN CHECK ===`);
        const { data: allRaw } = await supabase
            .schema('raw')
            .from('person_payloads')
            .select('linkedin_url');
        
        const { data: allProfiles } = await supabase
            .schema('extracted')
            .from('person_profile')
            .select('linkedin_url');

        if (allRaw && allProfiles) {
            const allRawUrls = new Set(allRaw.map(r => r.linkedin_url));
            const allProfileUrls = new Set(allProfiles.map(p => p.linkedin_url));
            
            const totalOrphans = [...allRawUrls].filter(url => !allProfileUrls.has(url));
            console.log(`Total orphaned linkedin_urls (raw exists, no profile): ${totalOrphans.length}`);
        }

    } catch (err) {
        console.error('Unexpected error:', err.message);
        process.exit(1);
    }
}

investigate();

