/**
 * Supabase client singleton.
 *
 * Reads the project URL and anon key from Vite env vars so the same
 * build can target different Supabase projects without code changes.
 */

import { createClient } from '@supabase/supabase-js';
import type { Database } from './database.types';

const supabaseUrl  = import.meta.env.VITE_SUPABASE_URL  as string;
const supabaseKey  = import.meta.env.VITE_SUPABASE_ANON_KEY as string;

if (!supabaseUrl || !supabaseKey) {
  throw new Error(
    'Missing VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY. ' +
    'Add them to your .env file.',
  );
}

export const supabase = createClient<Database>(supabaseUrl, supabaseKey);
