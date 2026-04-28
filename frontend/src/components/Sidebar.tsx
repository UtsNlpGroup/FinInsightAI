import { useState } from 'react';
import {
  LayoutDashboard, TrendingUp,
  ChevronLeft, ChevronRight, BarChart3,
  Plus, MessageCircle, Trash2,
} from 'lucide-react';
import type { PageKey } from '../types';
import { useChatSessions } from '../context/ChatSessionContext';
// ── Nav config ────────────────────────────────────────────────────────────────

const NAV_ITEMS: { key: PageKey; label: string; Icon: React.ElementType }[] = [
  { key: 'dashboard', label: 'Executive Dashboard', Icon: LayoutDashboard },
  { key: 'sentiment', label: 'Market Sentiment',    Icon: TrendingUp      },
];

// ── Props ─────────────────────────────────────────────────────────────────────

interface SidebarProps {
  currentPage: PageKey;
  currentAsset: string;
  onNavigate: (page: PageKey) => void;
  onAssetChange: (asset: string) => void;
  onNewChat: () => void;
  onSwitchSession: (id: string) => void;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function relativeTime(ts: number): string {
  const diff = Date.now() - ts;
  const min  = Math.floor(diff / 60_000);
  const hr   = Math.floor(diff / 3_600_000);
  const day  = Math.floor(diff / 86_400_000);
  if (min < 1)  return 'Just now';
  if (min < 60) return `${min}m ago`;
  if (hr  < 24) return `${hr}h ago`;
  return `${day}d ago`;
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function Sidebar({
  currentPage, currentAsset, onNavigate, onAssetChange, onNewChat, onSwitchSession,
}: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false);
  const { sessions, currentSessionId, deleteSession } = useChatSessions();

  return (
    <aside
      className="hidden md:flex flex-col shrink-0 h-screen sticky top-0 transition-all duration-200"
      style={{
        width: collapsed ? 64 : 240,
        background: '#FFFFFF',
        borderRight: '1px solid #E5E7EB',
      }}
    >
      {/* ── Logo ── */}
      <div className="flex items-center gap-2.5 px-4 py-4" style={{ borderBottom: '1px solid #E5E7EB' }}>
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
          style={{ background: 'linear-gradient(135deg, #4F46E5, #7C3AED)' }}
        >
          <BarChart3 size={16} color="#fff" strokeWidth={2.5} />
        </div>
        {!collapsed && (
          <span className="font-bold text-[15px]" style={{ color: '#111827', letterSpacing: '-0.3px' }}>
            FinSight AI
          </span>
        )}
        <button
          onClick={() => setCollapsed(c => !c)}
          className="ml-auto w-6 h-6 flex items-center justify-center rounded-md border-0 cursor-pointer transition-colors"
          style={{ background: 'transparent', color: '#9CA3AF' }}
          onMouseEnter={e => ((e.currentTarget as HTMLButtonElement).style.background = '#F3F4F6')}
          onMouseLeave={e => ((e.currentTarget as HTMLButtonElement).style.background = 'transparent')}
        >
          {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
        </button>
      </div>


      {/* ── Navigation ── */}
      <nav className="px-2 py-3" style={{ borderBottom: '1px solid #E5E7EB' }}>
        {!collapsed && (
          <p className="text-[10px] font-semibold uppercase tracking-widest mb-1.5 px-2" style={{ color: '#9CA3AF' }}>
            Menu
          </p>
        )}
        <div className="flex flex-col gap-0.5">
          {NAV_ITEMS.map(({ key, label, Icon }) => {
            const active = currentPage === key;
            return (
              <button
                key={key}
                onClick={() => onNavigate(key)}
                title={collapsed ? label : undefined}
                className={`w-full flex items-center rounded-lg border-0 cursor-pointer transition-all text-sm font-medium ${
                  collapsed ? 'justify-center px-2 py-2.5' : 'gap-2.5 px-3 py-2'
                }`}
                style={{
                  background: active ? '#EFF6FF' : 'transparent',
                  color: active ? '#2563EB' : '#374151',
                }}
                onMouseEnter={e => {
                  if (!active) (e.currentTarget as HTMLButtonElement).style.background = '#F9FAFB';
                }}
                onMouseLeave={e => {
                  if (!active) (e.currentTarget as HTMLButtonElement).style.background = 'transparent';
                }}
              >
                <Icon
                  size={16}
                  strokeWidth={active ? 2.5 : 2}
                  style={{ color: active ? '#2563EB' : '#6B7280' }}
                />
                {!collapsed && <span className="truncate">{label}</span>}
              </button>
            );
          })}
        </div>
      </nav>

      {/* ── Chat history ── */}
      <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
        <div
          className={`flex items-center py-2.5 ${collapsed ? 'justify-center px-2' : 'justify-between px-3'}`}
        >
          {!collapsed && (
            <p className="text-[10px] font-semibold uppercase tracking-widest px-1" style={{ color: '#9CA3AF' }}>
              Chat History
            </p>
          )}
          <button
            onClick={onNewChat}
            title="New Chat"
            className="w-7 h-7 flex items-center justify-center rounded-lg border-0 cursor-pointer transition-colors"
            style={{ background: '#EFF6FF', color: '#2563EB' }}
            onMouseEnter={e => ((e.currentTarget as HTMLButtonElement).style.background = '#DBEAFE')}
            onMouseLeave={e => ((e.currentTarget as HTMLButtonElement).style.background = '#EFF6FF')}
          >
            <Plus size={14} strokeWidth={2.5} />
          </button>
        </div>

        {!collapsed && (
          <div className="flex-1 overflow-y-auto px-2 pb-2 flex flex-col gap-0.5">
            {sessions.length === 0 ? (
              <p className="text-xs px-3 py-2" style={{ color: '#D1D5DB' }}>No chats yet</p>
            ) : (
              sessions.map(session => {
                const active = session.id === currentSessionId && currentPage === 'chat';
                return (
                  <div
                    key={session.id}
                    className="group flex items-center gap-2 rounded-lg px-2 py-1.5 cursor-pointer transition-colors"
                    style={{ background: active ? '#EFF6FF' : 'transparent' }}
                    onClick={() => onSwitchSession(session.id)}
                    onMouseEnter={e => {
                      if (!active) (e.currentTarget as HTMLDivElement).style.background = '#F9FAFB';
                    }}
                    onMouseLeave={e => {
                      if (!active) (e.currentTarget as HTMLDivElement).style.background = 'transparent';
                    }}
                  >
                    <MessageCircle
                      size={13}
                      strokeWidth={2}
                      style={{ color: active ? '#2563EB' : '#9CA3AF', flexShrink: 0 }}
                    />
                    <div className="flex-1 min-w-0">
                      <p
                        className="text-xs font-medium truncate leading-tight"
                        style={{ color: active ? '#2563EB' : '#374151' }}
                      >
                        {session.title}
                      </p>
                      <p className="text-[10px] leading-tight" style={{ color: '#9CA3AF' }}>
                        {relativeTime(session.updatedAt)}
                      </p>
                    </div>
                    <button
                      onClick={e => { e.stopPropagation(); deleteSession(session.id); }}
                      className="opacity-0 group-hover:opacity-100 w-5 h-5 flex items-center justify-center rounded border-0 cursor-pointer transition-all"
                      style={{ background: 'transparent', color: '#9CA3AF', flexShrink: 0 }}
                      onMouseEnter={e => {
                        (e.currentTarget as HTMLButtonElement).style.color = '#EF4444';
                        (e.currentTarget as HTMLButtonElement).style.background = '#FEF2F2';
                      }}
                      onMouseLeave={e => {
                        (e.currentTarget as HTMLButtonElement).style.color = '#9CA3AF';
                        (e.currentTarget as HTMLButtonElement).style.background = 'transparent';
                      }}
                    >
                      <Trash2 size={11} strokeWidth={2} />
                    </button>
                  </div>
                );
              })
            )}
          </div>
        )}
      </div>

    </aside>
  );
}
