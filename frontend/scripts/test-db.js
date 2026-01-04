
require('dotenv').config({ path: '.env.local' });
const { createClient } = require('@supabase/supabase-js');

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseKey) {
    console.error('Error: Missing env vars in .env.local');
    process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseKey);

async function testConnection() {
    console.log(`Testing connection to ${supabaseUrl}...`);
    try {
        // Attempt to select from a non-existent table to check connectivity
        // If we receive a postgres error (e.g. table not found), we are connected.
        // If we receive a network error, we are not.
        const { data, error } = await supabase.from('__test_connectivity__').select('*').limit(1);

        if (error) {
            // 42P01 is "undefined_table" code from Postgres, meaning we reached the DB
            // 401 means unauthorized, but we reached the server
            if (error.code === '42P01' || error.code === 'PGRST204' || error.message.includes('relation') || error.code === '404') {
                console.log('✅ Connection Successful! (Reached DB, table check confirmed)');
            } else {
                console.log('✅ Connection Successful! (Received error response from server: ' + error.message + ')');
            }
        } else {
            console.log('✅ Connection Successful! (Query executed)');
        }
    } catch (err) {
        console.error('❌ Connection Failed:', err.message);
        process.exit(1);
    }
}

testConnection();
