import { useLocation, useNavigate } from 'react-router-dom';
import { Home, ListTodo, Sparkles, Settings } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useTelegramWebApp } from '@/hooks/useTelegramWebApp';

const navItems = [
  { path: '/', icon: Home, label: 'Главная' },
  { path: '/habits', icon: ListTodo, label: 'Привычки' },
  { path: '/ai', icon: Sparkles, label: 'AI' },
  { path: '/settings', icon: Settings, label: 'Настройки' },
];

export function BottomNav() {
  const location = useLocation();
  const navigate = useNavigate();
  const { hapticFeedback } = useTelegramWebApp();

  const handleClick = (path: string) => {
    hapticFeedback.selection();
    navigate(path);
  };

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 safe-area-bottom">
      <div className="bg-[var(--tg-theme-bg-color)] border-t border-[var(--tg-theme-secondary-bg-color)] px-4 py-2">
        <div className="flex items-center justify-around max-w-md mx-auto">
          {navItems.map(({ path, icon: Icon, label }) => {
            const isActive = location.pathname === path || 
              (path !== '/' && location.pathname.startsWith(path));
            
            return (
              <button
                key={path}
                onClick={() => handleClick(path)}
                className={cn(
                  "flex flex-col items-center gap-1 px-3 py-2 rounded-lg transition-colors",
                  isActive 
                    ? "text-[var(--tg-theme-button-color)]" 
                    : "text-[var(--tg-theme-hint-color)]"
                )}
              >
                <Icon className={cn(
                  "w-6 h-6 transition-transform",
                  isActive && "scale-110"
                )} />
                <span className="text-xs font-medium">{label}</span>
              </button>
            );
          })}
        </div>
      </div>
    </nav>
  );
}
