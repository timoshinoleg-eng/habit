import { useState } from 'react';
import { motion } from 'framer-motion';
import { Check, Flame, MoreHorizontal, Clock } from 'lucide-react';
import { cn, formatTime } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { useTelegramWebApp } from '@/hooks/useTelegramWebApp';
import type { Habit } from '@/types';

interface HabitCardProps {
  habit: Habit;
  onComplete: (id: number) => void;
  onClick?: (habit: Habit) => void;
}

export function HabitCard({ habit, onComplete, onClick }: HabitCardProps) {
  const [isCompleting, setIsCompleting] = useState(false);
  const { hapticFeedback } = useTelegramWebApp();

  const handleComplete = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (habit.is_completed_today || isCompleting) return;

    setIsCompleting(true);
    hapticFeedback.impact('medium');
    
    try {
      await onComplete(habit.id);
    } finally {
      setIsCompleting(false);
    }
  };

  const progress = Math.min(100, habit.progress_percentage);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95 }}
      whileTap={{ scale: 0.98 }}
    >
      <Card
        onClick={() => onClick?.(habit)}
        className={cn(
          "p-4 cursor-pointer transition-all duration-200",
          "hover:shadow-md border-l-4",
          habit.is_completed_today 
            ? "border-l-green-500 bg-green-50/50 dark:bg-green-900/10" 
            : "border-l-[var(--tg-theme-button-color)]"
        )}
      >
        <div className="flex items-start gap-4">
          {/* Emoji & Checkbox */}
          <div className="flex flex-col items-center gap-2">
            <motion.div
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              onClick={handleComplete}
              className={cn(
                "w-14 h-14 rounded-2xl flex items-center justify-center text-3xl cursor-pointer transition-all",
                habit.is_completed_today
                  ? "bg-green-500 text-white shadow-lg shadow-green-500/30"
                  : "bg-[var(--tg-theme-secondary-bg-color)] hover:bg-[var(--tg-theme-button-color)]/10"
              )}
            >
              {habit.is_completed_today ? (
                <Check className="w-7 h-7" />
              ) : (
                <span>{habit.emoji}</span>
              )}
            </motion.div>
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2">
              <div>
                <h3 className={cn(
                  "font-semibold text-lg truncate",
                  habit.is_completed_today && "line-through opacity-60"
                )}>
                  {habit.name}
                </h3>
                {habit.description && (
                  <p className="text-sm text-[var(--tg-theme-hint-color)] line-clamp-1">
                    {habit.description}
                  </p>
                )}
              </div>
            </div>

            {/* Stats Row */}
            <div className="flex items-center gap-4 mt-2 text-sm">
              {habit.current_streak > 0 && (
                <div className="flex items-center gap-1 text-orange-500">
                  <Flame className="w-4 h-4 streak-fire" />
                  <span className="font-medium">{habit.current_streak}</span>
                </div>
              )}
              
              {habit.reminder_time && (
                <div className="flex items-center gap-1 text-[var(--tg-theme-hint-color)]">
                  <Clock className="w-4 h-4" />
                  <span>{formatTime(habit.reminder_time)}</span>
                </div>
              )}

              <div className="flex-1">
                <div className="h-1.5 bg-[var(--tg-theme-secondary-bg-color)] rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${progress}%` }}
                    transition={{ duration: 0.5 }}
                    className={cn(
                      "h-full rounded-full",
                      progress >= 100 
                        ? "bg-green-500" 
                        : "bg-[var(--tg-theme-button-color)]"
                    )}
                  />
                </div>
              </div>

              <span className="text-xs text-[var(--tg-theme-hint-color)] min-w-[40px]">
                {Math.round(progress)}%
              </span>
            </div>
          </div>

          {/* Options */}
          <Button
            variant="ghost"
            size="icon"
            className="shrink-0"
            onClick={(e) => {
              e.stopPropagation();
              // Open options menu
            }}
          >
            <MoreHorizontal className="w-5 h-5 text-[var(--tg-theme-hint-color)]" />
          </Button>
        </div>
      </Card>
    </motion.div>
  );
}
