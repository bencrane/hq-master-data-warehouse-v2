'use server';

import { createClient } from '@supabase/supabase-js';
import { TargetClient } from '@/types';

// We need a fresh client for server actions to ensure no caching issues if we were using cookies
// But here we are using the service role or just anon key. 
// Ideally we should use the one from @/lib/supabase but that might be client-side initialized if it uses browser storage.
// For server actions, best practice is to create a new client or use a server-specific helper.
// Since we have basic auth with env vars, we can reuse or recreate.
// Let's create a specialized client for server-side operations that targets the correct schema.

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

export async function getTargetClients(): Promise<TargetClient[]> {
    const supabase = createClient(supabaseUrl, supabaseKey, {
        db: { schema: 'reference' }
    });

    try {
        const { data, error } = await supabase
            .from('target_clients')
            .select('*')
            .order('created_at', { ascending: false });

        if (error) {
            console.error('Error fetching target clients:', error);
            throw new Error('Failed to fetch target clients');
        }

        return (data as TargetClient[]) || [];
    } catch (error) {
        console.error('Unexpected error:', error);
        return []; // Return empty array on failure to prevent UI crash
    }
}
