'use server';

import { createClient } from '@supabase/supabase-js';
import { Lead } from '@/types';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

export async function getLeads(targetClientId?: string): Promise<Lead[]> {
    const supabase = createClient(supabaseUrl, supabaseKey, {
        db: { schema: 'clients' }
    });

    try {
        let query = supabase
            .from('target_client_leads')
            .select('*');

        if (targetClientId) {
            query = query.eq('target_client_id', targetClientId);
        }

        // Limit for safety, remove later for pagination
        query = query.limit(100);

        const { data, error } = await query;

        if (error) {
            console.error('Error fetching leads:', error);
            // Don't crash for missing table, return empty for now
            return [];
        }

        return (data as Lead[]) || [];
    } catch (error) {
        console.error('Unexpected error fetching leads:', error);
        return [];
    }
}
