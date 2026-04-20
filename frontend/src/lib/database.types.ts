/**
 * Manual type definitions that mirror the Supabase schema.
 * Generated types would normally come from `supabase gen types typescript`.
 */

export interface Database {
  public: {
    Tables: {
      chat_sessions: {
        Row: {
          id: string;
          user_id: string;
          title: string;
          messages: unknown;     // stored as jsonb, cast at runtime
          api_history: unknown;  // stored as jsonb, cast at runtime
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: string;
          user_id: string;
          title?: string;
          messages?: unknown;
          api_history?: unknown;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          title?: string;
          messages?: unknown;
          api_history?: unknown;
          updated_at?: string;
        };
      };
    };
    Views: Record<string, never>;
    Functions: Record<string, never>;
    Enums: Record<string, never>;
  };
}
