import { useRef, useEffect, useState } from 'react';
import {
  Send, TrendingUp, BarChart2, FileSearch, PieChart, Square,
  TrendingDown, ShoppingCart,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { ChatMessage } from '../types';
import type { ApiMessage } from '../services/chatApi';
import { useChat } from '../hooks/useChat';
import ChartBlock, { type ChartSpec } from '../components/ChartBlock';

const MAX_CHARS = 3000;

// ── Markdown renderer ─────────────────────────────────────────────────────────

function Markdown({ children }: { children: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        // Headings
        h1: ({ children }) => <h1 className="text-xl font-bold mt-4 mb-2" style={{ color: '#111827' }}>{children}</h1>,
        h2: ({ children }) => <h2 className="text-lg font-bold mt-3 mb-1.5" style={{ color: '#111827' }}>{children}</h2>,
        h3: ({ children }) => <h3 className="text-base font-semibold mt-2 mb-1" style={{ color: '#111827' }}>{children}</h3>,
        // Paragraph – tight spacing to match chat style
        p: ({ children }) => <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>,
        // Lists
        ul: ({ children }) => <ul className="list-disc pl-5 mb-2 space-y-0.5">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal pl-5 mb-2 space-y-0.5">{children}</ol>,
        li: ({ children }) => <li className="leading-relaxed">{children}</li>,
        // Inline code
        code: ({ children, className }) => {
          const isBlock = className?.startsWith('language-');
          return isBlock ? (
            <code
              className="block rounded-lg px-4 py-3 text-xs font-mono overflow-x-auto my-2"
              style={{ background: '#F3F4F6', color: '#374151', border: '1px solid #E5E7EB' }}
            >
              {children}
            </code>
          ) : (
            <code
              className="rounded px-1.5 py-0.5 text-xs font-mono"
              style={{ background: '#F3F4F6', color: '#374151' }}
            >
              {children}
            </code>
          );
        },
        // Code block wrapper
        pre: ({ children }) => <pre className="my-2 overflow-x-auto">{children}</pre>,
        // Blockquote
        blockquote: ({ children }) => (
          <blockquote
            className="border-l-4 pl-4 my-2 italic"
            style={{ borderColor: '#D1D5DB', color: '#6B7280' }}
          >
            {children}
          </blockquote>
        ),
        // Table
        table: ({ children }) => (
          <div className="overflow-x-auto my-3">
            <table className="min-w-full text-xs border-collapse" style={{ borderColor: '#E5E7EB' }}>
              {children}
            </table>
          </div>
        ),
        thead: ({ children }) => <thead style={{ background: '#F9FAFB' }}>{children}</thead>,
        th: ({ children }) => (
          <th className="px-3 py-2 text-left font-semibold border" style={{ borderColor: '#E5E7EB', color: '#374151' }}>
            {children}
          </th>
        ),
        td: ({ children }) => (
          <td className="px-3 py-2 border" style={{ borderColor: '#E5E7EB', color: '#374151' }}>
            {children}
          </td>
        ),
        // Horizontal rule
        hr: () => <hr className="my-3" style={{ borderColor: '#E5E7EB' }} />,
        // Bold / italic / strikethrough
        strong: ({ children }) => <strong className="font-semibold" style={{ color: '#111827' }}>{children}</strong>,
        em: ({ children }) => <em className="italic">{children}</em>,
        del: ({ children }) => <del className="line-through" style={{ color: '#9CA3AF' }}>{children}</del>,
        // Links
        a: ({ href, children }) => (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="underline"
            style={{ color: '#2563EB' }}
          >
            {children}
          </a>
        ),
      }}
    >
      {children}
    </ReactMarkdown>
  );
}

// ── Content parser (splits off ```chart blocks before markdown rendering) ─────

type TextSegment  = { kind: 'text';  content: string };
type ChartSegment = { kind: 'chart'; spec: ChartSpec };
type Segment = TextSegment | ChartSegment;

function parseSegments(raw: string): Segment[] {
  const CHART_RE = /```chart\s*\n([\s\S]*?)\n```/g;
  const segments: Segment[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = CHART_RE.exec(raw)) !== null) {
    if (match.index > lastIndex) {
      const text = raw.slice(lastIndex, match.index).trim();
      if (text) segments.push({ kind: 'text', content: text });
    }
    try {
      segments.push({ kind: 'chart', spec: JSON.parse(match[1].trim()) as ChartSpec });
    } catch {
      segments.push({ kind: 'text', content: match[0] });
    }
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < raw.length) {
    const text = raw.slice(lastIndex).trim();
    if (text) segments.push({ kind: 'text', content: text });
  }
  return segments.length ? segments : [{ kind: 'text', content: raw }];
}

// ── Welcome action cards ──────────────────────────────────────────────────────

function makeActionCards(ticker: string, name: string) {
  return [
    {
      Icon: TrendingUp,
      iconBg: '#FEF3C7',
      iconColor: '#D97706',
      title: 'Price History',
      description: `Plot historical price data for ${ticker}`,
      prompt: `Show me ${ticker} price history for the last 6 months`,
    },
    {
      Icon: BarChart2,
      iconBg: '#EDE9FE',
      iconColor: '#7C3AED',
      title: 'Key Financials',
      description: 'Revenue, EBITDA, cash flow breakdown',
      prompt: `What are the key financials for ${name}?`,
    },
    {
      Icon: FileSearch,
      iconBg: '#DCFCE7',
      iconColor: '#16A34A',
      title: 'Risk Analysis',
      description: `Summarise top risks from ${ticker} 10-K`,
      prompt: `What are ${name}'s main risk factors from their 10-K filing?`,
    },
    {
      Icon: PieChart,
      iconBg: '#FCE7F3',
      iconColor: '#DB2777',
      title: 'Compare',
      description: 'Side-by-side metric comparison',
      prompt: `Compare revenue and EBITDA for ${ticker}, MSFT and GOOGL`,
    },
    {
      Icon: ShoppingCart,
      iconBg: '#DBEAFE',
      iconColor: '#2563EB',
      title: `Buy ${ticker}`,
      description: 'Place a paper buy order',
      prompt: `Place a paper buy order for 1 share of ${ticker} at market price`,
    },
    {
      Icon: TrendingDown,
      iconBg: '#FEE2E2',
      iconColor: '#DC2626',
      title: `Sell ${ticker}`,
      description: 'Place a paper sell order',
      prompt: `Place a paper sell order for 1 share of ${ticker} at market price`,
    },
  ];
}

// ── Rolling company name ──────────────────────────────────────────────────────

function RollingName({ name }: { name: string }) {
  return (
    <span
      style={{
        display: 'inline-block',
        overflow: 'hidden',
        verticalAlign: 'bottom',
        maxWidth: '100%',
      }}
    >
      <span
        key={name}
        style={{
          display: 'inline-block',
          animation: 'roll-in 0.45s cubic-bezier(0.22,1,0.36,1) forwards',
        }}
      >
        {name}
      </span>
    </span>
  );
}

function WelcomeState({
  onPrompt,
  currentAsset = 'AAPL',
  currentCompanyName = 'Apple Inc.',
}: {
  onPrompt: (s: string) => void;
  currentAsset?: string;
  currentCompanyName?: string;
}) {
  const cards = makeActionCards(currentAsset, currentCompanyName);

  return (
    <div className="flex flex-col items-center justify-center h-full px-6 pb-8 select-none">
      <h2
        className="text-4xl font-bold text-center mb-2"
        style={{ color: '#111827', letterSpacing: '-1px', lineHeight: 1.15 }}
      >
        Welcome to FinSight AI
      </h2>

      {/* Rolling company name subtitle */}
      <p
        className="text-base font-medium text-center mb-10"
        style={{ color: '#6B7280', maxWidth: 420 }}
      >
        Let's explore{' '}
        <span
          className="font-semibold"
          style={{ color: '#4F46E5' }}
        >
          <RollingName name={currentCompanyName} />
        </span>
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 w-full max-w-2xl">
        {cards.map(({ Icon, iconBg, iconColor, title, description, prompt }) => (
          <button
            key={title}
            onClick={() => onPrompt(prompt)}
            className="flex items-center gap-3.5 rounded-xl px-4 py-4 text-left cursor-pointer border transition-all"
            style={{ background: '#FFFFFF', borderColor: '#E5E7EB', boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}
            onMouseEnter={e => {
              const el = e.currentTarget as HTMLButtonElement;
              el.style.borderColor = '#D1D5DB';
              el.style.boxShadow = '0 2px 8px rgba(0,0,0,0.08)';
            }}
            onMouseLeave={e => {
              const el = e.currentTarget as HTMLButtonElement;
              el.style.borderColor = '#E5E7EB';
              el.style.boxShadow = '0 1px 2px rgba(0,0,0,0.04)';
            }}
          >
            <div className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0" style={{ background: iconBg }}>
              <Icon size={18} style={{ color: iconColor }} strokeWidth={2} />
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold truncate" style={{ color: '#111827' }}>{title}</p>
              <p className="text-xs truncate" style={{ color: '#9CA3AF' }}>{description}</p>
            </div>
            <span className="ml-auto text-lg shrink-0" style={{ color: '#D1D5DB' }}>+</span>
          </button>
        ))}
      </div>
    </div>
  );
}

// ── Streaming cursor ──────────────────────────────────────────────────────────

function StreamingCursor() {
  return (
    <span
      className="inline-block w-[5px] h-[14px] ml-0.5 rounded-sm align-middle"
      style={{ background: '#374151', animation: 'blink 1s step-end infinite' }}
    />
  );
}

// ── Tool banner ───────────────────────────────────────────────────────────────

function ToolBanner({ tool, status }: { tool: string; status: 'running' | 'done' }) {
  const running = status === 'running';
  return (
    <div className="flex justify-center mb-3">
      <span
        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border"
        style={{
          background: running ? '#F0F9FF' : '#F0FDF4',
          color:      running ? '#0369A1' : '#15803D',
          borderColor: running ? '#BAE6FD' : '#86EFAC',
        }}
      >
        <span style={{ display: 'inline-block', animation: running ? 'spin 1s linear infinite' : 'none' }}>⚙</span>
        {running ? `Running ${tool}…` : `${tool} complete`}
      </span>
    </div>
  );
}

// ── Message bubbles ───────────────────────────────────────────────────────────

interface AssistantBubbleProps {
  msg: ChatMessage;
  isStreaming?: boolean;
  onSuggestionClick?: (s: string) => void;
}

function AssistantBubble({ msg, isStreaming, onSuggestionClick }: AssistantBubbleProps) {
  const empty = msg.content === '' && isStreaming;

  return (
    <div className="flex gap-3 mb-5">
      {/* Avatar */}
      <div
        className="w-7 h-7 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0 mt-0.5"
        style={{ background: 'linear-gradient(135deg, #4F46E5, #7C3AED)' }}
      >
        F
      </div>

      <div className="flex-1 min-w-0 pt-0.5">
        {empty ? (
          <span className="flex items-center gap-1" style={{ color: '#D1D5DB' }}>
            <span style={{ animation: 'pulse 1.2s ease-in-out infinite' }}>●</span>
            <span style={{ animation: 'pulse 1.2s ease-in-out infinite', animationDelay: '0.25s' }}>●</span>
            <span style={{ animation: 'pulse 1.2s ease-in-out infinite', animationDelay: '0.5s' }}>●</span>
          </span>
        ) : (
          <>
            <div className="text-sm leading-relaxed" style={{ color: '#111827' }}>
              {parseSegments(msg.content).map((seg, i) =>
                seg.kind === 'chart' ? (
                  <ChartBlock key={i} spec={seg.spec} />
                ) : (
                  <Markdown key={i}>{seg.content}</Markdown>
                )
              )}
              {isStreaming && <StreamingCursor />}
            </div>

            {/* Suggestion pills */}
            {!isStreaming && msg.suggestions && msg.suggestions.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-3">
                {msg.suggestions.map(s => (
                  <button
                    key={s}
                    onClick={() => onSuggestionClick?.(s)}
                    className="px-3 py-1.5 rounded-full text-xs font-medium border cursor-pointer transition-colors"
                    style={{ background: '#FFFFFF', color: '#374151', borderColor: '#E5E7EB' }}
                    onMouseEnter={e => ((e.currentTarget as HTMLButtonElement).style.background = '#F9FAFB')}
                    onMouseLeave={e => ((e.currentTarget as HTMLButtonElement).style.background = '#FFFFFF')}
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}

            {/* Info cards */}
            {!isStreaming && msg.cards && msg.cards.length > 0 && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 mt-3">
                {msg.cards.map(card => (
                  <div
                    key={card.title}
                    className="rounded-xl p-3.5 border"
                    style={{ background: '#F9FAFB', borderColor: '#E5E7EB' }}
                  >
                    <p className="text-[10px] font-bold uppercase tracking-widest mb-1.5" style={{ color: '#6B7280' }}>
                      {card.title}
                    </p>
                    <p className="text-xs leading-relaxed" style={{ color: '#6B7280' }}>{card.description}</p>
                  </div>
                ))}
              </div>
            )}

            {/* Citations */}
            {!isStreaming && msg.citations && (
              <div className="flex items-center justify-between mt-3 text-xs" style={{ color: '#9CA3AF' }}>
                <span>{msg.citations}</span>
                <div className="flex gap-2">
                  <button className="hover:text-gray-600">👍</button>
                  <button className="hover:text-gray-600">👎</button>
                  <button className="hover:text-gray-600">📋</button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function UserBubble({ msg }: { msg: ChatMessage }) {
  return (
    <div className="flex justify-end gap-3 mb-5">
      <div
        className="rounded-2xl px-4 py-3 text-sm leading-relaxed max-w-[75%]"
        style={{ background: '#F3F4F6', color: '#111827', border: '1px solid #E5E7EB' }}
      >
        {msg.content}
      </div>
    </div>
  );
}

// ── Chat input ────────────────────────────────────────────────────────────────

interface ChatInputProps {
  isStreaming: boolean;
  onSend: (text: string) => void;
  onCancel: () => void;
}

function ChatInput({ isStreaming, onSend, onCancel }: ChatInputProps) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    const text = value.trim();
    if (!text || isStreaming) return;
    onSend(text);
    setValue('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    if (e.target.value.length > MAX_CHARS) return;
    setValue(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
    }
  };

  const canSend = value.trim().length > 0 && !isStreaming;

  return (
    <div
      className="rounded-xl overflow-hidden"
      style={{ background: '#FFFFFF', border: '1px solid #E5E7EB', boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}
    >
      <textarea
        ref={textareaRef}
        value={value}
        onChange={handleInput}
        onKeyDown={handleKeyDown}
        disabled={isStreaming}
        placeholder={isStreaming ? 'FinSight AI is responding…' : 'Ask about any company, metric, or filing…'}
        rows={1}
        className="w-full px-4 pt-3.5 pb-2 text-sm resize-none border-0 bg-transparent"
        style={{
          color: '#111827',
          minHeight: 44,
          maxHeight: 160,
          opacity: isStreaming ? 0.6 : 1,
          display: 'block',
          lineHeight: 1.6,
        }}
      />

      <div className="flex items-center gap-2 px-3 pb-3">
        <span className="flex-1 text-[11px]" style={{ color: '#9CA3AF' }}>
          {value.length} / {MAX_CHARS.toLocaleString()}
        </span>
        {isStreaming ? (
          <button
            onClick={onCancel}
            className="w-8 h-8 rounded-lg flex items-center justify-center border-0 cursor-pointer transition-opacity hover:opacity-80"
            style={{ background: '#F3F4F6', color: '#374151' }}
            title="Stop generating"
          >
            <Square size={13} strokeWidth={2.5} fill="#374151" />
          </button>
        ) : (
          <button
            onClick={handleSend}
            disabled={!canSend}
            className="w-8 h-8 rounded-lg flex items-center justify-center border-0 cursor-pointer transition-all"
            style={{
              background: canSend ? '#111827' : '#F3F4F6',
              color: canSend ? '#FFFFFF' : '#9CA3AF',
            }}
            title="Send"
          >
            <Send size={13} strokeWidth={2.5} />
          </button>
        )}
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

interface ChatProps {
  sessionId?: string | null;
  initialMessages?: ChatMessage[];
  initialApiHistory?: ApiMessage[];
  onUpdate?: (messages: ChatMessage[], apiHistory: ApiMessage[]) => void;
  currentAsset?: string;
  currentCompanyName?: string;
  model?: string;
}

export default function Chat({
  initialMessages,
  initialApiHistory,
  onUpdate,
  currentAsset = 'AAPL',
  currentCompanyName = 'Apple Inc.',
  model,
}: ChatProps) {
  const { messages, isStreaming, toolActivity, sendMessage, cancelStream } = useChat({
    initialMessages,
    initialApiHistory,
    onUpdate,
    currentAsset,
    currentCompanyName,
    model,
  });
  const bottomRef = useRef<HTMLDivElement>(null);

  const hasConversation = messages.some(m => m.role === 'user');

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, toolActivity]);

  return (
    <>
      <style>{`
        @keyframes blink  { 0%,100%{opacity:1} 50%{opacity:0} }
        @keyframes pulse  { 0%,100%{opacity:0.25} 50%{opacity:1} }
        @keyframes spin   { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }
        @keyframes roll-in {
          from { transform: translateY(70%); opacity: 0; }
          to   { transform: translateY(0);   opacity: 1; }
        }
      `}</style>

      <div className="flex-1 min-h-0 flex flex-col" style={{ background: '#FFFFFF' }}>
        {/* Messages */}
        <div className="flex-1 min-h-0 overflow-y-auto px-4 md:px-8 py-6">
          {!hasConversation ? (
            <WelcomeState
              onPrompt={sendMessage}
              currentAsset={currentAsset}
              currentCompanyName={currentCompanyName}
            />
          ) : (
            <div className="max-w-2xl mx-auto">
              {messages.map((msg, i) => {
                const isLast = i === messages.length - 1;
                return msg.role === 'assistant'
                  ? <AssistantBubble key={i} msg={msg} isStreaming={isLast && isStreaming} onSuggestionClick={sendMessage} />
                  : <UserBubble key={i} msg={msg} />;
              })}
              {toolActivity && <ToolBanner tool={toolActivity.tool} status={toolActivity.status} />}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        {/* Input */}
        <div
          className="shrink-0 px-4 md:px-8 py-4"
          style={{ borderTop: '1px solid #E5E7EB', background: '#FFFFFF' }}
        >
          <div className="max-w-2xl mx-auto">
            <ChatInput isStreaming={isStreaming} onSend={sendMessage} onCancel={cancelStream} />
            <p className="text-center text-[11px] mt-2" style={{ color: '#9CA3AF' }}>
              FinSight AI may make mistakes. Verify critical financial data with source documents.
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
