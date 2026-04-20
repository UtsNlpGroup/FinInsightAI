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
// Built dynamically so suggestions reflect the currently selected company.

function makeGreeting(ticker: string, name: string): ChatMessage {
  return {
    role: 'assistant',
    content:
      "Hello! I'm **FinsightAI**, your financial analyst assistant. " +
      'Ask me about any US-listed company — I can fetch live financials, ' +
      'plot price history, and search stored reports.',
    suggestions: [
      `Key financials for ${ticker}`,
      `Show ${ticker} annual revenue trend`,
      `What are ${name}'s main risk factors?`,
    ],
  };
}

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
  /**
   * Currently selected ticker (e.g. "AAPL"). Injected as a fresh system
   * context message on every API call so the agent always defaults to
   * the company the user has open — without permanently storing it in
   * apiHistory (so it updates immediately when the user switches company).
   */
  currentAsset?: string;
  currentCompanyName?: string;
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
  const {
    initialMessages,
    initialApiHistory,
    onUpdate,
    currentAsset = 'AAPL',
    currentCompanyName = 'Apple Inc.',
  } = options;

  // Seed from saved session, or show the greeting for a brand-new session
  const [messages, setMessages] = useState<ChatMessage[]>(
    initialMessages && initialMessages.length > 0
      ? initialMessages
      : [makeGreeting(currentAsset, currentCompanyName)],
  );
  const [isStreaming, setIsStreaming] = useState(false);
  const [toolActivity, setToolActivity] = useState<ToolActivity | null>(null);

  const conversationId  = useRef(crypto.randomUUID());
  const apiHistory      = useRef<ApiMessage[]>(initialApiHistory ?? []);
  const abortController = useRef<AbortController | null>(null);

  // Keep company context up-to-date in a ref so the latest value is always
  // used when sendMessage fires, even if it changed since last render.
  const assetRef       = useRef(currentAsset);
  const companyRef     = useRef(currentCompanyName);
  assetRef.current     = currentAsset;
  companyRef.current   = currentCompanyName;

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

      // ── Build the API message ─────────────────────────────────────────────
      // The displayed message stays exactly as the user typed it.
      // The API message silently appends the selected company so the agent
      // always knows the context — even when the user just says "show me
      // the financials" or "what are the risks".
      // If the user already mentioned the ticker we skip appending it.
      const ticker  = assetRef.current;
      const company = companyRef.current;
      const alreadyMentioned =
        trimmed.toLowerCase().includes(ticker.toLowerCase()) ||
        trimmed.toLowerCase().includes(company.toLowerCase());
      const apiMessage = alreadyMentioned
        ? trimmed
        : `${trimmed} [Selected company: ${company} (${ticker})]`;

      // Also prepend a system context message as a second layer of certainty.
      const contextMessage: ApiMessage = {
        role: 'system',
        content:
          `The user currently has "${company}" (${ticker}) selected in the dashboard. ` +
          `Default to this company for any query that does not explicitly name another one.`,
      };
      const historyWithContext: ApiMessage[] = [contextMessage, ...historySnapshot];

      // Optimistically append user turn + empty assistant placeholder
      // (show the clean original text in the UI, not the annotated API message)
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
          apiMessage,          // annotated message sent to the LLM
          historyWithContext,  // history + system context
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

        // Commit to API history — store the clean user message (not the
        // annotated version) so conversation replays look natural. The
        // system context is re-injected fresh on every new call anyway.
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
