/**
 * useChat – manages streaming chat state for a single session.
 *
 * Accepts initial messages/history from the session store and fires
 * `onUpdate` whenever the conversation changes so the caller can
 * persist the new state.
 */

import { useState, useCallback, useRef } from 'react';
import { streamChat, type ApiMessage } from '../services/chatApi';
import type { ChatMessage } from '../types';

// ── Greeting (display-only, never sent to the API) ────────────────────────────

const GREETING: ChatMessage = {
  role: 'assistant',
  content:
    "Hello! I'm **FinsightAI**, your financial analyst assistant. " +
    'Ask me about any US-listed company — I can fetch live financials, ' +
    'plot price history, and search stored reports.',
  suggestions: [
    'Key financials for AAPL',
    'Compare MSFT and GOOGL revenue',
    "What are Apple's main risk factors?",
  ],
};

// ── Public types ──────────────────────────────────────────────────────────────

export interface ToolActivity {
  tool: string;
  status: 'running' | 'done';
}

export interface UseChatOptions {
  /** Messages to restore (e.g. switching back to a saved session). */
  initialMessages?: ChatMessage[];
  /** API history to restore (parallel to initialMessages). */
  initialApiHistory?: ApiMessage[];
  /**
   * Called after every turn (user message + assistant reply) so the
   * session store can persist the updated conversation.
   */
  onUpdate?: (messages: ChatMessage[], apiHistory: ApiMessage[]) => void;
}

export interface UseChatReturn {
  messages: ChatMessage[];
  isStreaming: boolean;
  toolActivity: ToolActivity | null;
  sendMessage: (text: string) => Promise<void>;
  cancelStream: () => void;
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useChat(options: UseChatOptions = {}): UseChatReturn {
  const { initialMessages, initialApiHistory, onUpdate } = options;

  // Seed from saved session, or show the greeting for a brand-new session
  const [messages, setMessages] = useState<ChatMessage[]>(
    initialMessages && initialMessages.length > 0
      ? initialMessages
      : [GREETING],
  );
  const [isStreaming, setIsStreaming] = useState(false);
  const [toolActivity, setToolActivity] = useState<ToolActivity | null>(null);

  const conversationId = useRef(crypto.randomUUID());
  const apiHistory     = useRef<ApiMessage[]>(initialApiHistory ?? []);
  const abortController = useRef<AbortController | null>(null);
  // Session switching is handled by the parent giving Chat a new `key`
  // (key={currentSessionId}), which remounts the component and re-initialises
  // all useState/useRef values. No useEffect is needed here.

  const cancelStream = useCallback(() => {
    abortController.current?.abort();
  }, []);

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || isStreaming) return;

      const historySnapshot = [...apiHistory.current];

      // Optimistically append user turn + empty assistant placeholder
      setMessages(prev => [
        ...prev,
        { role: 'user', content: trimmed },
        { role: 'assistant', content: '' },
      ]);
      setIsStreaming(true);
      setToolActivity(null);

      abortController.current = new AbortController();
      let fullResponse = '';

      try {
        for await (const chunk of streamChat(
          trimmed,
          historySnapshot,
          conversationId.current,
          abortController.current.signal,
        )) {
          switch (chunk.event) {
            case 'token': {
              fullResponse += chunk.data as string;
              setMessages(prev => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last?.role === 'assistant') {
                  updated[updated.length - 1] = { ...last, content: fullResponse };
                }
                return updated;
              });
              break;
            }
            case 'tool_start': {
              const d = chunk.data as { tool: string };
              setToolActivity({ tool: d.tool, status: 'running' });
              break;
            }
            case 'tool_end': {
              const d = chunk.data as { tool: string };
              setToolActivity({ tool: d.tool, status: 'done' });
              break;
            }
            case 'done':
              setToolActivity(null);
              break;
            case 'error': {
              const d = chunk.data as { error: string };
              setMessages(prev => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                  role: 'assistant',
                  content: `Sorry, an error occurred: ${d.error}`,
                };
                return updated;
              });
              setToolActivity(null);
              break;
            }
          }
        }

        // Commit to API history
        const newHistory: ApiMessage[] = [
          ...historySnapshot,
          { role: 'user', content: trimmed },
          { role: 'assistant', content: fullResponse },
        ];
        apiHistory.current = newHistory;

        // Notify session store
        setMessages(prev => {
          onUpdate?.(prev, newHistory);
          return prev;
        });
      } catch (err) {
        if ((err as Error).name !== 'AbortError') {
          setMessages(prev => {
            const updated = [...prev];
            updated[updated.length - 1] = {
              role: 'assistant',
              content: 'Could not reach the server. Please check your connection and try again.',
            };
            return updated;
          });
        }
        setToolActivity(null);
      } finally {
        setIsStreaming(false);
        abortController.current = null;
      }
    },
    [isStreaming, onUpdate],
  );

  return { messages, isStreaming, toolActivity, sendMessage, cancelStream };
}
