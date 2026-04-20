import type { NewsArticle } from '../types';
import { NEWS_ARTICLES, AI_THEMES, SENTIMENT_DIVERGENCE, MACRO_CONTEXT } from '../data/mockData';

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

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[10px] font-bold uppercase tracking-widest mb-2.5" style={{ color: '#9CA3AF' }}>
      {children}
    </p>
  );
}

// ── AI Themes ────────────────────────────────────────────────────────────────

function AiThemesSection() {
  return (
    <div className="px-4 py-4 border-b border-slate-100">
      <div className="flex items-center gap-2 mb-3">
        <div className="w-6 h-6 rounded-md flex items-center justify-center text-xs shrink-0" style={{ background: '#F3F4F6' }}>
          ✦
        </div>
        <p className="text-xs font-semibold" style={{ color: '#111827' }}>Extracted AI Themes</p>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {AI_THEMES.map(t => (
          <span
            key={t}
            className="px-2 py-0.5 rounded-full text-[10px] font-medium border cursor-pointer"
            style={{ background: '#F9FAFB', color: '#374151', borderColor: '#E5E7EB' }}
          >
            {t}
          </span>
        ))}
      </div>
    </div>
  );
}

// ── Sentiment Divergence ─────────────────────────────────────────────────────

function DivergenceSection() {
  return (
    <div className="px-4 py-4 border-b border-slate-100">
      <SectionLabel>Sentiment Divergence</SectionLabel>
      <div className="space-y-3">
        {Object.values(SENTIMENT_DIVERGENCE).map(item => {
          const pos   = item.direction === 'Positive';
          const color = pos ? '#10B981' : '#EF4444';
          const bg    = pos ? '#F0FDF4' : '#FEF2F2';
          return (
            <div key={item.label}>
              <div className="flex justify-between items-baseline mb-1">
                <span className="text-[11px] font-medium" style={{ color: '#374151' }}>{item.label}</span>
                <span className="text-[10px] font-bold" style={{ color }}>
                  {item.value}% {item.direction}
                </span>
              </div>
              <div className="w-full h-1.5 rounded-full overflow-hidden" style={{ background: bg }}>
                <div className="h-full rounded-full transition-all duration-500" style={{ width: `${item.value}%`, background: color }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Macro Context ─────────────────────────────────────────────────────────────

function MacroSection() {
  return (
    <div className="px-4 py-4 border-b border-slate-100">
      <SectionLabel>Macro Market Context</SectionLabel>
      <div className="space-y-1.5">
        {MACRO_CONTEXT.map(item => {
          const color = item.value.startsWith('+')
            ? '#10B981'
            : item.value.startsWith('-')
            ? '#EF4444'
            : '#6B7280';
          return (
            <div
              key={item.label}
              className="flex justify-between items-center px-3 py-2 rounded-lg"
              style={{ background: '#F9FAFB', border: '1px solid #F3F4F6' }}
            >
              <span className="text-[11px] font-medium" style={{ color: '#374151' }}>{item.label}</span>
              <span className="text-[11px] font-bold" style={{ color }}>{item.value}</span>
            </div>
          );
        })}
      </div>
      <button className="mt-3 w-full text-center text-[10px] font-semibold cursor-pointer" style={{ color: '#2563EB' }}>
        View Detailed Macro Report →
      </button>
    </div>
  );
}

// ── News Feed ─────────────────────────────────────────────────────────────────

function NewsItem({ article }: { article: NewsArticle }) {
  return (
    <div className="px-4 py-3.5 border-b border-slate-50 hover:bg-slate-50/60 transition-colors cursor-pointer">
      {/* Source + badge row */}
      <div className="flex items-center justify-between gap-2 mb-1.5">
        <span className="text-[9px] font-semibold uppercase tracking-widest truncate" style={{ color: '#9CA3AF' }}>
          {article.source} · {article.time}
        </span>
        <SentimentBadge sentiment={article.sentiment} />
      </div>

      {/* Title */}
      <h3 className="text-[12px] font-semibold leading-snug mb-1 line-clamp-2" style={{ color: '#111827' }}>
        {article.title}
      </h3>

      {/* Description */}
      <p className="text-[10px] leading-relaxed line-clamp-2" style={{ color: '#6B7280' }}>
        {article.description}
      </p>
    </div>
  );
}

// ── Main ─────────────────────────────────────────────────────────────────────

export default function Sentiment() {
  return (
    <div className="flex flex-col h-full antialiased text-slate-900">

      {/* Panel header */}
      <div className="shrink-0 px-4 pt-5 pb-4 border-b border-slate-100">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-[9px] font-black uppercase tracking-wider px-1.5 py-0.5 rounded" style={{ background: '#111827', color: '#fff' }}>
            NLP
          </span>
          <span className="text-[10px] font-medium" style={{ color: '#9CA3AF' }}>Real-time analysis</span>
        </div>
        <h1 className="text-lg font-extrabold tracking-tight" style={{ color: '#111827' }}>
          Market Sentiment
        </h1>
        <p className="text-[11px] mt-0.5" style={{ color: '#6B7280' }}>
          Institutional news · NLP sentiment · macro signals
        </p>
      </div>

      {/* Scrollable body */}
      <div className="flex-1 overflow-y-auto">
        <AiThemesSection />
        <DivergenceSection />
        <MacroSection />

        {/* Signal stream label */}
        <div className="px-4 pt-4 pb-2 sticky top-0 bg-white z-10 border-b border-slate-50">
          <SectionLabel>Signal Stream</SectionLabel>
        </div>

        {/* News items */}
        {NEWS_ARTICLES.map(a => <NewsItem key={a.title} article={a} />)}
      </div>

    </div>
  );
}
