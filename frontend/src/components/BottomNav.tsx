import type { PageKey } from '../types';
import { NAV_PAGES } from '../data/mockData';

interface BottomNavProps {
  currentPage: PageKey;
  onNavigate: (page: PageKey) => void;
}

export default function BottomNav({ currentPage, onNavigate }: BottomNavProps) {
  return (
    <nav
      className="md:hidden fixed bottom-0 left-0 right-0 z-50 flex"
      style={{
        background: '#0B1121',
        borderTop: '1px solid #1E293B',
        boxShadow: '0 -4px 24px rgba(0,0,0,0.40)',
        paddingBottom: 'env(safe-area-inset-bottom, 0px)',
      }}
    >
      {NAV_PAGES.map(({ key, name, icon }) => {
        const active = currentPage === key;
        return (
          <button
            key={key}
            onClick={() => onNavigate(key)}
            className="flex-1 flex flex-col items-center justify-center py-2.5 border-0 outline-none cursor-pointer transition-colors"
            style={{
              background: active ? 'rgba(96,165,250,0.12)' : 'transparent',
              color: active ? '#60A5FA' : '#64748B',
              WebkitTapHighlightColor: 'transparent',
            }}
          >
            <span className="text-[22px] leading-none">{icon}</span>
            <span className="text-[10px] font-semibold mt-1 tracking-[0.3px]">{name}</span>
            {active && (
              <span
                className="block w-1 h-1 rounded-full mt-0.5"
                style={{ background: '#60A5FA' }}
              />
            )}
          </button>
        );
      })}
    </nav>
  );
}
