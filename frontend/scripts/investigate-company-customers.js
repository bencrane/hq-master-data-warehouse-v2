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
    console.log('=== COMPANY CUSTOMER INVESTIGATION ===');
    console.log(`Query executed at: ${new Date().toISOString()}\n`);

    // 1. Check raw table count
    console.log('--- RAW TABLE: company_customer_claygent_payloads ---\n');
    
    const { count: rawCount, error: rawCountError } = await supabase
        .schema('raw')
        .from('company_customer_claygent_payloads')
        .select('*', { count: 'exact', head: true });

    if (rawCountError) {
        console.error('Error fetching raw count:', rawCountError.message);
    } else {
        console.log(`Total raw payloads: ${rawCount}\n`);
    }

    // 2. Get all raw payloads with details
    const { data: rawPayloads, error: rawError } = await supabase
        .schema('raw')
        .from('company_customer_claygent_payloads')
        .select('id, created_at, origin_company_domain, origin_company_name, workflow_slug, raw_payload')
        .order('created_at', { ascending: false })
        .limit(10);

    if (rawError) {
        console.error('Error fetching raw payloads:', rawError.message);
    } else {
        console.log('Recent raw payloads:');
        rawPayloads.forEach((p, i) => {
            const customerCount = p.raw_payload?.customers?.length || 0;
            const confidence = p.raw_payload?.confidence || 'N/A';
            console.log(`${i + 1}. ${p.created_at}`);
            console.log(`   Domain: ${p.origin_company_domain}`);
            console.log(`   Name: ${p.origin_company_name}`);
            console.log(`   Workflow: ${p.workflow_slug}`);
            console.log(`   Customers in payload: ${customerCount}`);
            console.log(`   Confidence: ${confidence}`);
            console.log(`   Raw ID: ${p.id}\n`);
        });
    }

    // 3. Check extracted table count
    console.log('--- EXTRACTED TABLE: company_customer_claygent ---\n');

    const { count: extractedCount, error: extractedCountError } = await supabase
        .schema('extracted')
        .from('company_customer_claygent')
        .select('*', { count: 'exact', head: true });

    if (extractedCountError) {
        console.error('Error fetching extracted count:', extractedCountError.message);
    } else {
        console.log(`Total extracted customers: ${extractedCount}\n`);
    }

    // 4. Get extracted records grouped by origin company
    const { data: extractedByOrigin, error: extractedByOriginError } = await supabase
        .schema('extracted')
        .from('company_customer_claygent')
        .select('origin_company_domain, origin_company_name')
        .order('created_at', { ascending: false });

    if (extractedByOriginError) {
        console.error('Error fetching extracted by origin:', extractedByOriginError.message);
    } else {
        // Group by origin domain
        const grouped = {};
        extractedByOrigin.forEach(r => {
            if (!grouped[r.origin_company_domain]) {
                grouped[r.origin_company_domain] = { name: r.origin_company_name, count: 0 };
            }
            grouped[r.origin_company_domain].count++;
        });

        console.log('Extracted customers by origin company:');
        Object.entries(grouped).forEach(([domain, info]) => {
            console.log(`   ${info.name} (${domain}): ${info.count} customers`);
        });
        console.log('');
    }

    // 5. Sample extracted records
    const { data: sampleExtracted, error: sampleError } = await supabase
        .schema('extracted')
        .from('company_customer_claygent')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(10);

    if (sampleError) {
        console.error('Error fetching sample extracted:', sampleError.message);
    } else {
        console.log('Sample extracted records (10 most recent):');
        sampleExtracted.forEach((r, i) => {
            console.log(`${i + 1}. ${r.company_customer_name}`);
            console.log(`   Origin: ${r.origin_company_name} (${r.origin_company_domain})`);
            console.log(`   Case Study URL: ${r.case_study_url || 'N/A'}`);
            console.log(`   Has Case Study: ${r.has_case_study}`);
            console.log(`   Raw Payload ID: ${r.raw_payload_id}\n`);
        });
    }

    // 6. Verify raw->extracted linkage
    console.log('--- VERIFICATION: Raw → Extracted Linkage ---\n');

    if (rawPayloads && rawPayloads.length > 0) {
        for (const raw of rawPayloads.slice(0, 3)) {
            const expectedCustomers = raw.raw_payload?.customers?.length || 0;
            
            const { count: actualCustomers, error: linkError } = await supabase
                .schema('extracted')
                .from('company_customer_claygent')
                .select('*', { count: 'exact', head: true })
                .eq('raw_payload_id', raw.id);

            if (linkError) {
                console.log(`❌ ${raw.origin_company_name}: Error checking linkage - ${linkError.message}`);
            } else {
                const match = expectedCustomers === actualCustomers;
                const icon = match ? '✅' : '⚠️';
                console.log(`${icon} ${raw.origin_company_name} (${raw.origin_company_domain})`);
                console.log(`   Expected: ${expectedCustomers} customers`);
                console.log(`   Extracted: ${actualCustomers} customers`);
                if (!match) {
                    console.log(`   MISMATCH: ${expectedCustomers - actualCustomers} customers missing`);
                }
                console.log('');
            }
        }
    }

    // 7. Check workflow registry
    console.log('--- WORKFLOW REGISTRY CHECK ---\n');

    const { data: workflow, error: workflowError } = await supabase
        .schema('reference')
        .from('enrichment_workflow_registry')
        .select('*')
        .eq('workflow_slug', 'claygent-get-all-company-customers')
        .single();

    if (workflowError) {
        console.log(`❌ Workflow not found: ${workflowError.message}`);
    } else {
        console.log('✅ Workflow registered:');
        console.log(`   Slug: ${workflow.workflow_slug}`);
        console.log(`   Provider: ${workflow.provider}`);
        console.log(`   Platform: ${workflow.platform}`);
        console.log(`   Payload Type: ${workflow.payload_type}`);
        console.log(`   Entity Type: ${workflow.entity_type}`);
    }

    console.log('\n=== END INVESTIGATION ===');
}

investigate();

