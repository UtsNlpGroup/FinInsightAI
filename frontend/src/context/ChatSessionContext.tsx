/**
 * ChatSessionContext – manages multiple named chat sessions.
 *
 * Persistence strategy:
 *  - Primary:  Supabase `chat_sessions` table (synced when user is logged in)
 *  - Fallback: localStorage (used while loading or if Supabase is unavailable)
 *
 * The context loads all sessions for the current user on mount, keeps an
 * in-memory copy for instant UI updates, and flushes every change to Supabase
 * in the background.
 */

import {
  createContext, useContext, useState, useEffect,
  useCallback, type ReactNode,
} from 'react';
import type { ChatMessage, ChatCard } from '../types';
import type { ApiMessage } from '../services/chatApi';
import { supabase } from '../lib/supabase';
import { useAuth } from './AuthContext';

// ── Types ─────────────────────────────────────────────────────────────────────

export interface ChatSession {
  id: string;
  title: string;
  messages: ChatMessage[];
  apiHistory: ApiMessage[];
  createdAt: number;
  updatedAt: number;
}

interface ChatSessionContextValue {
  sessions: ChatSession[];
  currentSessionId: string | null;
  currentSession: ChatSession | null;
  createSession: () => ChatSession;
  switchSession: (id: string) => void;
  updateSession: (id: string, messages: ChatMessage[], apiHistory: ApiMessage[]) => void;
  deleteSession: (id: string) => void;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const LS_KEY = 'finsight_chat_sessions_v2';

function lsLoad(): ChatSession[] {
  try {
    const raw = localStorage.getItem(LS_KEY);
    return raw ? (JSON.parse(raw) as ChatSession[]) : [];
  } catch { return []; }
}

function lsSave(sessions: ChatSession[]) {
  try { localStorage.setItem(LS_KEY, JSON.stringify(sessions)); } catch { /* full */ }
}

function deriveTitle(messages: ChatMessage[]): string {
  const first = messages.find(m => m.role === 'user');
  if (!first) return 'New Chat';
  const text = first.content.trim().replace(/\s+/g, ' ');
  return text.length > 45 ? text.slice(0, 42) + '…' : text;
}

function makeSession(): ChatSession {
  return {
    id: crypto.randomUUID(),
    title: 'New Chat',
    messages: [],
    apiHistory: [],
    createdAt: Date.now(),
    updatedAt: Date.now(),
  };
}

// ── Supabase helpers ──────────────────────────────────────────────────────────

async function dbFetchSessions(userId: string): Promise<ChatSession[]> {
  console.log('[Supabase] SELECT chat_sessions where user_id =', userId);
  const { data: sessions, error: sessErr } = await supabase
    .from('chat_sessions')
    .select('id, title, created_at, updated_at')
    .eq('user_id', userId)
    .order('updated_at', { ascending: false });

  if (sessErr) {
    console.error('[Supabase] SELECT chat_sessions failed:', sessErr.message, sessErr);
    return [];
  }
  if (!sessions || sessions.length === 0) {
    console.log('[Supabase] SELECT chat_sessions → 0 rows');
    return [];
  }
  console.log('[Supabase] SELECT chat_sessions →', sessions.length, 'rows');

  // Fetch all messages for every session in one round-trip
  const sessionIds = sessions.map(s => s.id);
  console.log('[Supabase] SELECT chat_messages for', sessionIds.length, 'sessions');
  const { data: msgs, error: msgsErr } = await supabase
    .from('chat_messages')
    .select('session_id, id, role, content, suggestions, cards, citations, tool_call_id, is_greeting')
    .in('session_id', sessionIds)
    .order('id', { ascending: true });

  if (msgsErr) {
    console.error('[Supabase] SELECT chat_messages failed:', msgsErr.message, msgsErr);
  }
  const allMsgs = msgs ?? [];
  console.log('[Supabase] SELECT chat_messages →', allMsgs.length, 'rows');

  // Group by session
  type MsgRow = typeof allMsgs[number];
  const bySession = new Map<string, MsgRow[]>();
  for (const m of allMsgs) {
    const arr = bySession.get(m.session_id) ?? [];
    arr.push(m);
    bySession.set(m.session_id, arr);
  }

  return sessions.map(s => {
    const rows = bySession.get(s.id) ?? [];
    const messages: ChatMessage[] = rows
      .filter(m => m.role === 'user' || m.role === 'assistant')
      .map(m => ({
        role:        m.role as 'user' | 'assistant',
        content:     m.content,
        ...(m.suggestions && { suggestions: m.suggestions as string[]  }),
        ...(m.cards       && { cards:       m.cards       as ChatCard[] }),
        ...(m.citations   && { citations:   m.citations }),
      }));
    const apiHistory: ApiMessage[] = rows
      .filter(m => !m.is_greeting)
      .map(m => ({
        role:    m.role as ApiMessage['role'],
        content: m.content,
        ...(m.tool_call_id && { tool_call_id: m.tool_call_id }),
      }));
    return {
      id:         s.id,
      title:      s.title,
      messages,
      apiHistory,
      createdAt:  new Date(s.created_at).getTime(),
      updatedAt:  new Date(s.updated_at).getTime(),
    };
  });
}

async function dbUpsertSession(session: ChatSession, userId: string) {
  console.log('[Supabase] UPSERT chat_sessions id=%s title=%s user=%s', session.id, session.title, userId);
  const { error } = await supabase.from('chat_sessions').upsert({
    id:         session.id,
    user_id:    userId,
    title:      session.title,
    updated_at: new Date(session.updatedAt).toISOString(),
  });
  if (error) {
    console.error('[Supabase] UPSERT chat_sessions failed:', error.message, error);
  } else {
    console.log('[Supabase] UPSERT chat_sessions ok id=%s', session.id);
  }
}

async function dbSyncMessages(
  sessionId: string,
  messages: ChatMessage[],
  apiHistory: ApiMessage[],
) {
  console.log('[Supabase] SYNC chat_messages session=%s msgs=%d api=%d',
    sessionId, messages.length, apiHistory.length);

  // Delete all existing rows for this session first (full replace)
  const { error: delErr } = await supabase
    .from('chat_messages')
    .delete()
    .eq('session_id', sessionId);
  if (delErr) {
    console.error('[Supabase] DELETE chat_messages failed:', delErr.message, delErr);
    return;
  }

  if (messages.length === 0) return;

  // Detect the greeting: it's messages[0] when it's an assistant message that
  // isn't in apiHistory. Reliable check: messages has exactly one more entry
  // than apiHistory (greeting + matching user/assistant pairs).
  const hasGreeting =
    messages.length === apiHistory.length + 1 && messages[0]?.role === 'assistant';

  const rows = messages.map((msg, idx) => ({
    session_id:  sessionId,
    role:        msg.role,
    content:     msg.content,
    suggestions: msg.suggestions ?? null,
    cards:       msg.cards       ?? null,
    citations:   msg.citations   ?? null,
    is_greeting: hasGreeting && idx === 0,
  }));

  const { error: insErr } = await supabase.from('chat_messages').insert(rows);
  if (insErr) {
    console.error('[Supabase] INSERT chat_messages failed:', insErr.message, insErr);
  } else {
    console.log('[Supabase] INSERT chat_messages ok count=%d', rows.length);
  }
}

async function dbDeleteSession(id: string) {
  // ON DELETE CASCADE removes all chat_messages rows automatically
  console.log('[Supabase] DELETE chat_sessions id=%s', id);
  const { error } = await supabase.from('chat_sessions').delete().eq('id', id);
  if (error) {
    console.error('[Supabase] DELETE chat_sessions failed:', error.message, error);
  } else {
    console.log('[Supabase] DELETE chat_sessions ok id=%s (messages cascade-deleted)', id);
  }
}

// ── Context ───────────────────────────────────────────────────────────────────

const ChatSessionContext = createContext<ChatSessionContextValue | null>(null);

export function ChatSessionProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [sessions,          setSessions]         = useState<ChatSession[]>(lsLoad);
  const [currentSessionId,  setCurrentSessionId] = useState<string | null>(
    () => lsLoad()[0]?.id ?? null,
  );

  // Sync from Supabase whenever the logged-in user changes
  useEffect(() => {
    if (!user) {
      // Not logged in – fall back to localStorage
      const ls = lsLoad();
      setSessions(ls);
      setCurrentSessionId(ls[0]?.id ?? null);
      return;
    }

    dbFetchSessions(user.id).then(remote => {
      if (remote.length > 0) {
        setSessions(remote);
        setCurrentSessionId(remote[0].id);
      }
    });
  }, [user]);

  // Mirror to localStorage on every change
  useEffect(() => { lsSave(sessions); }, [sessions]);

  const currentSession = sessions.find(s => s.id === currentSessionId) ?? null;

  const createSession = useCallback((): ChatSession => {
    const session = makeSession();
    setSessions(prev => [session, ...prev]);
    setCurrentSessionId(session.id);
    if (user) void dbUpsertSession(session, user.id);
    return session;
  }, [user]);

  const switchSession = useCallback((id: string) => {
    setCurrentSessionId(id);
  }, []);

  const updateSession = useCallback(
    (id: string, messages: ChatMessage[], apiHistory: ApiMessage[]) => {
      const now = Date.now();
      const title = deriveTitle(messages);
      let merged: ChatSession | undefined;

      setSessions(prev => {
        const next = prev.map(s => {
          if (s.id !== id) return s;
          merged = { ...s, messages, apiHistory, title, updatedAt: now };
          return merged;
        });
        return next;
      });

      // Persist outside the updater (avoids Strict-mode double-invocation).
      if (user && merged) {
        void dbUpsertSession(merged, user.id);
        void dbSyncMessages(id, messages, apiHistory);
      }
    },
    [user],
  );

  const deleteSession = useCallback((id: string) => {
    setSessions(prev => {
      const next = prev.filter(s => s.id !== id);
      if (id === currentSessionId) setCurrentSessionId(next[0]?.id ?? null);
      return next;
    });
    if (user) void dbDeleteSession(id);
  }, [currentSessionId, user]);

  return (
    <ChatSessionContext.Provider
      value={{ sessions, currentSessionId, currentSession, createSession, switchSession, updateSession, deleteSession }}
    >
      {children}
    </ChatSessionContext.Provider>
  );
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useChatSessions(): ChatSessionContextValue {
  const ctx = useContext(ChatSessionContext);
  if (!ctx) throw new Error('useChatSessions must be used inside ChatSessionProvider');
  return ctx;
}
