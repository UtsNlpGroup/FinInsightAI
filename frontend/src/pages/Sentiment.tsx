import type { NewsArticle } from '../types';
import {
  NEWS_ARTICLES, AI_THEMES, SENTIMENT_DIVERGENCE, MACRO_CONTEXT,
} from '../data/mockData';

const SENTIMENT_CFG = {
  BULLISH: { text: 'BULLISH', icon: '↗', color: '#10B981', bg: '#DCFCE7' },
  BEARISH: { text: 'BEARISH', icon: '↘', color: '#EF4444', bg: '#FEE2E2' },
  NEUTRAL: { text: 'NEUTRAL', icon: '—',  color: '#64748B', bg: '#F1F5F9' },
};

function SentimentBadge({ sentiment }: { sentiment: NewsArticle['sentiment'] }) {
  const cfg = SENTIMENT_CFG[sentiment] ?? SENTIMENT_CFG.NEUTRAL;
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-extrabold uppercase tracking-wide"
      style={{ background: cfg.bg, color: cfg.color }}
    >
      {cfg.icon} {cfg.text}
    </span>
  );
}

function NewsCard({ article }: { article: NewsArticle }) {
  return (
    <div
      className="rounded-xl p-5 mb-4 border flex justify-between gap-6"
      style={{ background: '#fff', borderColor: '#E2E8F0', boxShadow: '0 1px 2px rgba(0,0,0,0.05)' }}
    >
      <div className="flex-1">
        <div className="flex items-center gap-3 mb-3">
          <span
            className="text-[11px] font-bold uppercase tracking-wide"
            style={{ color: '#94A3B8' }}
          >
            {article.source} · {article.time}
          </span>
          <SentimentBadge sentiment={article.sentiment} />
        </div>
        <h3
          className="text-lg font-bold leading-snug mb-2"
          style={{ color: '#111827' }}
        >
          {article.title}
        </h3>
        <p className="text-sm leading-relaxed" style={{ color: '#475569' }}>{article.description}</p>
      </div>
      {/* Thumbnail placeholder */}
      <div
        className="hidden sm:block w-28 h-28 rounded-lg shrink-0"
        style={{
          background: 'linear-gradient(135deg, #334155, #0F172A)',
          boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.2)',
        }}
      />
    </div>
  );
}

function NewsFeed() {
  return (
    <div>
      {/* Feed Header */}
      <div className="flex flex-wrap justify-between items-end gap-3 mb-6">
        <div>
          <h2 className="text-[28px] font-extrabold mb-1" style={{ color: '#111827' }}>Signal Stream</h2>
          <p className="text-sm" style={{ color: '#475569' }}>Real-time NLP sentiment analysis of institutional news</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            className="px-4 py-2 rounded-md text-sm font-semibold border-0 cursor-pointer"
            style={{ background: '#F1F5F9', color: '#475569' }}
          >
            All Sources
          </button>
          <button
            className="flex items-center gap-1.5 px-4 py-2 rounded-md text-sm font-semibold border-0 cursor-pointer text-white"
            style={{ background: '#003399', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}
          >
            <span>≡</span> Sort: Newest
          </button>
        </div>
      </div>
      {NEWS_ARTICLES.map(a => <NewsCard key={a.title} article={a} />)}
    </div>
  );
}

function AiInsightsPanel() {
  const themes = AI_THEMES;
  const divergence = SENTIMENT_DIVERGENCE;

  return (
    <div
      className="rounded-xl p-6 mb-6 border"
      style={{ background: '#F8FAFC', borderColor: '#E2E8F0' }}
    >
      {/* Extracted Themes */}
      <div className="flex items-center gap-3 mb-4">
        <div
          className="w-7 h-7 rounded-md flex items-center justify-center text-sm font-bold"
          style={{ background: '#E0E7FF', color: '#4338CA' }}
        >
          ✦
        </div>
        <span className="text-base font-extrabold" style={{ color: '#111827' }}>Extracted AI Themes</span>
      </div>
      <div className="mb-8">
        {themes.map(t => (
          <span
            key={t}
            className="inline-block px-3.5 py-1.5 rounded-full text-xs font-semibold mr-2 mb-2.5 border cursor-pointer"
            style={{
              background: '#fff',
              color: '#0052CC',
              borderColor: '#D1D5DB',
              boxShadow: '0 1px 2px rgba(0,0,0,0.02)',
            }}
          >
            {t}
          </span>
        ))}
      </div>

      {/* Divergence Bars */}
      <div
        className="text-[11px] font-extrabold uppercase tracking-wide mb-4"
        style={{ color: '#64748B' }}
      >
        Sentiment Divergence
      </div>
      {Object.values(divergence).map(item => {
        const isPositive = item.direction === 'Positive';
        const barColor = isPositive ? '#10B981' : '#EF4444';
        return (
          <div key={item.label} className="mb-4">
            <div className="flex justify-between items-baseline mb-1.5">
              <span className="text-sm font-semibold" style={{ color: '#111827' }}>{item.label}</span>
              <span className="text-sm font-bold" style={{ color: barColor }}>
                {item.value}% {item.direction}
              </span>
            </div>
            <div className="w-full h-1.5 rounded overflow-hidden" style={{ background: '#E2E8F0' }}>
              <div
                className="h-full rounded"
                style={{ width: `${item.value}%`, background: barColor }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function MacroPanel() {
  const macro = MACRO_CONTEXT;

  return (
    <div
      className="rounded-xl p-6 border"
      style={{ background: '#fff', borderColor: '#E2E8F0', boxShadow: '0 1px 2px rgba(0,0,0,0.05)' }}
    >
      <h3 className="text-base font-extrabold mb-4" style={{ color: '#111827' }}>Macro Market Context</h3>
      <div className="space-y-2 mb-4">
        {macro.map(item => {
          const color = item.value.startsWith('+')
            ? '#16A34A'
            : item.value.startsWith('-')
              ? '#DC2626'
              : '#475569';
          return (
            <div
              key={item.label}
              className="flex justify-between items-center rounded-lg px-4 py-3"
              style={{ background: '#F1F5F9' }}
            >
              <span className="text-sm font-semibold" style={{ color: '#334155' }}>{item.label}</span>
              <span className="text-sm font-bold" style={{ color }}>{item.value}</span>
            </div>
          );
        })}
      </div>
      <div className="text-center mt-4">
        <span className="text-sm font-bold cursor-pointer" style={{ color: '#0052CC' }}>
          View Detailed Macro Report
        </span>
      </div>
    </div>
  );
}

export default function Sentiment() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-6">
      <NewsFeed />
      <div>
        <AiInsightsPanel />
        <MacroPanel />
      </div>
    </div>
  );
}
