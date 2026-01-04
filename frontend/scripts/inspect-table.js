
require('dotenv').config({ path: '.env.local' });
const { createClient } = require('@supabase/supabase-js');

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
const supabase = createClient(supabaseUrl, supabaseKey);

async function inspectSchema() {
    console.log('Inspecting reference.target_clients...');
    // We can fetch a single row to see the structure if we don't have direct access to schema metadata
    // Or we can try to infer it. Since Supabase JS client wraps the response, let's just get one row.
    const { data, error } = await supabase
        .from('target_clients')
        .select('*')
        .limit(1);
    // Note: The js client might default to 'public' schema.
    // If table is in 'reference' schema, we might need to specify it or configured the client.
    // However, supabase-js usually defaults to public. 
    // Let's try specifying schema in the options if that fails, or use .from('target_clients') if it's exposed.

    if (error) {
        console.log('Error fetching from default schema:', error.message);

        // Try explicitly setting schema if possible, or assume we might need to use the table name if it's in public in api (unlikely if user said reference.target_clients)
        // Actually, supabase-js allows changing schema in constructor or options.
        // Let's try a different approach:
    } else {
        console.log('Sample Row (Default Schema):', data[0] || 'No rows found');
    }
}

async function inspectReferenceSchema() {
    // Re-init with schema

    // Note: To access a different schema with supabase-js, you often need to change the search_path 
    // or use correct permissions. Standard anon key might not have access to 'reference' schema
    // unless explicitly granted.

    // Attempt 1: Fetch from 'reference' schema using rpc or just trying to select if exposed.
    // Supabase client config supports { db: { schema: 'reference' } }

    const clientRef = createClient(supabaseUrl, supabaseKey, { db: { schema: 'reference' } });

    const { data, error } = await clientRef
        .from('target_clients')
        .select('*')
        .limit(1);

    if (error) {
        console.error('Error fetching from reference schema:', error);
    } else {
        console.log('Sample Row (Reference Schema):', data && data.length > 0 ? Object.keys(data[0]) : 'No rows found, cannot infer columns');
        if (data && data.length > 0) console.log('Sample Data:', data[0]);
    }
}

inspectReferenceSchema();
