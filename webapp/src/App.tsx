import { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useTelegramWebApp } from '@/hooks/useTelegramWebApp';
import { useHabitStore } from '@/store/useHabitStore';
import { api } from '@/api/client';
import { Dashboard } from '@/pages/Dashboard';
import { Habits } from '@/pages/Habits';
import { AIAssistant } from '@/pages/AIAssistant';
import { Settings } from '@/pages/Settings';
import { BottomNav } from '@/components/layout/BottomNav';
import { Toaster } from '@/components/ui/toaster';

function App() {
  const { ready, initData, theme } = useTelegramWebApp();
  const { setHabits, setUser, setLoading, setError } = useHabitStore();

  // Устанавливаем initData для API
  useEffect(() => {
    if (initData) {
      api.setInitData(initData);
    }
  }, [initData]);

  // Применяем тему
  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [theme]);

  // Загружаем данные при старте
  useEffect(() => {
    if (!ready || !initData) return;

    const loadData = async () => {
      setLoading(true);
      try {
        const [habitsData, userData] = await Promise.all([
          api.getHabits(),
          api.getUserProfile(),
        ]);
        setHabits(habitsData.habits || []);
        setUser(userData);
      } catch (err) {
        console.error('Failed to load data:', err);
        setError('Не удалось загрузить данные');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [ready, initData, setHabits, setUser, setLoading, setError]);

  if (!ready) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[var(--tg-theme-button-color)]" />
      </div>
    );
  }

  return (
    <div className="min-h-screen pb-20">
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/habits" element={<Habits />} />
        <Route path="/habits/new" element={<Habits />} />
        <Route path="/ai" element={<AIAssistant />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <BottomNav />
      <Toaster />
    </div>
  );
}

export default App;
