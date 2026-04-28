/**
 * Vitest global setup file.
 *
 * - Imports @testing-library/jest-dom so custom matchers (toBeInTheDocument, etc.)
 *   are available in every test file.
 * - Mocks browser globals that jsdom doesn't implement.
 * - Mocks Supabase auth so tests never hit the real backend.
 */

import '@testing-library/jest-dom';
import { vi } from 'vitest';

// ── Mock matchMedia (jsdom doesn't implement it) ──────────────────────────────
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// ── Mock IntersectionObserver ─────────────────────────────────────────────────
Object.defineProperty(window, 'IntersectionObserver', {
  writable: true,
  value: vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
  })),
});

// ── Mock ResizeObserver ───────────────────────────────────────────────────────
Object.defineProperty(window, 'ResizeObserver', {
  writable: true,
  value: vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
  })),
});

// ── Mock Supabase ─────────────────────────────────────────────────────────────
vi.mock('@supabase/supabase-js', () => ({
  createClient: vi.fn(() => ({
    auth: {
      getSession: vi.fn().mockResolvedValue({ data: { session: null }, error: null }),
      onAuthStateChange: vi.fn(() => ({ data: { subscription: { unsubscribe: vi.fn() } } })),
      signInWithPassword: vi.fn().mockResolvedValue({ data: {}, error: null }),
      signOut: vi.fn().mockResolvedValue({ error: null }),
    },
    from: vi.fn(() => ({
      select: vi.fn().mockReturnThis(),
      insert: vi.fn().mockReturnThis(),
      update: vi.fn().mockReturnThis(),
      delete: vi.fn().mockReturnThis(),
      eq: vi.fn().mockReturnThis(),
      single: vi.fn().mockResolvedValue({ data: null, error: null }),
    })),
  })),
}));

// ── Mock fetch (for API calls) ────────────────────────────────────────────────
global.fetch = vi.fn().mockResolvedValue({
  ok: true,
  json: async () => ({
    models: [
      { id: 'openai:gpt-5.4-mini', label: 'GPT-5.4 Mini', is_default: true },
    ],
    default_model: 'openai:gpt-5.4-mini',
  }),
  text: async () => '',
  headers: new Headers({ 'content-type': 'application/json' }),
});
