import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl) {
  throw new Error(
    'NEXT_PUBLIC_SUPABASE_URL is not set. Add it to .env.local or Vercel environment variables.'
  );
}

if (!supabaseKey) {
  throw new Error(
    'NEXT_PUBLIC_SUPABASE_ANON_KEY is not set. Add it to .env.local or Vercel environment variables.'
  );
}

export const supabase = createClient(supabaseUrl, supabaseKey);
