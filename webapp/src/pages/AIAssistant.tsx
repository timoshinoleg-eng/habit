import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, MessageCircle, AlertTriangle, TrendingUp, Wand2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { WeeklySummaryCard } from '@/components/ai/WeeklySummaryCard';
import { FailureAnalysisModal } from '@/components/ai/FailureAnalysisModal';
import { AIChat } from '@/components/ai/AIChat';
import { useTelegramWebApp } from '@/hooks/useTelegramWebApp';
import { useHabitStore } from '@/store/useHabitStore';
import { api } from '@/api/client';
import type { WeeklySummary, FailureAnalysis } from '@/types';

export function AIAssistant() {
  const navigate = useNavigate();
  const { hapticFeedback } = useTelegramWebApp();
  const { habits } = useHabitStore();
  
  const [weeklySummary, setWeeklySummary] = useState<WeeklySummary | null>(null);
  const [failureAnalysis, setFailureAnalysis] = useState<FailureAnalysis | null>(null);
  const [showFailureModal, setShowFailureModal] = useState(false);
  const [showChat, setShowChat] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const hasFailures = habits.some((h) => h.current_streak === 0 && h.total_completions > 0);

  const loadWeeklySummary = async () => {
    setIsLoading(true);
    try {
      const summary = await api.getWeeklySummary();
      setWeeklySummary(summary);
      hapticFeedback.notification('success');
    } catch (error) {
      console.error('Failed to load weekly summary:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const loadFailureAnalysis = async () => {
    setIsLoading(true);
    try {
      const analysis = await api.analyzeFailures();
      setFailureAnalysis(analysis);
      setShowFailureModal(true);
    } catch (error) {
      console.error('Failed to load failure analysis:', error);
    } finally {
      setIsLoading(false);
    }
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
          <h1 className="text-xl font-bold flex-1">AI-Помощник</h1>
        </div>
      </div>

      {/* Content */}
      <div className="p-4 space-y-6">
        {/* Quick Actions */}
        <div className="grid grid-cols-2 gap-3">
          <Button
            variant="outline"
            className="h-auto py-4 flex flex-col items-center gap-2"
            onClick={() => setShowChat(true)}
          >
            <MessageCircle className="w-6 h-6" />
            <span className="text-sm">Задать вопрос</span>
          </Button>
          
          {hasFailures && (
            <Button
              variant="outline"
              className="h-auto py-4 flex flex-col items-center gap-2 border-orange-500/50 text-orange-500"
              onClick={loadFailureAnalysis}
            >
              <AlertTriangle className="w-6 h-6" />
              <span className="text-sm">Разобрать срывы</span>
            </Button>
          )}
        </div>

        {/* Tabs */}
        <Tabs defaultValue="summary">
          <TabsList className="w-full">
            <TabsTrigger value="summary" className="flex-1">
              <TrendingUp className="w-4 h-4 mr-2" />
              Саммари
            </TabsTrigger>
            <TabsTrigger value="suggestions" className="flex-1">
              <Wand2 className="w-4 h-4 mr-2" />
              Идеи
            </TabsTrigger>
          </TabsList>

          <TabsContent value="summary" className="mt-4">
            <WeeklySummaryCard
              summary={weeklySummary}
              isLoading={isLoading}
              onRefresh={loadWeeklySummary}
            />
          </TabsContent>

          <TabsContent value="suggestions" className="mt-4 space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Популярные привычки</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {[
                  { name: 'Утренняя зарядка', emoji: '🏃', desc: '15 минут упражнений' },
                  { name: 'Чтение', emoji: '📚', desc: '30 минут в день' },
                  { name: 'Медитация', emoji: '🧘', desc: '10 минут' },
                  { name: 'Вода', emoji: '💧', desc: '2 литра в день' },
                ].map((item, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.1 }}
                    className="flex items-center gap-3 p-3 rounded-lg bg-[var(--tg-theme-secondary-bg-color)] cursor-pointer hover:bg-[var(--tg-theme-button-color)]/10"
                    onClick={() => {
                      hapticFeedback.impact('light');
                      navigate('/habits/new');
                    }}
                  >
                    <span className="text-2xl">{item.emoji}</span>
                    <div className="flex-1">
                      <p className="font-medium">{item.name}</p>
                      <p className="text-sm text-[var(--tg-theme-hint-color)]">{item.desc}</p>
                    </div>
                    <Button size="sm" variant="ghost">+</Button>
                  </motion.div>
                ))}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      {/* Modals */}
      <FailureAnalysisModal
        isOpen={showFailureModal}
        onClose={() => setShowFailureModal(false)}
        analysis={failureAnalysis}
        isLoading={isLoading}
      />

      <AIChat
        isOpen={showChat}
        onClose={() => setShowChat(false)}
      />
    </div>
  );
}
