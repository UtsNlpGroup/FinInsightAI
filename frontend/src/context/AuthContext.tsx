/**
 * AuthContext – wraps Supabase auth state so any component can:
 *   - read the current user  (null = not logged in)
 *   - call signIn / signUp / signOut without touching Supabase directly
 */

import {
  createContext, useContext, useEffect, useState, type ReactNode,
} from 'react';
import type { User, AuthError } from '@supabase/supabase-js';
import { supabase } from '../lib/supabase';

// ── Types ─────────────────────────────────────────────────────────────────────

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  signIn:  (email: string, password: string) => Promise<AuthError | null>;
  signUp:  (email: string, password: string) => Promise<AuthError | null>;
  signOut: () => Promise<void>;
}

// ── Context ───────────────────────────────────────────────────────────────────

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user,    setUser]    = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    console.log('[Supabase] auth.getSession()');
    supabase.auth.getSession().then(({ data }) => {
      console.log('[Supabase] auth.getSession() →', data.session ? `user=${data.session.user.email}` : 'no session');
      setUser(data.session?.user ?? null);
      setLoading(false);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      console.log('[Supabase] auth.onAuthStateChange event=%s user=%s', _event, session?.user.email ?? 'none');
      setUser(session?.user ?? null);
    });

    return () => subscription.unsubscribe();
  }, []);

  const signIn = async (email: string, password: string): Promise<AuthError | null> => {
    console.log('[Supabase] auth.signInWithPassword email=%s', email);
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) console.error('[Supabase] auth.signInWithPassword failed:', error.message);
    else console.log('[Supabase] auth.signInWithPassword ok');
    return error;
  };

  const signUp = async (email: string, password: string): Promise<AuthError | null> => {
    console.log('[Supabase] auth.signUp email=%s', email);
    const { error } = await supabase.auth.signUp({ email, password });
    if (error) console.error('[Supabase] auth.signUp failed:', error.message);
    else console.log('[Supabase] auth.signUp ok');
    return error;
  };

  const signOut = async () => {
    console.log('[Supabase] auth.signOut()');
    await supabase.auth.signOut();
    console.log('[Supabase] auth.signOut ok');
  };

  return (
    <AuthContext.Provider value={{ user, loading, signIn, signUp, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
