import { useState } from 'react';
import type { DisclosureCard } from '../types';
import {
  DISCLOSURE_META, DISCLOSURE_KEY_RISKS, DISCLOSURE_GROWTH_DRIVERS,
  DISCLOSURE_STRATEGIC_FOCUS, DISCLOSURE_FINANCIAL_TRENDS,
  FINANCIAL_SNAPSHOT_HEADERS, FINANCIAL_SNAPSHOT_ROWS,
} from '../data/mockData';

function Card({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={`rounded-xl border bg-white ${className}`}
      style={{ borderColor: '#E5E7EB', boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}
    >
      {children}
    </div>
  );
}

const IMPACT_CFG: Record<string, { color: string; bg: string }> = {
  high:            { color: '#DC2626', bg: '#FEF2F2' },
  medium:          { color: '#D97706', bg: '#FFFBEB' },
  low:             { color: '#6B7280', bg: '#F9FAFB' },
  positive_high:   { color: '#15803D', bg: '#F0FDF4' },
  positive_medium: { color: '#0891B2', bg: '#ECFEFF' },
};

function ImpactBadge({ level, label }: { level: string; label: string }) {
  const cfg = IMPACT_CFG[level] ?? IMPACT_CFG.low;
  return (
    <span className="text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full"
      style={{ background: cfg.bg, color: cfg.color }}>
      {label}
    </span>
  );
}

function CardGrid({ cards }: { cards: DisclosureCard[] }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {cards.map(card => (
        <Card key={card.title} className="p-5 flex flex-col">
          <div className="flex justify-between items-start gap-3 mb-3">
            <div className="flex items-center gap-2.5">
              <span className="w-8 h-8 rounded-lg flex items-center justify-center text-sm shrink-0" style={{ background: '#F3F4F6' }}>{card.icon}</span>
              <span className="text-sm font-semibold" style={{ color: '#111827' }}>{card.title}</span>
            </div>
            <span className="text-[10px] font-medium px-2 py-0.5 rounded shrink-0" style={{ background: '#F3F4F6', color: '#6B7280' }}>{card.pageRef}</span>
          </div>
          <p className="text-xs leading-relaxed flex-1 mb-4" style={{ color: '#6B7280' }}>{card.description}</p>
          <div className="flex justify-between items-center pt-3" style={{ borderTop: '1px solid #F3F4F6' }}>
            <ImpactBadge level={card.impactLevel} label={card.impact} />
            <span className="text-xs font-medium cursor-pointer" style={{ color: '#2563EB' }}>View →</span>
          </div>
        </Card>
      ))}
    </div>
  );
}

function FinancialSnapshot() {
  return (
    <Card className="mt-5 overflow-hidden">
      <div className="flex justify-between items-center px-5 py-4" style={{ borderBottom: '1px solid #F3F4F6' }}>
        <p className="text-sm font-semibold" style={{ color: '#111827' }}>Financial Snapshot Overview</p>
        <span className="text-xs font-medium cursor-pointer" style={{ color: '#2563EB' }}>View Full Trends</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full" style={{ borderCollapse: 'collapse', minWidth: 480 }}>
          <thead>
            <tr>
              {FINANCIAL_SNAPSHOT_HEADERS.map((h, i) => (
                <th key={h} className="px-5 py-3 text-[10px] font-semibold uppercase tracking-widest"
                  style={{ background: '#F9FAFB', color: '#9CA3AF', borderBottom: '1px solid #E5E7EB', textAlign: i === 0 ? 'left' : 'right' }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {FINANCIAL_SNAPSHOT_ROWS.map(row => {
              const changeColor = row.change.startsWith('-') ? '#EF4444' : row.change.startsWith('+') ? '#10B981' : '#6B7280';
              return (
                <tr key={row.metric} style={{ transition: 'background 0.1s' }}
                  onMouseEnter={e => ((e.currentTarget as HTMLTableRowElement).style.background = '#F9FAFB')}
                  onMouseLeave={e => ((e.currentTarget as HTMLTableRowElement).style.background = '')}>
                  <td className="px-5 py-3 text-sm font-medium" style={{ borderBottom: '1px solid #F3F4F6', color: '#111827' }}>{row.metric}</td>
                  <td className="px-5 py-3 text-sm text-right" style={{ borderBottom: '1px solid #F3F4F6', color: '#374151' }}>{row.fy2023}</td>
                  <td className="px-5 py-3 text-sm text-right" style={{ borderBottom: '1px solid #F3F4F6', color: '#374151' }}>{row.fy2022}</td>
                  <td className="px-5 py-3 text-sm text-right font-semibold" style={{ borderBottom: '1px solid #F3F4F6', color: changeColor }}>{row.change}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

const TABS = [
  { id: 'risks',     label: 'Key Risks' },
  { id: 'growth',    label: 'Growth Drivers' },
  { id: 'strategic', label: 'Strategic Focus' },
  { id: 'financial', label: 'Financial Trends' },
];

const CARD_MAP: Record<string, DisclosureCard[]> = {
  risks: DISCLOSURE_KEY_RISKS, growth: DISCLOSURE_GROWTH_DRIVERS,
  strategic: DISCLOSURE_STRATEGIC_FOCUS, financial: DISCLOSURE_FINANCIAL_TRENDS,
};

export default function Disclosures() {
  const [activeTab, setActiveTab] = useState('risks');
  const meta = DISCLOSURE_META;

  return (
    <div className="max-w-5xl">
      {/* Header */}
      <div className="flex flex-wrap justify-between items-start gap-4 mb-6">
        <div>
          <p className="text-xs mb-1.5" style={{ color: '#9CA3AF' }}>
            Documents › Annual Filings › <span style={{ color: '#2563EB' }}>10-K</span>
          </p>
          <h1 className="text-2xl font-bold mb-1" style={{ color: '#111827', letterSpacing: '-0.3px' }}>{meta.title}</h1>
          <p className="text-sm" style={{ color: '#6B7280' }}>{meta.subtitle}</p>
        </div>
        <div className="flex gap-2">
          <button className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-sm font-medium border cursor-pointer"
            style={{ background: '#fff', borderColor: '#E5E7EB', color: '#374151' }}>
            ↓ Export PDF
          </button>
          <button className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-sm font-medium border-0 cursor-pointer text-white"
            style={{ background: '#111827' }}>
            ✦ AI Summary
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-5 p-1 rounded-lg w-fit" style={{ background: '#F3F4F6' }}>
        {TABS.map(tab => {
          const active = activeTab === tab.id;
          return (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)}
              className="px-4 py-1.5 rounded-md text-sm font-medium border-0 cursor-pointer transition-all"
              style={{
                background: active ? '#FFFFFF' : 'transparent',
                color: active ? '#111827' : '#6B7280',
                boxShadow: active ? '0 1px 3px rgba(0,0,0,0.08)' : 'none',
              }}>
              {tab.label}
            </button>
          );
        })}
      </div>

      <CardGrid cards={CARD_MAP[activeTab]} />
      {(activeTab === 'risks' || activeTab === 'financial') && <FinancialSnapshot />}
    </div>
  );
}
