import {
  ASSET_DATA, AI_OUTLOOK, DASHBOARD_TOP_RISKS,
  MARKET_SENTIMENT_PULSE, DASHBOARD_METRICS,
} from '../data/mockData';
import ConfidenceGauge from '../components/ConfidenceGauge';

function ImpactTag({ tag }: { tag: string }) {
  return (
    <span
      className="inline-block px-3.5 py-1.5 rounded-full text-xs font-semibold mr-2 mb-1"
      style={{ background: '#EEF2FF', color: '#4338CA' }}
    >
      {tag}
    </span>
  );
}

export default function Dashboard() {
  const asset = ASSET_DATA;
  const outlook = AI_OUTLOOK;
  const risks = DASHBOARD_TOP_RISKS;
  const pulse = MARKET_SENTIMENT_PULSE;
  const metrics = DASHBOARD_METRICS;

  return (
    <div>
      {/* Asset Header */}
      <div className="flex flex-wrap justify-between items-end gap-4 mb-6">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <span
              className="px-2 py-1 rounded text-[11px] font-extrabold text-white"
              style={{ background: '#003399' }}
            >
              TICKER: {asset.ticker}
            </span>
            <span className="text-sm font-medium" style={{ color: '#4B5563' }}>
              {asset.exchange} · {asset.dataType}
            </span>
          </div>
          <h1
            className="text-4xl font-extrabold leading-tight"
            style={{ color: '#111827' }}
          >
            {asset.name}
          </h1>
        </div>
        <div className="flex items-center gap-5 flex-wrap">
          <div style={{ borderLeft: '3px solid #2563EB', paddingLeft: 16 }}>
            <div
              className="text-[11px] font-bold uppercase tracking-wide mb-1"
              style={{ color: '#6B7280' }}
            >
              MARKET PRICE
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold" style={{ color: '#111827' }}>
                ${asset.price.toFixed(2)}
              </span>
              <span className="text-sm font-bold" style={{ color: '#10B981' }}>
                ↑ {asset.changePct}%
              </span>
            </div>
          </div>
          <button
            className="text-white text-sm font-semibold px-5 py-2.5 rounded-md cursor-pointer border-0"
            style={{ background: '#003399', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}
          >
            + Track Asset
          </button>
        </div>
      </div>

      {/* AI Outlook Card */}
      <div
        className="rounded-xl p-6 mb-6 border"
        style={{ background: '#fff', borderColor: '#E2E8F0', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}
      >
        <div className="flex items-start gap-3 mb-4">
          <div
            className="w-10 h-10 rounded-lg flex items-center justify-center text-xl shrink-0"
            style={{ background: '#2563EB', color: '#fff' }}
          >
            🧠
          </div>
          <div>
            <div className="font-bold text-lg" style={{ color: '#111827' }}>{outlook.title}</div>
            <div className="text-sm" style={{ color: '#64748B' }}>
              Cross-referencing 10-K Filings with Global Macro Sentiment
            </div>
          </div>
        </div>
        <p
          className="italic text-base leading-relaxed mb-5"
          style={{ color: '#334155' }}
        >
          "{outlook.quote}"
        </p>
        <div>
          {outlook.tags.map(t => <ImpactTag key={t} tag={t} />)}
        </div>
      </div>

      {/* Two-column: Risks + Pulse */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Top Risks */}
        <div
          className="rounded-xl p-6 border"
          style={{ background: '#fff', borderColor: '#E2E8F0', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}
        >
          <div
            className="flex items-center gap-2 text-[11px] font-extrabold uppercase tracking-wide mb-4"
            style={{ color: '#DC2626' }}
          >
            <div className="w-4 h-0.5 rounded" style={{ background: '#DC2626' }} />
            INTERNAL REALITY
          </div>
          <h2 className="text-[22px] font-bold mb-7" style={{ color: '#0F172A' }}>
            Top 10-K Highlighted Risks
          </h2>
          {risks.map(r => (
            <div key={r.title} className="flex gap-4 mb-6 items-start">
              <span className="text-xl mt-0.5">{r.icon}</span>
              <div>
                <div className="font-bold text-[15px] mb-1" style={{ color: '#0F172A' }}>{r.title}</div>
                <div className="text-sm leading-relaxed" style={{ color: '#475569' }}>{r.description}</div>
              </div>
            </div>
          ))}
        </div>

        {/* Market Pulse */}
        <div
          className="rounded-xl p-6 border"
          style={{ background: '#fff', borderColor: '#E2E8F0', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}
        >
          <div
            className="flex items-center gap-2 text-[11px] font-extrabold uppercase tracking-wide mb-4"
            style={{ color: '#059669' }}
          >
            <div className="w-4 h-0.5 rounded" style={{ background: '#059669' }} />
            EXTERNAL REALITY
          </div>
          <h2 className="text-[22px] font-bold mb-4" style={{ color: '#0F172A' }}>
            Market Sentiment Pulse
          </h2>
          <ConfidenceGauge value={pulse.confidenceIndex} />
          <div
            className="rounded-xl p-4 mt-1"
            style={{ background: '#F0FDF4', border: '1px solid #DCFCE7' }}
          >
            <div className="flex justify-between items-center mb-3">
              <div className="flex items-center gap-2">
                <span
                  className="w-6 h-6 rounded flex items-center justify-center text-xs"
                  style={{ background: '#065F46', color: '#fff' }}
                >
                  📈
                </span>
                <span className="font-bold text-[15px]" style={{ color: '#065F46' }}>{pulse.label}</span>
              </div>
              <span className="text-[11px] font-bold" style={{ color: '#065F46' }}>{pulse.confidenceTier}</span>
            </div>
            <div className="w-full h-1.5 rounded-full mb-3" style={{ background: '#DCFCE7' }}>
              <div
                className="h-full rounded-full"
                style={{ width: `${pulse.confidenceIndex * 100}%`, background: '#065F46' }}
              />
            </div>
            <p className="text-xs leading-snug" style={{ color: '#475569' }}>{pulse.description}</p>
          </div>
        </div>
      </div>

      {/* Bottom Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {metrics.map(m => (
          <div
            key={m.label}
            className="rounded-xl px-5 py-4 flex items-center gap-4 border"
            style={{ background: '#fff', borderColor: '#E2E8F0', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}
          >
            <span className="text-xl">{m.icon}</span>
            <div>
              <div
                className="text-[11px] font-bold uppercase tracking-wide mb-0.5"
                style={{ color: '#64748B' }}
              >
                {m.label}
              </div>
              <div className="text-base font-bold" style={{ color: '#0F172A' }}>{m.value}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
