const { createClient } = require('@supabase/supabase-js');
const dotenv = require('dotenv');
const path = require('path');

// Load env vars
dotenv.config({ path: path.resolve(__dirname, '../.env.local') });

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseKey) {
    console.error('Missing Supabase credentials');
    process.exit(1);
}

console.log('Using Service Role Key:', !!process.env.SUPABASE_SERVICE_ROLE_KEY);

const supabase = createClient(supabaseUrl, supabaseKey, {
    db: { schema: 'extracted' }
});

async function inspectSchema() {
    console.log('Fetching one row from extracted.target_client_leads...');
    const { data, error } = await supabase
        .from('target_client_leads')
        .select('*')
        .limit(1);

    if (error) {
        console.error('Error:', error);
        return;
    }

    if (data && data.length > 0) {
        console.log('Columns found:', Object.keys(data[0]));
        console.log('Sample row:', data[0]);
    } else {
        console.log('Table is empty or no access.');
    }
}

inspectSchema();
