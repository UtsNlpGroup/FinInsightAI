import { useState } from 'react';
import type { PageKey } from './types';
import Sidebar from './components/Sidebar';
import BottomNav from './components/BottomNav';
import Dashboard from './pages/Dashboard';
import Disclosures from './pages/Disclosures';
import Sentiment from './pages/Sentiment';
import Chat from './pages/Chat';

const PAGE_TITLES: Record<PageKey, string> = {
  dashboard:   'Executive Dashboard',
  disclosures: '10-K Disclosures',
  sentiment:   'Market Sentiment',
  chat:        'Talk to Report',
};

function renderPage(page: PageKey) {
  switch (page) {
    case 'dashboard':   return <Dashboard />;
    case 'disclosures': return <Disclosures />;
    case 'sentiment':   return <Sentiment />;
    case 'chat':        return <Chat />;
  }
}

export default function App() {
  const [currentPage, setCurrentPage] = useState<PageKey>('dashboard');
  const [currentAsset, setCurrentAsset] = useState('AAPL');

  return (
    <div className="flex min-h-screen" style={{ background: '#F8FAFC' }}>
      {/* Sidebar – desktop only */}
      <Sidebar
        currentPage={currentPage}
        currentAsset={currentAsset}
        onNavigate={setCurrentPage}
        onAssetChange={setCurrentAsset}
      />

      {/* Main Content */}
      <main className="flex-1 min-w-0 flex flex-col">
        {/* Top Bar */}
        <header
          className="sticky top-0 z-40 flex items-center justify-between px-6 py-4 border-b"
          style={{
            background: '#fff',
            borderColor: '#E2E8F0',
            boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
          }}
        >
          {/* Mobile branding */}
          <div className="md:hidden flex items-center gap-2">
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center text-lg"
              style={{ background: 'linear-gradient(135deg, #2563EB, #1D4ED8)', color: '#fff' }}
            >
              📈
            </div>
            <span className="font-bold text-base" style={{ color: '#0F172A' }}>FinSight AI</span>
          </div>

          {/* Page Title – desktop */}
          <h2 className="hidden md:block text-xl font-bold" style={{ color: '#0F172A' }}>
            {PAGE_TITLES[currentPage]}
          </h2>

          {/* Right-side user chip */}
          <div className="flex items-center gap-3">
            <div className="text-right hidden sm:block">
              <div className="text-sm font-semibold" style={{ color: '#0F172A' }}>Alex Stratton</div>
              <div className="text-xs" style={{ color: '#64748B' }}>Managing Director</div>
            </div>
            <div
              className="w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold text-white"
              style={{ background: '#2563EB' }}
            >
              AS
            </div>
          </div>
        </header>

        {/* Page Content */}
        <div
          className="flex-1 p-6 overflow-auto"
          style={{ paddingBottom: currentPage === 'chat' ? '1.5rem' : undefined }}
        >
          {/* Extra bottom padding on mobile so content clears the bottom nav */}
          <div className="md:pb-0 pb-20">
            {renderPage(currentPage)}
          </div>
        </div>
      </main>

      {/* Bottom Navigation – mobile only */}
      <BottomNav currentPage={currentPage} onNavigate={setCurrentPage} />
    </div>
  );
}
