import { motion, AnimatePresence } from 'framer-motion';
import { X, AlertTriangle, Lightbulb, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Skeleton } from '@/components/ui/skeleton';
import type { FailureAnalysis } from '@/types';

interface FailureAnalysisModalProps {
  isOpen: boolean;
  onClose: () => void;
  analysis: FailureAnalysis | null;
  isLoading: boolean;
}

export function FailureAnalysisModal({
  isOpen,
  onClose,
  analysis,
  isLoading,
}: FailureAnalysisModalProps) {
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-orange-500" />
            <DialogTitle>Давай разберемся</DialogTitle>
          </div>
        </DialogHeader>

        {isLoading ? (
          <div className="space-y-4">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
        ) : analysis ? (
          <div className="space-y-6">
            {/* Empathetic Message */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-orange-50 dark:bg-orange-900/20 rounded-lg p-4"
            >
              <p className="text-sm leading-relaxed">{analysis.empathetic_message}</p>
            </motion.div>

            {/* Stats */}
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center p-3 bg-[var(--tg-theme-secondary-bg-color)] rounded-lg">
                <p className="text-2xl font-bold text-orange-500">{analysis.failure_count}</p>
                <p className="text-xs text-[var(--tg-theme-hint-color)]">Пропусков</p>
              </div>
              <div className="text-center p-3 bg-[var(--tg-theme-secondary-bg-color)] rounded-lg">
                <p className="text-2xl font-bold">{Math.round(analysis.failure_rate)}%</p>
                <p className="text-xs text-[var(--tg-theme-hint-color)]">Процент срывов</p>
              </div>
            </div>

            {/* Patterns */}
            {analysis.common_patterns.length > 0 && (
              <div>
                <h4 className="font-medium mb-2 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4" />
                  Паттерны пропусков
                </h4>
                <div className="space-y-2">
                  {analysis.common_patterns.map((pattern, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between p-2 bg-[var(--tg-theme-secondary-bg-color)] rounded-lg text-sm"
                    >
                      <span>{pattern.day_of_week}</span>
                      <span className="text-orange-500 font-medium">{pattern.frequency} раз</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Root Causes */}
            {analysis.root_causes.length > 0 && (
              <div>
                <h4 className="font-medium mb-2">Возможные причины:</h4>
                <ul className="space-y-2">
                  {analysis.root_causes.map((cause, i) => (
                    <motion.li
                      key={i}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.1 }}
                      className="flex items-start gap-2 text-sm"
                    >
                      <span className="text-orange-500">•</span>
                      {cause}
                    </motion.li>
                  ))}
                </ul>
              </div>
            )}

            {/* Strategies */}
            <div>
              <h4 className="font-medium mb-3 flex items-center gap-2">
                <Lightbulb className="w-4 h-4 text-[var(--tg-theme-button-color)]" />
                Рекомендации AI
              </h4>
              <div className="space-y-3">
                {analysis.strategies.map((strategy, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.15 }}
                    className="border border-[var(--tg-theme-secondary-bg-color)] rounded-lg p-3"
                  >
                    <div className="flex items-start gap-2">
                      <CheckCircle2 className="w-5 h-5 text-green-500 shrink-0 mt-0.5" />
                      <div>
                        <h5 className="font-medium text-sm">{strategy.title}</h5>
                        <p className="text-xs text-[var(--tg-theme-hint-color)] mt-1">
                          {strategy.description}
                        </p>
                        <div className="flex items-center gap-2 mt-2">
                          <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--tg-theme-secondary-bg-color)]">
                            {strategy.difficulty === 'easy' ? 'Легко' : 
                             strategy.difficulty === 'medium' ? 'Средне' : 'Сложно'}
                          </span>
                          <span className="text-xs text-[var(--tg-theme-hint-color)]">
                            Эффективность: {strategy.estimated_effectiveness}/5
                          </span>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>

            {analysis.is_cached && (
              <p className="text-xs text-center text-[var(--tg-theme-hint-color)]">
                Результат из кэша
              </p>
            )}
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
