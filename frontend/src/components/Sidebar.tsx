import { useState } from 'react';
import type { PageKey } from '../types';
import { NAV_PAGES, ASSETS } from '../data/mockData';

interface SidebarProps {
  currentPage: PageKey;
  currentAsset: string;
  onNavigate: (page: PageKey) => void;
  onAssetChange: (asset: string) => void;
}

export default function Sidebar({ currentPage, currentAsset, onNavigate, onAssetChange }: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false);

  const change = ASSETS[currentAsset];
  const isUp = change.startsWith('↑');
  const trendColor = isUp ? '#10B981' : '#EF4444';

  return (
    <aside
      className="hidden md:flex flex-col shrink-0 h-screen sticky top-0 overflow-y-auto transition-all duration-300"
      style={{
        width: collapsed ? 88 : 280,
        background: '#0B1121',
        borderRight: '1px solid #1E293B',
      }}
    >
      {/* Toggle + Branding */}
      <div className="p-4">
        <div className={`flex items-center ${collapsed ? 'justify-center' : 'gap-3'} mb-6`}>
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="w-10 h-10 flex items-center justify-center rounded-lg text-base shrink-0 transition-colors cursor-pointer"
            style={{ background: '#1E293B', color: '#94A3B8' }}
            title="Toggle Navigation"
          >
            ☰
          </button>
          {!collapsed && (
            <div>
              <div className="text-white font-bold text-lg leading-tight" style={{ letterSpacing: '-0.5px' }}>
                FinSight AI
              </div>
              <div className="text-xs font-medium" style={{ color: '#64748B' }}>
                Market &amp; Enterprise Synthesizer
              </div>
            </div>
          )}
        </div>

        {/* Asset Selector */}
        {collapsed ? (
          <div
            className="text-center mb-8 pb-6"
            style={{ borderBottom: '1px solid #1E293B' }}
          >
            <div
              className="w-10 h-10 rounded-lg flex items-center justify-center text-xl mx-auto mb-3"
              style={{ background: 'linear-gradient(135deg, #2563EB, #1D4ED8)', color: '#fff' }}
            >
              📈
            </div>
            <div className="text-white text-xs font-bold">{currentAsset}</div>
            <div className="text-xs font-semibold mt-1" style={{ color: trendColor }}>{change}</div>
          </div>
        ) : (
          <>
            <div
              className="text-xs font-bold mb-3 px-2 uppercase tracking-widest"
              style={{ color: '#475569' }}
            >
              Portfolio Context
            </div>
            <div className="relative mb-6">
              <select
                value={currentAsset}
                onChange={e => onAssetChange(e.target.value)}
                className="w-full rounded-md px-3 py-2.5 text-sm font-semibold appearance-none cursor-pointer outline-none pr-8"
                style={{
                  background: '#0F172A',
                  border: '1px solid #1E293B',
                  color: trendColor,
                }}
              >
                {Object.entries(ASSETS).map(([ticker, chg]) => (
                  <option key={ticker} value={ticker} style={{ color: '#F8FAFC', background: '#0F172A' }}>
                    {ticker}   {chg}
                  </option>
                ))}
              </select>
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none text-xs">▼</span>
            </div>
            <div className="mb-6" style={{ borderBottom: '1px solid #1E293B' }} />
          </>
        )}

        {/* Nav label */}
        {!collapsed && (
          <div
            className="text-xs font-bold mb-3 px-2 uppercase tracking-widest"
            style={{ color: '#475569' }}
          >
            Menu
          </div>
        )}

        {/* Nav Items */}
        <nav className="flex flex-col gap-1.5">
          {NAV_PAGES.map(({ key, name, icon }) => {
            const active = currentPage === key;
            return (
              <button
                key={key}
                onClick={() => onNavigate(key)}
                className={`w-full flex items-center rounded-md text-sm font-medium cursor-pointer transition-all duration-200 border-0 outline-none ${
                  collapsed ? 'justify-center px-3 py-3' : 'gap-3.5 px-4 py-3'
                }`}
                style={{
                  background: active ? '#2563EB' : 'transparent',
                  color: active ? '#FFFFFF' : '#64748B',
                  boxShadow: active ? '0 4px 6px -1px rgba(0,0,0,0.1)' : 'none',
                }}
                title={collapsed ? name : undefined}
              >
                <span className="text-base leading-none">{icon}</span>
                {!collapsed && <span>{name}</span>}
              </button>
            );
          })}
        </nav>
      </div>
    </aside>
  );
}
