require('dotenv').config({ path: '.env.local' });
const { createClient } = require('@supabase/supabase-js');

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseKey) {
    console.error('Error: Missing env vars in .env.local');
    process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseKey);

const domainsToDelete = ['sqrx.com', 'crexi.com'];

async function deleteRecords() {
    console.log('=== DELETING COMPANY CUSTOMER RECORDS ===\n');
    console.log(`Domains to delete: ${domainsToDelete.join(', ')}\n`);

    for (const domain of domainsToDelete) {
        console.log(`--- Processing: ${domain} ---\n`);

        // 1. Check if raw record exists
        const { data: rawData, error: rawCheckError } = await supabase
            .schema('raw')
            .from('company_customer_claygent_payloads')
            .select('id, origin_company_name')
            .eq('origin_company_domain', domain);

        if (rawCheckError) {
            console.log(`❌ Error checking raw for ${domain}: ${rawCheckError.message}`);
            continue;
        }

        if (!rawData || rawData.length === 0) {
            console.log(`⚠️ No raw records found for ${domain}\n`);
            continue;
        }

        const rawId = rawData[0].id;
        const companyName = rawData[0].origin_company_name;
        console.log(`Found raw record: ${companyName} (ID: ${rawId})`);

        // 2. Count extracted records
        const { count: extractedCount, error: extractedCountError } = await supabase
            .schema('extracted')
            .from('company_customer_claygent')
            .select('*', { count: 'exact', head: true })
            .eq('origin_company_domain', domain);

        if (extractedCountError) {
            console.log(`❌ Error counting extracted for ${domain}: ${extractedCountError.message}`);
        } else {
            console.log(`Found ${extractedCount} extracted customer records`);
        }

        // 3. Delete extracted records first (due to FK constraint)
        const { error: deleteExtractedError } = await supabase
            .schema('extracted')
            .from('company_customer_claygent')
            .delete()
            .eq('origin_company_domain', domain);

        if (deleteExtractedError) {
            console.log(`❌ Error deleting extracted for ${domain}: ${deleteExtractedError.message}`);
            continue;
        }
        console.log(`✅ Deleted extracted records`);

        // 4. Delete raw record
        const { error: deleteRawError } = await supabase
            .schema('raw')
            .from('company_customer_claygent_payloads')
            .delete()
            .eq('origin_company_domain', domain);

        if (deleteRawError) {
            console.log(`❌ Error deleting raw for ${domain}: ${deleteRawError.message}`);
            continue;
        }
        console.log(`✅ Deleted raw record\n`);
    }

    // Verify final counts
    console.log('--- FINAL COUNTS ---\n');

    const { count: finalRawCount } = await supabase
        .schema('raw')
        .from('company_customer_claygent_payloads')
        .select('*', { count: 'exact', head: true });

    const { count: finalExtractedCount } = await supabase
        .schema('extracted')
        .from('company_customer_claygent')
        .select('*', { count: 'exact', head: true });

    console.log(`Raw payloads remaining: ${finalRawCount}`);
    console.log(`Extracted customers remaining: ${finalExtractedCount}`);

    console.log('\n=== DELETION COMPLETE ===');
}

deleteRecords();

