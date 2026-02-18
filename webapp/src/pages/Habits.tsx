import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { HabitCard } from '@/components/habits/HabitCard';
import { HabitForm } from '@/components/habits/HabitForm';
import { useTelegramWebApp } from '@/hooks/useTelegramWebApp';
import { useHabitStore } from '@/store/useHabitStore';
import { api } from '@/api/client';
import { useToast } from '@/hooks/useToast';
import type { Habit } from '@/types';

export function Habits() {
  const navigate = useNavigate();
  const { hapticFeedback } = useTelegramWebApp();
  const { toast } = useToast();
  const { habits, setHabits, addHabit } = useHabitStore();
  const [showForm, setShowForm] = useState(false);
  const [editingHabit, setEditingHabit] = useState<Habit | null>(null);

  const activeHabits = habits.filter((h) => h.is_active);
  const archivedHabits = habits.filter((h) => !h.is_active);

  const handleComplete = async (id: number) => {
    try {
      await api.completeHabit(id);
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
      hapticFeedback.notification('success');
    } catch (error) {
      toast({
        title: 'Ошибка',
        description: 'Не удалось отметить привычку',
        variant: 'destructive',
      });
    }
  };

  const handleCreate = async (data: any) => {
    try {
      const newHabit = await api.createHabit(data);
      addHabit(newHabit);
      setShowForm(false);
      hapticFeedback.notification('success');
      toast({
        title: 'Привычка создана!',
        description: 'Ты на верном пути к успеху 🎯',
      });
    } catch (error) {
      toast({
        title: 'Ошибка',
        description: 'Не удалось создать привычку',
        variant: 'destructive',
      });
    }
  };

  const handleEdit = (habit: Habit) => {
    setEditingHabit(habit);
    setShowForm(true);
  };

  return (
    <div className="min-h-screen">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-[var(--tg-theme-bg-color)] border-b border-[var(--tg-theme-secondary-bg-color)] safe-area-top">
        <div className="flex items-center gap-3 p-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate(-1)}
          >
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <h1 className="text-xl font-bold flex-1">Мои привычки</h1>
          <Button onClick={() => setShowForm(true)} size="sm">
            <Plus className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        <AnimatePresence mode="wait">
          {showForm ? (
            <motion.div
              key="form"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
            >
              <HabitForm
                habit={editingHabit}
                onSubmit={handleCreate}
                onCancel={() => {
                  setShowForm(false);
                  setEditingHabit(null);
                }}
              />
            </motion.div>
          ) : (
            <motion.div
              key="list"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <Tabs defaultValue="active">
                <TabsList className="w-full mb-4">
                  <TabsTrigger value="active" className="flex-1">
                    Активные ({activeHabits.length})
                  </TabsTrigger>
                  <TabsTrigger value="archived" className="flex-1">
                    Архив ({archivedHabits.length})
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="active" className="space-y-3">
                  {activeHabits.length === 0 ? (
                    <div className="text-center py-8 text-[var(--tg-theme-hint-color)]">
                      Нет активных привычек
                    </div>
                  ) : (
                    activeHabits.map((habit) => (
                      <HabitCard
                        key={habit.id}
                        habit={habit}
                        onComplete={handleComplete}
                        onClick={handleEdit}
                      />
                    ))
                  )}
                </TabsContent>

                <TabsContent value="archived" className="space-y-3">
                  {archivedHabits.length === 0 ? (
                    <div className="text-center py-8 text-[var(--tg-theme-hint-color)]">
                      Нет архивных привычек
                    </div>
                  ) : (
                    archivedHabits.map((habit) => (
                      <HabitCard
                        key={habit.id}
                        habit={habit}
                        onComplete={() => {}}
                      />
                    ))
                  )}
                </TabsContent>
              </Tabs>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
