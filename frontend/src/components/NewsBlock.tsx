export interface NewsItem {
  title: string;
  summary: string;
  sentiment: 'bullish' | 'bearish' | 'neutral';
  ticker?: string;
  date?: string;
  source?: string;
  url?: string;
}

const SENTIMENT_CONFIG = {
  bullish: { label: 'Bullish', badge: '#16A34A' },
  bearish: { label: 'Bearish', badge: '#DC2626' },
  neutral: { label: 'Neutral', badge: '#CA8A04' },
};

function NewsCard({ item }: { item: NewsItem }) {
  const cfg = SENTIMENT_CONFIG[item.sentiment] ?? SENTIMENT_CONFIG.neutral;

  return (
    <div
      className="rounded-xl p-4 mb-3 last:mb-0"
      style={{ background: '#F9FAFB', border: '1px solid #E5E7EB' }}
    >
      {/* Header row */}
      <div className="flex items-start justify-between gap-3 mb-2">
        <p className="text-sm font-semibold leading-snug flex-1" style={{ color: '#111827' }}>
          {item.title}
        </p>
        <span
          className="shrink-0 text-[10px] font-bold uppercase tracking-wide rounded-full px-2 py-0.5"
          style={{ background: cfg.badge, color: '#FFFFFF' }}
        >
          {cfg.label}
        </span>
      </div>

      {/* Meta row */}
      {(item.date || item.source || item.ticker) && (
        <div className="flex flex-wrap items-center gap-2 text-[11px] mb-2" style={{ color: '#6B7280' }}>
          {item.date   && <span>📅 {item.date}</span>}
          {item.source && <span>🏢 {item.source}</span>}
          {item.ticker && (
            <span
              className="font-mono font-bold rounded px-1.5 py-0.5 text-[10px]"
              style={{ background: '#E0E7FF', color: '#4338CA' }}
            >
              {item.ticker}
            </span>
          )}
        </div>
      )}

      {/* Summary */}
      <p className="text-xs leading-relaxed" style={{ color: '#374151' }}>
        {item.summary}
      </p>

      {/* URL */}
      {item.url && (
        <a
          href={item.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 mt-2 text-[11px] underline underline-offset-2 hover:opacity-75 transition-opacity"
          style={{ color: '#2563EB' }}
        >
          🔗 Read full article
        </a>
      )}
    </div>
  );
}

export default function NewsBlock({ items }: { items: NewsItem[] }) {
  if (!items.length) return null;

  return (
    <div className="my-3">
      {items.map((item, i) => (
        <NewsCard key={i} item={item} />
      ))}
    </div>
  );
}
