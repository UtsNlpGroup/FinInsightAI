import { useState } from 'react';
import type { DisclosureCard } from '../types';
import {
  DISCLOSURE_META,
  DISCLOSURE_KEY_RISKS,
  DISCLOSURE_GROWTH_DRIVERS,
  DISCLOSURE_STRATEGIC_FOCUS,
  DISCLOSURE_FINANCIAL_TRENDS,
  FINANCIAL_SNAPSHOT_HEADERS,
  FINANCIAL_SNAPSHOT_ROWS,
} from '../data/mockData';

const IMPACT_COLORS: Record<string, string> = {
  high:             '#EF4444',
  medium:           '#EF4444',
  low:              '#6B7280',
  positive_high:    '#22C55E',
  positive_medium:  '#22C55E',
};

function ImpactBadge({ level, label }: { level: string; label: string }) {
  const color = IMPACT_COLORS[level] ?? '#6B7280';
  return (
    <span
      className="text-[11px] font-extrabold uppercase tracking-wide"
      style={{ color }}
    >
      {label}
    </span>
  );
}

function CardGrid({ cards }: { cards: DisclosureCard[] }) {
  const rows: DisclosureCard[][] = [];
  for (let i = 0; i < cards.length; i += 2) rows.push(cards.slice(i, i + 2));

  return (
    <div>
      {rows.map((pair, ri) => (
        <div key={ri} className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-4">
          {pair.map(card => (
            <div
              key={card.title}
              className="rounded-xl p-6 border flex flex-col justify-between"
              style={{ background: '#fff', borderColor: '#F1F5F9', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}
            >
              <div>
                <div className="flex justify-between items-start mb-4">
                  <div className="flex items-center gap-3">
                    <span className="text-xl">{card.icon}</span>
                    <span className="text-lg font-bold" style={{ color: '#111827' }}>{card.title}</span>
                  </div>
                  <span
                    className="text-[11px] font-bold px-2 py-1 rounded-md shrink-0"
                    style={{ background: '#F1F5F9', color: '#64748B' }}
                  >
                    {card.pageRef}
                  </span>
                </div>
                <p className="text-sm leading-relaxed mb-6" style={{ color: '#475569' }}>{card.description}</p>
              </div>
              <div className="flex justify-between items-center">
                <ImpactBadge level={card.impactLevel} label={card.impact} />
                <span
                  className="text-sm font-semibold cursor-pointer"
                  style={{ color: '#0052CC' }}
                >
                  View Full Text →
                </span>
              </div>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

function FinancialSnapshot() {
  const headers = FINANCIAL_SNAPSHOT_HEADERS;
  const rows = FINANCIAL_SNAPSHOT_ROWS;

  return (
    <div
      className="rounded-xl mt-4 p-4"
      style={{ background: '#fff' }}
    >
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center gap-2.5">
          <span className="text-xl" style={{ color: '#0052CC' }}>📊</span>
          <span className="text-lg font-bold" style={{ color: '#111827' }}>Financial Snapshot Overview</span>
        </div>
        <span className="text-sm font-bold cursor-pointer" style={{ color: '#0052CC' }}>View Full Trends</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full" style={{ borderCollapse: 'collapse', minWidth: 480 }}>
          <thead>
            <tr>
              {headers.map((h, i) => (
                <th
                  key={h}
                  className="px-4 py-4 text-[11px] font-bold uppercase"
                  style={{
                    background: '#F8FAFC',
                    color: '#475569',
                    borderBottom: '1px solid #E2E8F0',
                    textAlign: i === 0 ? 'left' : 'right',
                  }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map(row => {
              const changeColor = row.change.startsWith('-') && row.change.includes('%')
                ? '#EF4444'
                : row.change.startsWith('+')
                  ? '#22C55E'
                  : '#6B7280';
              return (
                <tr key={row.metric}>
                  <td className="px-4 py-4 text-sm font-semibold" style={{ borderBottom: '1px solid #E2E8F0', color: '#111827' }}>{row.metric}</td>
                  <td className="px-4 py-4 text-sm text-right" style={{ borderBottom: '1px solid #E2E8F0', color: '#374151' }}>{row.fy2023}</td>
                  <td className="px-4 py-4 text-sm text-right" style={{ borderBottom: '1px solid #E2E8F0', color: '#374151' }}>{row.fy2022}</td>
                  <td className="px-4 py-4 text-sm text-right font-semibold" style={{ borderBottom: '1px solid #E2E8F0', color: changeColor }}>{row.change}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const TABS = [
  { id: 'risks',     label: 'Key Risks' },
  { id: 'growth',    label: 'Growth Drivers' },
  { id: 'strategic', label: 'Strategic Focus' },
  { id: 'financial', label: 'Financial Trends' },
];

export default function Disclosures() {
  const [activeTab, setActiveTab] = useState('risks');
  const meta = DISCLOSURE_META;

  const cardMap: Record<string, DisclosureCard[]> = {
    risks:     DISCLOSURE_KEY_RISKS,
    growth:    DISCLOSURE_GROWTH_DRIVERS,
    strategic: DISCLOSURE_STRATEGIC_FOCUS,
    financial: DISCLOSURE_FINANCIAL_TRENDS,
  };

  return (
    <div>
      {/* Page Header */}
      <div className="flex flex-wrap justify-between items-start gap-4 mb-6">
        <div>
          <div className="text-sm font-medium mb-2" style={{ color: '#64748B' }}>
            Documents &nbsp;›&nbsp; Annual Filings &nbsp;›&nbsp;
            <span className="font-bold" style={{ color: '#0052CC' }}>10-K</span>
          </div>
          <h1 className="text-[32px] font-extrabold leading-tight mb-1" style={{ color: '#111827' }}>
            {meta.title}
          </h1>
          <p className="text-base" style={{ color: '#475569' }}>{meta.subtitle}</p>
        </div>
        <div className="flex gap-3 mt-4 flex-wrap">
          <button
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold border cursor-pointer"
            style={{
              background: '#fff',
              borderColor: '#D1D5DB',
              color: '#111827',
              boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
            }}
          >
            ↓ Export PDF
          </button>
          <button
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold border-0 cursor-pointer text-white"
            style={{
              background: '#003399',
              boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
            }}
          >
            ✦ Generate AI Summary
          </button>
        </div>
      </div>

      {/* Pill Tabs */}
      <div
        className="inline-flex rounded-xl p-1.5 mb-6 gap-1"
        style={{ background: '#F1F5F9' }}
      >
        {TABS.map(tab => {
          const active = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className="px-5 py-2 rounded-lg text-sm font-semibold border-0 cursor-pointer transition-all"
              style={{
                background: active ? '#fff' : 'transparent',
                color: active ? '#0052CC' : '#64748B',
                boxShadow: active ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
              }}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      <div className="mt-2">
        <CardGrid cards={cardMap[activeTab]} />
        {(activeTab === 'risks' || activeTab === 'financial') && <FinancialSnapshot />}
      </div>
    </div>
  );
}
