import { LayoutDashboard, TrendingUp } from 'lucide-react';
import type { PageKey } from '../types';

const NAV_ITEMS: { key: PageKey; label: string; Icon: React.ElementType }[] = [
  { key: 'dashboard', label: 'Dashboard', Icon: LayoutDashboard },
  { key: 'sentiment', label: 'Sentiment', Icon: TrendingUp      },
];

interface BottomNavProps {
  currentPage: PageKey;
  onNavigate: (page: PageKey) => void;
}

export default function BottomNav({ currentPage, onNavigate }: BottomNavProps) {
  return (
    <nav
      className="md:hidden fixed bottom-0 left-0 right-0 z-50 flex"
      style={{
        background: '#FFFFFF',
        borderTop: '1px solid #E5E7EB',
        boxShadow: '0 -1px 8px rgba(0,0,0,0.06)',
        paddingBottom: 'env(safe-area-inset-bottom, 0px)',
      }}
    >
      {NAV_ITEMS.map(({ key, label, Icon }) => {
        const active = currentPage === key;
        return (
          <button
            key={key}
            onClick={() => onNavigate(key)}
            className="flex-1 flex flex-col items-center justify-center py-2.5 border-0 cursor-pointer transition-all"
            style={{ background: 'transparent', WebkitTapHighlightColor: 'transparent' }}
          >
            <Icon
              size={20}
              strokeWidth={active ? 2.5 : 2}
              style={{ color: active ? '#2563EB' : '#9CA3AF' }}
            />
            <span
              className="text-[10px] font-medium mt-0.5"
              style={{ color: active ? '#2563EB' : '#9CA3AF' }}
            >
              {label}
            </span>
          </button>
        );
      })}
    </nav>
  );
}
