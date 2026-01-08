
require('dotenv').config({ path: '.env.local' });
const { createClient } = require('@supabase/supabase-js');

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseKey) {
    console.error('Error: Missing env vars in .env.local');
    process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseKey);

const BATCH_ID = '00000000-0000-0000-0000-000000000000';

async function deleteBatchRecords() {
    console.log(`\n=== Deleting records for batch_id: ${BATCH_ID} ===\n`);

    try {
        // Step 1: Get raw_record_ids for this batch
        console.log('Step 1: Finding raw_records for this batch...');
        const { data: rawRecords, error: rawError } = await supabase
            .from('raw_records')
            .select('id')
            .eq('batch_id', BATCH_ID);

        if (rawError) {
            console.error('Error fetching raw_records:', rawError);
            process.exit(1);
        }

        console.log(`Found ${rawRecords?.length || 0} raw_records in this batch`);

        if (!rawRecords || rawRecords.length === 0) {
            console.log('No records to delete. Exiting.');
            process.exit(0);
        }

        const rawRecordIds = rawRecords.map(r => r.id);

        // Step 2: Delete person_profiles linked to these raw_records
        console.log('\nStep 2: Deleting person_profiles linked to these raw_records...');
        const { data: deletedProfiles, error: profileError } = await supabase
            .from('person_profiles')
            .delete()
            .in('raw_record_id', rawRecordIds)
            .select();

        if (profileError) {
            console.error('Error deleting person_profiles:', profileError);
        } else {
            console.log(`Deleted ${deletedProfiles?.length || 0} person_profiles`);
        }

        // Step 3: Delete raw_records for this batch
        console.log('\nStep 3: Deleting raw_records for this batch...');
        const { data: deletedRaw, error: deleteRawError } = await supabase
            .from('raw_records')
            .delete()
            .eq('batch_id', BATCH_ID)
            .select();

        if (deleteRawError) {
            console.error('Error deleting raw_records:', deleteRawError);
        } else {
            console.log(`Deleted ${deletedRaw?.length || 0} raw_records`);
        }

        console.log('\n=== Deletion complete ===\n');

    } catch (err) {
        console.error('Unexpected error:', err.message);
        process.exit(1);
    }
}

deleteBatchRecords();

