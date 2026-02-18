import { useState } from 'react';
import { motion } from 'framer-motion';
import { Sparkles, Share2, Trophy, TrendingUp, Target } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { useTelegramWebApp } from '@/hooks/useTelegramWebApp';
import type { WeeklySummary } from '@/types';

interface WeeklySummaryCardProps {
  summary: WeeklySummary | null;
  isLoading: boolean;
  onRefresh: () => void;
}

export function WeeklySummaryCard({ summary, isLoading, onRefresh }: WeeklySummaryCardProps) {
  const [isSharing, setIsSharing] = useState(false);
  const { showPopup, hapticFeedback } = useTelegramWebApp();

  const handleShare = async () => {
    if (!summary) return;
    
    setIsSharing(true);
    hapticFeedback.impact('light');
    
    // Копируем текст для шеринга
    try {
      await navigator.clipboard.writeText(summary.share_text);
      showPopup('Отлично!', 'Текст скопирован. Поделись в своих сторис!');
    } catch {
      showPopup('Ошибка', 'Не удалось скопировать текст');
    }
    
    setIsSharing(false);
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-8 w-48" />
        </CardHeader>
        <CardContent className="space-y-4">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-16 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (!summary) {
    return (
      <Card className="text-center py-8">
        <CardContent>
          <TrendingUp className="w-12 h-12 mx-auto text-[var(--tg-theme-hint-color)] mb-4" />
          <p className="text-[var(--tg-theme-hint-color)] mb-4">
            Недостаточно данных для анализа
          </p>
          <Button onClick={onRefresh} variant="outline">
            <Sparkles className="w-4 h-4 mr-2" />
            Получить анализ
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <Card className="overflow-hidden">
        <CardHeader className="bg-gradient-to-br from-purple-500/10 to-blue-500/10">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-purple-500" />
              <CardTitle className="text-lg">Моя неделя</CardTitle>
            </div>
            {summary.is_cached && (
              <Badge variant="secondary" className="text-xs">
                Кэш
              </Badge>
            )}
          </div>
          <p className="text-sm text-[var(--tg-theme-hint-color)]">
            {new Date(summary.week_start).toLocaleDateString('ru-RU')} — {new Date(summary.week_end).toLocaleDateString('ru-RU')}
          </p>
        </CardHeader>

        <CardContent className="space-y-6 pt-6">
          {/* Stats Grid */}
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center">
              <div className="flex items-center justify-center gap-1 text-green-500 mb-1">
                <Target className="w-4 h-4" />
                <span className="text-2xl font-bold">{summary.completed_count}</span>
              </div>
              <p className="text-xs text-[var(--tg-theme-hint-color)]">Выполнено</p>
            </div>
            <div className="text-center">
              <div className="flex items-center justify-center gap-1 text-orange-500 mb-1">
                <Trophy className="w-4 h-4" />
                <span className="text-2xl font-bold">{summary.best_streak}</span>
              </div>
              <p className="text-xs text-[var(--tg-theme-hint-color)]">Лучшая серия</p>
            </div>
            <div className="text-center">
              <div className="flex items-center justify-center gap-1 text-blue-500 mb-1">
                <TrendingUp className="w-4 h-4" />
                <span className="text-2xl font-bold">{Math.round(summary.completion_rate)}%</span>
              </div>
              <p className="text-xs text-[var(--tg-theme-hint-color)]">Эффективность</p>
            </div>
          </div>

          {/* AI Summary */}
          <div className="bg-[var(--tg-theme-secondary-bg-color)] rounded-lg p-4">
            <p className="text-sm leading-relaxed">{summary.ai_summary}</p>
          </div>

          {/* Tips */}
          {summary.tips.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-medium">Советы на следующую неделю:</p>
              <ul className="space-y-2">
                {summary.tips.map((tip, index) => (
                  <motion.li
                    key={index}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.1 }}
                    className="flex items-start gap-2 text-sm text-[var(--tg-theme-hint-color)]"
                  >
                    <span className="text-[var(--tg-theme-button-color)]">•</span>
                    {tip}
                  </motion.li>
                ))}
              </ul>
            </div>
          )}

          {/* Share Button */}
          <Button 
            onClick={handleShare} 
            className="w-full"
            disabled={isSharing}
          >
            <Share2 className="w-4 h-4 mr-2" />
            Поделиться результатами
          </Button>
        </CardContent>
      </Card>
    </motion.div>
  );
}
