import { useState, useRef, useMemo, useEffect } from 'react';
import {
  LogOut, Search, X, LayoutDashboard, TrendingUp,
  Plus, BarChart3, MessageCircle, Trash2, Clock, MessageSquare,
  ChevronLeft, ChevronRight,
} from 'lucide-react';
import Dashboard from './pages/Dashboard';
import Sentiment from './pages/Sentiment';
import Chat from './pages/Chat';
import Login from './pages/Login';
import TickerBand from './components/TickerBand';
import { useChatSessions } from './context/ChatSessionContext';
import { useAuth } from './context/AuthContext';
import { useCompanies } from './hooks/useCompanies';

// ── Types ─────────────────────────────────────────────────────────────────────

type PanelKey   = 'dashboard' | 'sentiment';
type MobileView = 'chat' | 'dashboard' | 'sentiment' | 'history';

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

// ── Company search bar ────────────────────────────────────────────────────────

function CompanySearch({
  currentAsset,
  onAssetChange,
}: {
  currentAsset: string;
  onAssetChange: (ticker: string) => void;
}) {
  const { companies } = useCompanies();
  const [query,   setQuery]   = useState('');
  const [open,    setOpen]    = useState(false);
  const [focused, setFocused] = useState(false);
  const inputRef     = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const filtered = useMemo(() => {
    const q = query.toLowerCase();
    if (!q) return companies.slice(0, 8);
    return companies
      .filter(c => c.ticker.toLowerCase().includes(q) || c.company_name.toLowerCase().includes(q))
      .slice(0, 8);
  }, [companies, query]);

  useEffect(() => {
    function handleOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false); setFocused(false); setQuery('');
      }
    }
    document.addEventListener('mousedown', handleOutside);
    return () => document.removeEventListener('mousedown', handleOutside);
  }, []);

  const handleSelect = (ticker: string) => {
    onAssetChange(ticker);
    setQuery(''); setOpen(false); setFocused(false);
    inputRef.current?.blur();
  };

  return (
    <div ref={containerRef} className="relative w-full max-w-lg">
      <div
        className="flex items-center gap-3 px-4 transition-all"
        style={{
          height: 42,
          background: focused ? '#FFFFFF' : '#F3F4F6',
          border: `1.5px solid ${focused ? '#6366F1' : 'transparent'}`,
          borderRadius: 999,
          boxShadow: focused
            ? '0 0 0 4px rgba(99,102,241,0.10), 0 2px 8px rgba(0,0,0,0.06)'
            : '0 1px 3px rgba(0,0,0,0.04)',
        }}
      >
        <Search size={15} strokeWidth={2} style={{ color: focused ? '#6366F1' : '#9CA3AF', flexShrink: 0 }} />
        <input
          ref={inputRef}
          type="text"
          value={focused ? query : currentAsset}
          onChange={e => { setQuery(e.target.value); setOpen(true); }}
          onFocus={() => { setFocused(true); setQuery(''); setOpen(true); }}
          placeholder="Search ticker or company…"
          className="flex-1 bg-transparent border-0 outline-none font-medium"
          style={{ color: '#111827', minWidth: 0, fontSize: 14, letterSpacing: '-0.1px' }}
        />
        {focused && query && (
          <button
            onMouseDown={e => { e.preventDefault(); setQuery(''); }}
            className="w-5 h-5 flex items-center justify-center rounded-full"
            style={{ color: '#9CA3AF', background: '#E5E7EB', border: 'none', cursor: 'pointer', padding: 0, flexShrink: 0 }}
          >
            <X size={11} strokeWidth={2.5} />
          </button>
        )}
      </div>

      {open && filtered.length > 0 && (
        <div
          className="absolute top-full left-0 right-0 mt-2 overflow-hidden z-50"
          style={{
            background: '#FFFFFF',
            border: '1px solid #E5E7EB',
            borderRadius: 16,
            boxShadow: '0 12px 32px rgba(0,0,0,0.12)',
          }}
        >
          {filtered.map(c => (
            <button
              key={c.ticker}
              onMouseDown={() => handleSelect(c.ticker)}
              className="w-full flex items-center gap-3 px-4 py-2.5 text-left border-0 cursor-pointer transition-colors"
              style={{ background: 'transparent' }}
              onMouseEnter={e => ((e.currentTarget as HTMLButtonElement).style.background = '#F9FAFB')}
              onMouseLeave={e => ((e.currentTarget as HTMLButtonElement).style.background = 'transparent')}
            >
              <span
                className="text-[10px] font-bold px-2 py-0.5 rounded-md shrink-0 uppercase tracking-wide"
                style={{ background: '#EEF2FF', color: '#4F46E5' }}
              >
                {c.ticker}
              </span>
              <span className="text-sm font-medium truncate" style={{ color: '#374151' }}>{c.company_name}</span>
              {c.sector && (
                <span className="text-[11px] ml-auto shrink-0" style={{ color: '#9CA3AF' }}>{c.sector}</span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────────

export default function App() {
  const { user, loading, signOut } = useAuth();
  const [activePanel,     setActivePanel]     = useState<PanelKey | null>(null);
  const [currentAsset,    setCurrentAsset]    = useState('AAPL');
  const [mobileView,      setMobileView]      = useState<MobileView>('chat');
  const [navCollapsed,     setNavCollapsed]     = useState(false);
  const [historyCollapsed, setHistoryCollapsed] = useState(false);

  const {
    currentSessionId, currentSession, sessions,
    createSession, switchSession, updateSession, deleteSession,
  } = useChatSessions();

  // ── Loading / auth guard ──
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: '#F9FAFB' }}>
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #4F46E5, #7C3AED)' }}>
            <span className="text-white font-bold text-base">F</span>
          </div>
          <p className="text-sm" style={{ color: '#9CA3AF' }}>Loading…</p>
        </div>
      </div>
    );
  }
  if (!user) return <Login />;

  // ── Handlers ──
  const handleNewChat = () => {
    setMobileView('chat');
    createSession();
  };

  const handleSwitchSession = (id: string) => {
    setMobileView('chat');
    switchSession(id);
  };

  const handleTogglePanel = (panel: PanelKey) => {
    setActivePanel(prev => prev === panel ? null : panel);
  };

  // ── Shared chat node (always mounted to preserve state) ──
  const chatNode = (
    <Chat
      key={currentSessionId ?? 'empty'}
      sessionId={currentSessionId}
      initialMessages={currentSession?.messages}
      initialApiHistory={currentSession?.apiHistory}
      onUpdate={(messages, apiHistory) => {
        if (currentSessionId) {
          updateSession(currentSessionId, messages, apiHistory);
        } else {
          const s = createSession();
          updateSession(s.id, messages, apiHistory);
        }
      }}
    />
  );

  // ── History list (reused in desktop right panel and mobile view) ──
  const historyList = (
    <div className="flex flex-col gap-0.5 px-2 py-1">
      {sessions.length === 0 ? (
        <p className="text-xs text-center py-6" style={{ color: '#D1D5DB' }}>No chats yet</p>
      ) : (
        sessions.map(session => {
          const active = session.id === currentSessionId;
          return (
            <div
              key={session.id}
              className="group flex items-center gap-2 rounded-lg px-2 py-2 cursor-pointer"
              style={{ background: active ? '#EFF6FF' : 'transparent' }}
              onClick={() => handleSwitchSession(session.id)}
              onMouseEnter={e => { if (!active) (e.currentTarget as HTMLDivElement).style.background = '#F9FAFB'; }}
              onMouseLeave={e => { if (!active) (e.currentTarget as HTMLDivElement).style.background = 'transparent'; }}
            >
              <MessageCircle size={13} strokeWidth={2} style={{ color: active ? '#2563EB' : '#9CA3AF', flexShrink: 0 }} />
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium truncate leading-tight" style={{ color: active ? '#2563EB' : '#374151' }}>
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
                onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.color = '#EF4444'; (e.currentTarget as HTMLButtonElement).style.background = '#FEF2F2'; }}
                onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.color = '#9CA3AF'; (e.currentTarget as HTMLButtonElement).style.background = 'transparent'; }}
              >
                <Trash2 size={11} strokeWidth={2} />
              </button>
            </div>
          );
        })
      )}
    </div>
  );

  return (
    <div className="flex flex-col h-screen overflow-hidden" style={{ background: '#F9FAFB' }}>

      {/* ══════════════════════════════════════════════════════════
          HEADER (full width)
      ══════════════════════════════════════════════════════════ */}
      <header
        className="shrink-0 flex items-center gap-4 px-4 py-2.5 z-50"
        style={{ background: '#FFFFFF', borderBottom: '1px solid #E5E7EB' }}
      >
        {/* FinSight AI branding (always visible) */}
        <div className="flex items-center gap-2 shrink-0">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
            style={{ background: 'linear-gradient(135deg, #4F46E5, #7C3AED)' }}
          >
            <BarChart3 size={15} color="#fff" strokeWidth={2.5} />
          </div>
          <span className="hidden sm:block font-bold text-[15px]" style={{ color: '#111827', letterSpacing: '-0.3px' }}>
            FinSight AI
          </span>
        </div>

        {/* Company search — centered */}
        <div className="flex-1 flex justify-center px-4">
          <CompanySearch currentAsset={currentAsset} onAssetChange={setCurrentAsset} />
        </div>

        {/* Avatar + sign out */}
        <div className="shrink-0 flex items-center gap-1.5">
          <div
            className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white shrink-0"
            style={{ background: 'linear-gradient(135deg, #4F46E5, #7C3AED)' }}
            title={user.email ?? ''}
          >
            {(user.email?.[0] ?? 'U').toUpperCase()}
          </div>
          <button
            onClick={signOut}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-sm font-medium border-0 cursor-pointer transition-colors"
            style={{ background: 'transparent', color: '#6B7280' }}
            onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = '#FEF2F2'; (e.currentTarget as HTMLButtonElement).style.color = '#EF4444'; }}
            onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = 'transparent'; (e.currentTarget as HTMLButtonElement).style.color = '#6B7280'; }}
          >
            <LogOut size={14} strokeWidth={2} />
            <span className="hidden sm:inline text-sm">Log Out</span>
          </button>
        </div>
      </header>

      {/* ══════════════════════════════════════════════════════════
          TICKER BAND
      ══════════════════════════════════════════════════════════ */}
      <TickerBand />

      {/* ══════════════════════════════════════════════════════════
          BODY
      ══════════════════════════════════════════════════════════ */}
      <div className="flex-1 min-h-0 flex overflow-hidden">

        {/* ── 1. Left nav (desktop md+, collapsible) ── */}
        <aside
          className="hidden md:flex flex-col shrink-0 transition-all duration-200 overflow-hidden"
          style={{
            width: navCollapsed ? 56 : 200,
            background: '#FFFFFF',
            borderRight: '1px solid #E5E7EB',
          }}
        >
          {/* Collapse toggle */}
          <div
            className={`flex shrink-0 px-2 pt-2 pb-1 ${navCollapsed ? 'justify-center' : 'justify-end'}`}
          >
            <button
              onClick={() => setNavCollapsed(c => !c)}
              className="w-6 h-6 flex items-center justify-center rounded-md border-0 cursor-pointer transition-colors"
              style={{ background: 'transparent', color: '#9CA3AF' }}
              onMouseEnter={e => ((e.currentTarget as HTMLButtonElement).style.background = '#F3F4F6')}
              onMouseLeave={e => ((e.currentTarget as HTMLButtonElement).style.background = 'transparent')}
              title={navCollapsed ? 'Expand' : 'Collapse'}
            >
              {navCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
            </button>
          </div>

          {/* Nav items */}
          <nav className="flex flex-col gap-0.5 px-2 py-3">
            {([
              { key: 'dashboard' as PanelKey, Icon: LayoutDashboard, label: 'Executive Dashboard' },
              { key: 'sentiment' as PanelKey, Icon: TrendingUp,       label: 'Market Sentiment' },
            ]).map(({ key, Icon, label }) => {
              const active = activePanel === key;
              return (
                <button
                  key={key}
                  onClick={() => handleTogglePanel(key)}
                  title={navCollapsed ? label : undefined}
                  className={`flex items-center rounded-lg border-0 cursor-pointer transition-all text-sm font-medium ${navCollapsed ? 'justify-center px-0 py-2.5 w-10 mx-auto' : 'gap-2.5 px-3 py-2 w-full'}`}
                  style={{ background: active ? '#EFF6FF' : 'transparent', color: active ? '#2563EB' : '#374151' }}
                  onMouseEnter={e => { if (!active) (e.currentTarget as HTMLButtonElement).style.background = '#F9FAFB'; }}
                  onMouseLeave={e => { if (!active) (e.currentTarget as HTMLButtonElement).style.background = 'transparent'; }}
                >
                  <Icon size={17} strokeWidth={active ? 2.5 : 2} style={{ color: active ? '#2563EB' : '#6B7280', flexShrink: 0 }} />
                  {!navCollapsed && <span className="truncate">{label}</span>}
                </button>
              );
            })}
          </nav>
        </aside>

        {/* ── 2. Left content panel (desktop md+, animated) ── */}
        <div
          className="hidden md:flex flex-col bg-white overflow-hidden transition-all duration-200 shrink-0"
          style={{
            width: activePanel && !navCollapsed ? 320 : 0,
            borderRight: activePanel && !navCollapsed ? '1px solid #E5E7EB' : 'none',
          }}
        >
          {activePanel && !navCollapsed && (
            <div className="w-80 flex-1 overflow-y-auto overflow-x-hidden">
              {activePanel === 'dashboard' && <Dashboard currentAsset={currentAsset} />}
              {activePanel === 'sentiment' && <Sentiment />}
            </div>
          )}
        </div>

        {/* ── 3. Main chat + mobile views ── */}
        <div className="flex-1 min-w-0 min-h-0 flex flex-col overflow-hidden bg-white">

          {/* Chat — always mounted on desktop; on mobile only when mobileView === 'chat' */}
          <div
            className={`flex-1 min-h-0 flex-col overflow-hidden
              ${mobileView === 'chat' ? 'flex' : 'hidden md:flex'}`}
          >
            {chatNode}
          </div>

          {/* Mobile: dashboard view */}
          <div className={`flex-1 overflow-y-auto ${mobileView === 'dashboard' ? 'flex md:hidden flex-col' : 'hidden'}`}>
            <Dashboard currentAsset={currentAsset} />
          </div>

          {/* Mobile: sentiment view */}
          <div className={`flex-1 overflow-y-auto ${mobileView === 'sentiment' ? 'flex md:hidden flex-col' : 'hidden'}`}>
            <Sentiment />
          </div>

          {/* Mobile: history view */}
          <div
            className={`flex-1 overflow-y-auto bg-white pb-20 ${mobileView === 'history' ? 'flex md:hidden flex-col' : 'hidden'}`}
          >
            <div className="flex items-center justify-between px-4 py-3" style={{ borderBottom: '1px solid #F3F4F6' }}>
              <p className="text-[10px] font-semibold uppercase tracking-widest" style={{ color: '#9CA3AF' }}>Chat History</p>
              <button
                onClick={handleNewChat}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border-0 cursor-pointer"
                style={{ background: '#EFF6FF', color: '#2563EB' }}
              >
                <Plus size={12} strokeWidth={2.5} /> New Chat
              </button>
            </div>
            {historyList}
          </div>
        </div>

        {/* ── 4. Right chat history panel (desktop lg+, collapsible) ── */}
        <div
          className="hidden lg:flex flex-col shrink-0 overflow-hidden transition-all duration-200"
          style={{
            width: historyCollapsed ? 40 : 220,
            background: '#FFFFFF',
            borderLeft: '1px solid #E5E7EB',
          }}
        >
          {/* Collapse toggle row — mirrors the left nav */}
          <div
            className={`flex shrink-0 px-2 pt-2 pb-1 ${historyCollapsed ? 'justify-center' : 'justify-between items-center pr-2 pl-3'}`}
          >
            {!historyCollapsed && (
              <p className="text-[10px] font-semibold uppercase tracking-widest" style={{ color: '#9CA3AF' }}>
                History
              </p>
            )}
            <button
              onClick={() => setHistoryCollapsed(c => !c)}
              className="w-6 h-6 flex items-center justify-center rounded-md border-0 cursor-pointer transition-colors"
              style={{ background: 'transparent', color: '#9CA3AF' }}
              onMouseEnter={e => ((e.currentTarget as HTMLButtonElement).style.background = '#F3F4F6')}
              onMouseLeave={e => ((e.currentTarget as HTMLButtonElement).style.background = 'transparent')}
              title={historyCollapsed ? 'Expand history' : 'Collapse history'}
            >
              {historyCollapsed ? <ChevronLeft size={14} /> : <ChevronRight size={14} />}
            </button>
          </div>

          {/* Expanded: New Chat + list */}
          {!historyCollapsed && (
            <>
              <div
                className="flex items-center justify-end px-3 pb-2 shrink-0"
                style={{ borderBottom: '1px solid #F3F4F6' }}
              >
                <button
                  onClick={handleNewChat}
                  title="New Chat"
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border-0 cursor-pointer text-xs font-medium transition-colors"
                  style={{ background: '#EFF6FF', color: '#2563EB' }}
                  onMouseEnter={e => ((e.currentTarget as HTMLButtonElement).style.background = '#DBEAFE')}
                  onMouseLeave={e => ((e.currentTarget as HTMLButtonElement).style.background = '#EFF6FF')}
                >
                  <Plus size={12} strokeWidth={2.5} /> New Chat
                </button>
              </div>
              <div className="flex-1 overflow-y-auto">
                {historyList}
              </div>
            </>
          )}

          {/* Collapsed: centred clock icon as visual hint */}
          {historyCollapsed && (
            <div className="flex flex-col items-center pt-3 gap-3">
              <button
                onClick={handleNewChat}
                title="New Chat"
                className="w-7 h-7 flex items-center justify-center rounded-lg border-0 cursor-pointer transition-colors"
                style={{ background: '#EFF6FF', color: '#2563EB' }}
                onMouseEnter={e => ((e.currentTarget as HTMLButtonElement).style.background = '#DBEAFE')}
                onMouseLeave={e => ((e.currentTarget as HTMLButtonElement).style.background = '#EFF6FF')}
              >
                <Plus size={13} strokeWidth={2.5} />
              </button>
              <Clock size={14} style={{ color: '#D1D5DB' }} />
            </div>
          )}
        </div>

      </div>

      {/* ══════════════════════════════════════════════════════════
          MOBILE BOTTOM NAV
      ══════════════════════════════════════════════════════════ */}
      <nav
        className="md:hidden fixed bottom-0 left-0 right-0 z-50 flex"
        style={{
          background: '#FFFFFF',
          borderTop: '1px solid #E5E7EB',
          boxShadow: '0 -1px 8px rgba(0,0,0,0.06)',
          paddingBottom: 'env(safe-area-inset-bottom, 0px)',
        }}
      >
        {([
          { key: 'dashboard' as MobileView, label: 'Dashboard', Icon: LayoutDashboard },
          { key: 'sentiment' as MobileView, label: 'Sentiment', Icon: TrendingUp      },
          { key: 'chat'      as MobileView, label: 'Chat',      Icon: MessageSquare   },
          { key: 'history'   as MobileView, label: 'History',   Icon: Clock           },
        ]).map(({ key, label, Icon }) => {
          const active = mobileView === key;
          return (
            <button
              key={key}
              onClick={() => setMobileView(key)}
              className="flex-1 flex flex-col items-center justify-center py-2.5 border-0 cursor-pointer transition-all"
              style={{ background: 'transparent', WebkitTapHighlightColor: 'transparent' }}
            >
              <Icon size={20} strokeWidth={active ? 2.5 : 2} style={{ color: active ? '#2563EB' : '#9CA3AF' }} />
              <span className="text-[10px] font-medium mt-0.5" style={{ color: active ? '#2563EB' : '#9CA3AF' }}>
                {label}
              </span>
            </button>
          );
        })}
      </nav>

    </div>
  );
}
