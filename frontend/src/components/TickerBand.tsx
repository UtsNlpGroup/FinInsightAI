import { useTickerBand } from '../hooks/useTickerBand';
import type { BandItem } from '../hooks/useTickerBand';

// ── Mini sparkline SVG ────────────────────────────────────────────────────────

function Sparkline({ points, up }: { points: number[]; up: boolean }) {
  if (!points || points.length < 2) return null;

  const W = 44;
  const H = 16;
  const min   = Math.min(...points);
  const max   = Math.max(...points);
  const range = max - min || 1;

  const pad = 1.5;
  const innerH = H - pad * 2;

  const sx = (i: number) => (i / (points.length - 1)) * W;
  const sy = (v: number) => H - pad - ((v - min) / range) * innerH;

  const ptStr  = points.map((v, i) => `${sx(i)},${sy(v)}`).join(' ');
  const areaD  =
    `M ${sx(0)},${sy(points[0])} ` +
    points.slice(1).map((v, i) => `L ${sx(i + 1)},${sy(v)}`).join(' ') +
    ` L ${sx(points.length - 1)},${H} L ${sx(0)},${H} Z`;

  const stroke = up ? '#10B981' : '#EF4444';
  const fill   = up ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)';

  return (
    <svg
      width={W}
      height={H}
      viewBox={`0 0 ${W} ${H}`}
      className="shrink-0"
      style={{ overflow: 'visible' }}
    >
      <path d={areaD} fill={fill} stroke="none" />
      <polyline
        points={ptStr}
        fill="none"
        stroke={stroke}
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}

// ── Single ticker card ────────────────────────────────────────────────────────

function TickerCard({ item }: { item: BandItem }) {
  const up      = (item.change_pct ?? 0) >= 0;
  const color   = up ? '#10B981' : '#EF4444';
  const bg      = up ? '#F0FDF4' : '#FEF2F2';

  const fmt = (n: number | null | undefined, d = 2) =>
    n == null ? '—' : n.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });

  return (
    <div
      className="flex items-center gap-3 px-4 shrink-0 select-none"
      style={{ borderRight: '1px solid #F3F4F6' }}
    >
      {/* Ticker + name */}
      <div className="flex flex-col leading-none">
        <span className="text-[11px] font-black uppercase tracking-tight" style={{ color: '#111827' }}>
          {item.ticker}
        </span>
        <span className="text-[9px] font-medium mt-0.5 max-w-[80px] truncate" style={{ color: '#9CA3AF' }}>
          {item.company_name}
        </span>
      </div>

      {/* Sparkline */}
      <Sparkline points={item.sparkline} up={up} />

      {/* Price + badge */}
      <div className="flex items-center gap-1.5">
        <span className="text-[12px] font-bold" style={{ color: '#111827' }}>
          {item.currency === 'USD' ? '$' : ''}{fmt(item.price)}
        </span>
        <span
          className="text-[10px] font-bold px-1.5 py-0.5 rounded-full"
          style={{ background: bg, color }}
        >
          {up ? '+' : ''}{fmt(item.change_pct, 2)}%
        </span>
      </div>
    </div>
  );
}

// ── Skeleton card placeholder ─────────────────────────────────────────────────

function SkeletonCard() {
  return (
    <div className="flex items-center gap-3 px-4 shrink-0" style={{ borderRight: '1px solid #F3F4F6' }}>
      <div className="flex flex-col gap-1">
        <div className="h-3 w-10 bg-slate-200 rounded animate-pulse" />
        <div className="h-2 w-16 bg-slate-100 rounded animate-pulse" />
      </div>
      <div className="w-11 h-4 bg-slate-100 rounded animate-pulse" />
      <div className="flex items-center gap-1.5">
        <div className="h-3 w-14 bg-slate-200 rounded animate-pulse" />
        <div className="h-4 w-12 bg-slate-100 rounded-full animate-pulse" />
      </div>
    </div>
  );
}

// ── Main ticker band ──────────────────────────────────────────────────────────

export default function TickerBand() {
  const { items, loading } = useTickerBand();

  const displayItems = loading || items.length === 0
    ? Array.from({ length: 8 }, (_, i) => i)
    : null;

  return (
    <div
      className="shrink-0 overflow-hidden"
      style={{
        height: 40,
        background: '#FFFFFF',
        borderBottom: '1px solid #F3F4F6',
      }}
    >
      {/* Loading skeletons — static row */}
      {displayItems && (
        <div className="flex items-center h-full gap-0">
          {displayItems.map(i => <SkeletonCard key={i} />)}
        </div>
      )}

      {/* Scrolling band */}
      {!displayItems && (
        <div className="flex items-center h-full ticker-scroll">
          {/* Duplicate for seamless loop */}
          {[...items, ...items].map((item, i) => (
            <TickerCard key={`${item.ticker}-${i}`} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}
