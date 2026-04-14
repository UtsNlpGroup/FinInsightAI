import { useState, useRef, useEffect } from 'react';
import type { ChatMessage } from '../types';
import { CHAT_DOCUMENT, CHAT_MESSAGES } from '../data/mockData';

function parseMarkdown(text: string): string {
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>');
}

function AssistantMessage({ msg }: { msg: ChatMessage }) {
  return (
    <div className="flex gap-4 mb-6">
      <div
        className="w-9 h-9 rounded-lg flex items-center justify-center text-white text-base shrink-0"
        style={{ background: '#334155', boxShadow: '0 1px 2px rgba(0,0,0,0.1)' }}
      >
        ✨
      </div>
      <div
        className="rounded-xl p-5 flex-1 text-[15px] leading-relaxed"
        style={{ background: '#F1F5F9', color: '#1E293B' }}
      >
        {/* Content */}
        <p dangerouslySetInnerHTML={{ __html: parseMarkdown(msg.content) }} />

        {/* Suggestion Pills */}
        {msg.suggestions && (
          <div className="flex flex-wrap gap-2 mt-4">
            {msg.suggestions.map(s => (
              <button
                key={s}
                className="px-4 py-2 rounded-full text-xs font-semibold border cursor-pointer"
                style={{
                  background: '#fff',
                  color: '#0052CC',
                  borderColor: '#E2E8F0',
                  boxShadow: '0 1px 2px rgba(0,0,0,0.02)',
                }}
              >
                {s}
              </button>
            ))}
          </div>
        )}

        {/* Cards Grid */}
        {msg.cards && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-5">
            {msg.cards.map(card => (
              <div
                key={card.title}
                className="rounded-lg p-4 border"
                style={{ background: '#fff', borderColor: '#E2E8F0' }}
              >
                <div
                  className="text-[11px] font-extrabold uppercase tracking-wide mb-2"
                  style={{ color: '#0052CC' }}
                >
                  {card.title}
                </div>
                <p className="text-sm leading-relaxed" style={{ color: '#475569' }}>{card.description}</p>
              </div>
            ))}
          </div>
        )}

        {/* Citations + Actions */}
        {msg.citations && (
          <div
            className="flex justify-between items-center mt-5 pt-3 text-xs"
            style={{ borderTop: '1px solid #E2E8F0', color: '#64748B' }}
          >
            <span>{msg.citations}</span>
            <div className="flex gap-3 text-base cursor-pointer">
              <span>👍</span>
              <span>👎</span>
              <span>📋</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function UserMessage({ msg }: { msg: ChatMessage }) {
  return (
    <div className="flex justify-end gap-4 mb-6">
      <div
        className="rounded-xl px-5 py-4 text-[15px] max-w-[75%] leading-relaxed text-white"
        style={{ background: '#003399', boxShadow: '0 1px 2px rgba(0,0,0,0.1)' }}
        dangerouslySetInnerHTML={{ __html: parseMarkdown(msg.content) }}
      />
      <div
        className="w-9 h-9 rounded-lg flex items-center justify-center text-white text-base shrink-0"
        style={{ background: '#003399', boxShadow: '0 1px 2px rgba(0,0,0,0.1)' }}
      >
        👤
      </div>
    </div>
  );
}

export default function Chat() {
  const doc = CHAT_DOCUMENT;
  const [messages, setMessages] = useState<ChatMessage[]>(CHAT_MESSAGES);
  const [input, setInput] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed) return;
    setMessages(prev => [
      ...prev,
      { role: 'user', content: trimmed },
      {
        role: 'assistant',
        content: 'This is a prototype. Connect a real LLM backend to generate live answers.',
      },
    ]);
    setInput('');
  };

  return (
    <div className="flex flex-col h-full">
      {/* Document Header */}
      <div
        className="rounded-xl px-6 py-5 flex justify-between items-center mb-8 border"
        style={{ background: '#fff', borderColor: '#E2E8F0', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}
      >
        <div className="flex items-center gap-4">
          <div
            className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl shrink-0"
            style={{ background: '#EEF2FF', color: '#4338CA' }}
          >
            📄
          </div>
          <div>
            <div className="text-lg font-bold mb-1" style={{ color: '#0F172A' }}>{doc.title}</div>
            <div className="text-sm" style={{ color: '#64748B' }}>{doc.description}</div>
          </div>
        </div>
        <span
          className="text-[11px] font-extrabold px-4 py-1.5 rounded-full tracking-wide border shrink-0"
          style={{ background: '#DCFCE7', color: '#166534', borderColor: '#BBF7D0' }}
        >
          {doc.status.toUpperCase()}
        </span>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto pb-4">
        {messages.map((msg, i) =>
          msg.role === 'assistant'
            ? <AssistantMessage key={i} msg={msg} />
            : <UserMessage key={i} msg={msg} />
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="mt-4 pb-1">
        <div
          className="flex items-end gap-3 rounded-xl px-4 py-3 border"
          style={{ background: '#fff', borderColor: '#E2E8F0', boxShadow: '0 4px 6px rgba(0,0,0,0.05)' }}
        >
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="Ask a question about the filings..."
            rows={1}
            className="flex-1 resize-none bg-transparent border-0 outline-none text-sm leading-relaxed"
            style={{ color: '#0F172A', minHeight: 24, maxHeight: 120 }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim()}
            className="w-9 h-9 rounded-lg flex items-center justify-center text-white border-0 cursor-pointer transition-opacity shrink-0"
            style={{
              background: '#003399',
              opacity: input.trim() ? 1 : 0.5,
            }}
          >
            ➤
          </button>
        </div>
        <p className="text-center text-[11px] mt-2" style={{ color: '#64748B' }}>
          FinSight AI can make mistakes. Please verify critical financial data with the source documents.
        </p>
      </div>
    </div>
  );
}
