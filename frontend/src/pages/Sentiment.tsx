import { useState } from 'react';
import type { NewsArticle } from '../types';
import { NEWS_ARTICLES, AI_THEMES, SENTIMENT_DIVERGENCE } from '../data/mockData';
import { useMarketMacro } from '../hooks/useMarketMacro';

// ── Shared primitives ────────────────────────────────────────────────────────

const SENTIMENT_CFG = {
  BULLISH: { label: 'Bullish', icon: '↗', color: '#15803D', bg: '#F0FDF4', border: '#D1FAE5' },
  BEARISH: { label: 'Bearish', icon: '↘', color: '#DC2626', bg: '#FEF2F2', border: '#FEE2E2' },
  NEUTRAL: { label: 'Neutral', icon: '—',  color: '#6B7280', bg: '#F9FAFB', border: '#E5E7EB' },
};

function SentimentBadge({ sentiment }: { sentiment: NewsArticle['sentiment'] }) {
  const cfg = SENTIMENT_CFG[sentiment];
  return (
    <span
      className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wide border shrink-0"
      style={{ background: cfg.bg, color: cfg.color, borderColor: cfg.border }}
    >
      {cfg.icon} {cfg.label}
    </span>
  );
}

// ── Live Macro card ───────────────────────────────────────────────────────────

function MacroCard() {
  const { items, loading } = useMarketMacro(); // fetches all 5 by default

  const fmt = (n: number | null | undefined, d = 2) =>
    n == null ? '—' : n.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });

  return (
    <div className="rounded-xl border border-slate-100 bg-white px-4 py-3.5">
      <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-3">
        Macro Market Context
      </p>

      {loading && items.length === 0 ? (
        <div className="space-y-1.5">
          {[1, 2, 3].map(i => (
            <div key={i} className="flex justify-between items-center px-3 py-2 rounded-lg animate-pulse" style={{ background: '#F9FAFB' }}>
              <div className="h-3 w-20 bg-slate-200 rounded" />
              <div className="h-3 w-12 bg-slate-200 rounded" />
            </div>
          ))}
        </div>
      ) : (
        <div className="space-y-1.5">
          {items.map(item => {
            // Yields: display the actual price as "X.XX%"
            // Indices: display the daily change_pct as "+X.XX%"
            const displayValue = item.is_yield
              ? `${fmt(item.price, 2)}%`
              : item.change_pct != null
              ? `${item.change_pct >= 0 ? '+' : ''}${fmt(item.change_pct, 2)}%`
              : '—';

            const color = item.is_yield
              ? '#6B7280'
              : (item.change_pct ?? 0) >= 0
              ? '#10B981'
              : '#EF4444';

            return (
              <div
                key={item.key}
                className="flex justify-between items-center px-3 py-2 rounded-lg"
                style={{ background: '#F9FAFB', border: '1px solid #F3F4F6' }}
              >
                <span className="text-[11px] font-medium text-slate-600">{item.label}</span>
                <span className="text-[12px] font-bold" style={{ color }}>{displayValue}</span>
              </div>
            );
          })}
        </div>
      )}

    </div>
  );
}

// ── Overview tab ─────────────────────────────────────────────────────────────

function OverviewTab() {
  return (
    <div className="space-y-3 pt-1">

      {/* AI Themes card */}
      <div className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3.5">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-6 h-6 rounded-md flex items-center justify-center text-xs shrink-0" style={{ background: '#E0E7FF' }}>
            ✦
          </div>
          <p className="text-xs font-bold text-slate-800">Extracted AI Themes</p>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {AI_THEMES.map(t => (
            <span
              key={t}
              className="px-2 py-0.5 rounded-full text-[10px] font-medium border cursor-pointer hover:border-indigo-300 hover:bg-indigo-50 transition-colors"
              style={{ background: '#F9FAFB', color: '#374151', borderColor: '#E5E7EB' }}
            >
              {t}
            </span>
          ))}
        </div>
      </div>

      {/* Sentiment Divergence card */}
      <div className="rounded-xl border border-slate-100 bg-white px-4 py-3.5">
        <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-3">
          Sentiment Divergence
        </p>
        <div className="space-y-3.5">
          {Object.values(SENTIMENT_DIVERGENCE).map(item => {
            const pos   = item.direction === 'Positive';
            const color = pos ? '#10B981' : '#EF4444';
            const bg    = pos ? '#F0FDF4' : '#FEF2F2';
            const trackBg = pos ? '#D1FAE5' : '#FEE2E2';
            return (
              <div key={item.label}>
                <div className="flex justify-between items-baseline mb-1.5">
                  <span className="text-[11px] font-semibold text-slate-700">{item.label}</span>
                  <span
                    className="text-[10px] font-bold px-1.5 py-0.5 rounded-full"
                    style={{ background: bg, color }}
                  >
                    {item.value}% {item.direction}
                  </span>
                </div>
                <div className="w-full h-1.5 rounded-full overflow-hidden" style={{ background: trackBg }}>
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{ width: `${item.value}%`, background: color }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Macro Market Context — live data */}
      <MacroCard />

    </div>
  );
}

// ── News tab ──────────────────────────────────────────────────────────────────

function NewsTab() {
  return (
    <div className="pt-1 space-y-2">
      {NEWS_ARTICLES.map(article => (
        <div
          key={article.title}
          className="rounded-xl border border-slate-100 bg-white p-3.5 hover:border-slate-200 hover:bg-slate-50/50 transition-colors cursor-pointer"
        >
          {/* Source + badge */}
          <div className="flex items-center justify-between gap-2 mb-1.5">
            <span className="text-[9px] font-semibold uppercase tracking-widest truncate text-slate-400">
              {article.source} · {article.time}
            </span>
            <SentimentBadge sentiment={article.sentiment} />
          </div>

          {/* Title */}
          <h3 className="text-[12px] font-semibold leading-snug mb-1 line-clamp-2 text-slate-900">
            {article.title}
          </h3>

          {/* Description */}
          <p className="text-[10px] leading-relaxed line-clamp-2 text-slate-500">
            {article.description}
          </p>
        </div>
      ))}
    </div>
  );
}

// ── Main ─────────────────────────────────────────────────────────────────────

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'news',     label: 'News'     },
];

export default function Sentiment() {
  const [activeTab, setActiveTab] = useState('overview');

  return (
    <div className="flex flex-col h-full antialiased text-slate-900">

      {/* Panel header */}
      <div className="shrink-0 px-4 pt-5 pb-3 border-b border-slate-100">
        <div className="flex items-center gap-2 mb-1">
          <span
            className="text-[9px] font-black uppercase tracking-wider px-1.5 py-0.5 rounded"
            style={{ background: '#111827', color: '#fff' }}
          >
            NLP
          </span>
          <span className="text-[10px] font-medium text-slate-400">Real-time analysis</span>
        </div>
        <h1 className="text-base font-extrabold tracking-tight text-slate-900">
          Market Sentiment
        </h1>
      </div>

      {/* Tab bar */}
      <div className="shrink-0 px-3 pt-3 pb-2">
        <div className="flex gap-0.5 p-1 bg-slate-100 rounded-xl no-scrollbar">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 px-2 py-1.5 text-[10px] font-bold rounded-lg whitespace-nowrap transition-all ${
                activeTab === tab.id
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto px-4 pb-6">
        {activeTab === 'overview' ? <OverviewTab /> : <NewsTab />}
      </div>

    </div>
  );
}
