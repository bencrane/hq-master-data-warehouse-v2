
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
    const now = new Date().toISOString();
    console.log(`\n=== DATABASE INVESTIGATION ===`);
    console.log(`Query executed at: ${now}\n`);

    try {
        // EXACT COUNTS - no estimation
        console.log('--- EXACT CURRENT COUNTS ---\n');
        
        const { count: rawCount, error: rawErr } = await supabase
            .schema('raw')
            .from('person_payloads')
            .select('*', { count: 'exact', head: true });
        
        const { count: profileCount, error: profErr } = await supabase
            .schema('extracted')
            .from('person_profile')
            .select('*', { count: 'exact', head: true });
        
        const { count: expCount, error: expErr } = await supabase
            .schema('extracted')
            .from('person_experience')
            .select('*', { count: 'exact', head: true });
        
        const { count: eduCount, error: eduErr } = await supabase
            .schema('extracted')
            .from('person_education')
            .select('*', { count: 'exact', head: true });

        if (rawErr || profErr || expErr || eduErr) {
            console.log('ERROR fetching counts:', rawErr || profErr || expErr || eduErr);
            return;
        }

        console.log(`raw.person_payloads:         ${rawCount}`);
        console.log(`extracted.person_profile:    ${profileCount}`);
        console.log(`extracted.person_experience: ${expCount}`);
        console.log(`extracted.person_education:  ${eduCount}`);

        // MOST RECENT RAW PAYLOADS
        console.log('\n--- 10 MOST RECENT RAW PAYLOADS ---\n');
        
        const { data: recentRaw, error: recentRawErr } = await supabase
            .schema('raw')
            .from('person_payloads')
            .select('id, linkedin_url, created_at')
            .order('created_at', { ascending: false })
            .limit(10);

        if (recentRawErr) {
            console.log('ERROR:', recentRawErr);
        } else {
            recentRaw.forEach((r, i) => {
                console.log(`${i + 1}. ${r.created_at} | ${r.linkedin_url}`);
            });
        }

        // MOST RECENT EXTRACTED PROFILES
        console.log('\n--- 10 MOST RECENT EXTRACTED PROFILES ---\n');
        
        const { data: recentProfiles, error: recentProfErr } = await supabase
            .schema('extracted')
            .from('person_profile')
            .select('id, linkedin_url, full_name, updated_at')
            .order('updated_at', { ascending: false })
            .limit(10);

        if (recentProfErr) {
            console.log('ERROR:', recentProfErr);
        } else {
            recentProfiles.forEach((p, i) => {
                console.log(`${i + 1}. ${p.updated_at} | ${p.full_name} | ${p.linkedin_url}`);
            });
        }

        // TIME RANGE OF TODAY'S DATA
        console.log('\n--- RECORDS FROM TODAY (Jan 7, 2026) ---\n');
        
        const todayStart = '2026-01-07T00:00:00.000Z';
        
        const { count: todayRawCount } = await supabase
            .schema('raw')
            .from('person_payloads')
            .select('*', { count: 'exact', head: true })
            .gte('created_at', todayStart);

        const { count: todayProfileCount } = await supabase
            .schema('extracted')
            .from('person_profile')
            .select('*', { count: 'exact', head: true })
            .gte('updated_at', todayStart);

        console.log(`Raw payloads received today:     ${todayRawCount}`);
        console.log(`Profiles created/updated today:  ${todayProfileCount}`);

        // LAST HOUR breakdown
        console.log('\n--- LAST HOUR BREAKDOWN ---\n');
        
        const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000).toISOString();
        
        const { count: lastHourRaw } = await supabase
            .schema('raw')
            .from('person_payloads')
            .select('*', { count: 'exact', head: true })
            .gte('created_at', oneHourAgo);

        const { count: lastHourProfiles } = await supabase
            .schema('extracted')
            .from('person_profile')
            .select('*', { count: 'exact', head: true })
            .gte('updated_at', oneHourAgo);

        console.log(`Raw payloads in last hour:       ${lastHourRaw}`);
        console.log(`Profiles updated in last hour:   ${lastHourProfiles}`);

        // ORPHAN CHECK - raw payloads without extracted profiles
        console.log('\n--- ORPHAN CHECK ---\n');
        
        // Get all linkedin_urls from raw
        const { data: allRawUrls } = await supabase
            .schema('raw')
            .from('person_payloads')
            .select('linkedin_url');

        // Get all linkedin_urls from profiles
        const { data: allProfileUrls } = await supabase
            .schema('extracted')
            .from('person_profile')
            .select('linkedin_url');

        const rawUrlSet = new Set(allRawUrls?.map(r => r.linkedin_url) || []);
        const profileUrlSet = new Set(allProfileUrls?.map(p => p.linkedin_url) || []);

        const orphanedUrls = [...rawUrlSet].filter(url => !profileUrlSet.has(url));

        console.log(`Total unique linkedin_urls in raw:      ${rawUrlSet.size}`);
        console.log(`Total unique linkedin_urls in profiles: ${profileUrlSet.size}`);
        console.log(`Orphaned (raw exists, no profile):      ${orphanedUrls.length}`);

        if (orphanedUrls.length > 0 && orphanedUrls.length <= 20) {
            console.log('\nOrphaned URLs:');
            orphanedUrls.forEach(url => console.log(`  - ${url}`));
        } else if (orphanedUrls.length > 20) {
            console.log(`\nFirst 20 orphaned URLs:`);
            orphanedUrls.slice(0, 20).forEach(url => console.log(`  - ${url}`));
            console.log(`  ... and ${orphanedUrls.length - 20} more`);
        }

        // SUMMARY
        console.log('\n' + '='.repeat(50));
        console.log('SUMMARY');
        console.log('='.repeat(50));
        console.log(`\nTotal raw payloads:     ${rawCount}`);
        console.log(`Total profiles:         ${profileCount}`);
        console.log(`Difference:             ${rawCount - profileCount}`);
        console.log(`Orphaned URLs:          ${orphanedUrls.length}`);
        console.log(`\nData observed at:       ${now}`);

    } catch (err) {
        console.error('UNEXPECTED ERROR:', err.message);
        process.exit(1);
    }
}

investigate();

