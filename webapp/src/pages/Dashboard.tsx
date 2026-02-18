import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus, Sparkles, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { useTelegramWebApp } from '@/hooks/useTelegramWebApp';
import { useHabitStore } from '@/store/useHabitStore';
import { HabitCard } from '@/components/habits/HabitCard';
import { ProgressRing } from '@/components/habits/ProgressRing';
import { WeeklySummaryCard } from '@/components/ai/WeeklySummaryCard';
import { api } from '@/api/client';
import { getGreeting, getRandomMotivationalMessage } from '@/lib/utils';
import { useToast } from '@/hooks/useToast';
import type { Habit, WeeklySummary } from '@/types';
import confetti from 'canvas-confetti';

export function Dashboard() {
  const navigate = useNavigate();
  const { user } = useTelegramWebApp();
  const { toast } = useToast();
  const {
    habits,
    setHabits,
    getTodayProgress,
    getCompletedToday,
    getStreakData,
    isLoading,
  } = useHabitStore();

  const [weeklySummary, setWeeklySummary] = useState<WeeklySummary | null>(null);
  const [isSummaryLoading, setIsSummaryLoading] = useState(false);
  const [showConfetti, setShowConfetti] = useState(false);

  const progress = getTodayProgress();
  const completedToday = getCompletedToday();
  const totalHabits = habits.length;
  const { current: currentStreak } = getStreakData();

  // Загружаем саммари
  useEffect(() => {
    loadWeeklySummary();
  }, []);

  // Показываем конфетти при 100%
  useEffect(() => {
    if (progress === 100 && totalHabits > 0 && !showConfetti) {
      setShowConfetti(true);
      confetti({
        particleCount: 100,
        spread: 70,
        origin: { y: 0.6 },
      });
    }
  }, [progress, totalHabits, showConfetti]);

  const loadWeeklySummary = async () => {
    setIsSummaryLoading(true);
    try {
      const summary = await api.getWeeklySummary();
      setWeeklySummary(summary);
    } catch (error) {
      console.error('Failed to load weekly summary:', error);
    } finally {
      setIsSummaryLoading(false);
    }
  };

  const handleCompleteHabit = async (id: number) => {
    try {
      await api.completeHabit(id);
      
      // Обновляем локальное состояние
      const updatedHabits = habits.map((h) =>
        h.id === id
          ? {
              ...h,
              is_completed_today: true,
              total_completions: h.total_completions + 1,
              current_streak: h.current_streak + 1,
            }
          : h
      );
      setHabits(updatedHabits);

      toast({
        title: 'Отлично! 🎉',
        description: getRandomMotivationalMessage(),
      });
    } catch (error) {
      toast({
        title: 'Ошибка',
        description: 'Не удалось отметить привычку',
        variant: 'destructive',
      });
    }
  };

  const handleAddHabit = () => {
    navigate('/habits/new');
  };

  const greeting = getGreeting(user?.first_name);

  return (
    <div className="min-h-screen p-4 space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-2xl font-bold">{greeting}</h1>
          <p className="text-[var(--tg-theme-hint-color)]">
            {completedToday}/{totalHabits} привычек выполнено
          </p>
        </div>
        {user?.photo_url ? (
          <img
            src={user.photo_url}
            alt={user.first_name}
            className="w-12 h-12 rounded-full object-cover border-2 border-[var(--tg-theme-button-color)]"
          />
        ) : (
          <div className="w-12 h-12 rounded-full bg-[var(--tg-theme-button-color)] flex items-center justify-center text-white text-xl font-bold">
            {user?.first_name?.[0] || 'U'}
          </div>
        )}
      </motion.div>

      {/* Progress Ring */}
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.1 }}
        className="flex justify-center"
      >
        <ProgressRing progress={progress} size={160} strokeWidth={12}>
          <div className="text-center">
            <span className="text-4xl font-bold">{progress}%</span>
            <p className="text-sm text-[var(--tg-theme-hint-color)]">на сегодня</p>
          </div>
        </ProgressRing>
      </motion.div>

      {/* Quick Actions */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="flex gap-3"
      >
        <Button onClick={handleAddHabit} className="flex-1">
          <Plus className="w-4 h-4 mr-2" />
          Добавить
        </Button>
        <Button 
          variant="outline" 
          onClick={() => navigate('/ai')}
          className="flex-1"
        >
          <Sparkles className="w-4 h-4 mr-2" />
          AI-Помощь
        </Button>
      </motion.div>

      {/* Smart Widget - Failure Analysis */}
      {habits.some((h) => h.current_streak === 0 && h.total_completions > 0) && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
        >
          <Card 
            className="bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800 cursor-pointer"
            onClick={() => navigate('/ai')}
          >
            <CardContent className="p-4 flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-orange-500" />
              <div className="flex-1">
                <p className="font-medium text-sm">Есть срывы?</p>
                <p className="text-xs text-[var(--tg-theme-hint-color)]">
                  AI поможет разобрать причины
                </p>
              </div>
              <Button size="sm" variant="ghost">
                Разобрать
              </Button>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Habits List */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
        className="space-y-3"
      >
        <h2 className="text-lg font-semibold">Сегодня</h2>
        
        <AnimatePresence mode="popLayout">
          {habits.length === 0 ? (
            <Card className="p-8 text-center">
              <p className="text-[var(--tg-theme-hint-color)] mb-4">
                У тебя пока нет привычек
              </p>
              <Button onClick={handleAddHabit}>
                <Plus className="w-4 h-4 mr-2" />
                Создать первую
              </Button>
            </Card>
          ) : (
            habits.map((habit, index) => (
              <motion.div
                key={habit.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
              >
                <HabitCard
                  habit={habit}
                  onComplete={handleCompleteHabit}
                />
              </motion.div>
            ))
          )}
        </AnimatePresence>
      </motion.div>

      {/* Weekly Summary */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
      >
        <WeeklySummaryCard
          summary={weeklySummary}
          isLoading={isSummaryLoading}
          onRefresh={loadWeeklySummary}
        />
      </motion.div>
    </div>
  );
}
