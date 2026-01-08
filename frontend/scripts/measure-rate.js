
require('dotenv').config({ path: '.env.local' });
const { createClient } = require('@supabase/supabase-js');

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
const supabase = createClient(supabaseUrl, supabaseKey);

async function measureRate() {
    console.log('\n=== MEASURING INGEST RATE ===\n');

    // First sample
    const t1 = Date.now();
    const { count: count1 } = await supabase
        .schema('raw')
        .from('person_payloads')
        .select('*', { count: 'exact', head: true });
    
    console.log(`Sample 1: ${count1} raw payloads at ${new Date(t1).toISOString()}`);

    // Wait 10 seconds
    console.log('Waiting 10 seconds...');
    await new Promise(r => setTimeout(r, 10000));

    // Second sample
    const t2 = Date.now();
    const { count: count2 } = await supabase
        .schema('raw')
        .from('person_payloads')
        .select('*', { count: 'exact', head: true });
    
    console.log(`Sample 2: ${count2} raw payloads at ${new Date(t2).toISOString()}`);

    // Calculate rate
    const elapsedSeconds = (t2 - t1) / 1000;
    const newRecords = count2 - count1;
    const ratePerSecond = newRecords / elapsedSeconds;
    const ratePerMinute = ratePerSecond * 60;

    console.log('\n=== RESULTS ===\n');
    console.log(`Time elapsed:        ${elapsedSeconds.toFixed(1)} seconds`);
    console.log(`New records:         ${newRecords}`);
    console.log(`Rate:                ${ratePerSecond.toFixed(1)} records/second`);
    console.log(`Rate:                ${ratePerMinute.toFixed(0)} records/minute`);

    if (newRecords === 0) {
        console.log('\n✅ STREAM APPEARS COMPLETE - No new records in 10 seconds');
    } else {
        console.log(`\n🔴 STILL STREAMING at ${ratePerMinute.toFixed(0)} records/minute`);
    }

    // Get latest timestamp
    const { data: latest } = await supabase
        .schema('raw')
        .from('person_payloads')
        .select('created_at')
        .order('created_at', { ascending: false })
        .limit(1);

    if (latest && latest[0]) {
        const latestTime = new Date(latest[0].created_at);
        const now = new Date();
        const lagSeconds = (now - latestTime) / 1000;
        console.log(`\nLatest record:       ${latest[0].created_at}`);
        console.log(`Lag from now:        ${lagSeconds.toFixed(1)} seconds`);
    }
}

measureRate();

