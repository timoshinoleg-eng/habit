import { useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowLeft, Clock, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useTelegramWebApp } from '@/hooks/useTelegramWebApp';
import { api } from '@/api/client';
import type { Habit } from '@/types';

interface HabitFormProps {
  habit?: Habit | null;
  onSubmit: (data: any) => void;
  onCancel: () => void;
}

const EMOJIS = [
  '✅', '💪', '🏃', '📚', '💧', '🧘', '🥗', '💊',
  '🎯', '⭐', '🔥', '❤️', '🌟', '⚡', '🎨', '🎵'
];

const FREQUENCIES = [
  { value: 'daily', label: 'Каждый день' },
  { value: 'weekdays', label: 'По будням' },
  { value: 'weekends', label: 'По выходным' },
  { value: 'weekly', label: 'Раз в неделю' },
];

export function HabitForm({ habit, onSubmit, onCancel }: HabitFormProps) {
  const [name, setName] = useState(habit?.name || '');
  const [description, setDescription] = useState(habit?.description || '');
  const [emoji, setEmoji] = useState(habit?.emoji || '✅');
  const [frequency, setFrequency] = useState(habit?.frequency || 'daily');
  const [reminderTime, setReminderTime] = useState(habit?.reminder_time || '');
  const [isLoading, setIsLoading] = useState(false);
  const [suggestion, setSuggestion] = useState<any>(null);
  
  const { hapticFeedback, showPopup } = useTelegramWebApp();

  const handleNameChange = async (value: string) => {
    setName(value);
    
    // AI suggestion after 3 characters
    if (value.length >= 3 && !suggestion) {
      try {
        const result = await api.suggestHabit(value);
        setSuggestion(result);
      } catch (e) {
        // Ignore errors
      }
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    hapticFeedback.impact('medium');
    onSubmit({
      name: name.trim(),
      description: description.trim() || undefined,
      emoji,
      frequency,
      reminder_time: reminderTime || undefined,
    });
  };

  const applySuggestion = () => {
    if (!suggestion) return;
    
    setName(suggestion.suggested_name);
    setEmoji(suggestion.suggested_emoji);
    setReminderTime(suggestion.suggested_time || '');
    hapticFeedback.notification('success');
    setSuggestion(null);
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={onCancel}>
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <h2 className="text-xl font-bold">
          {habit ? 'Редактировать' : 'Новая привычка'}
        </h2>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Name */}
        <div className="space-y-2">
          <Label>Название</Label>
          <Input
            value={name}
            onChange={(e) => handleNameChange(e.target.value)}
            placeholder="Например: Утренняя зарядка"
            className="h-12"
          />
        </div>

        {/* AI Suggestion */}
        {suggestion && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-[var(--tg-theme-secondary-bg-color)] rounded-lg p-4"
          >
            <div className="flex items-start gap-3">
              <Sparkles className="w-5 h-5 text-[var(--tg-theme-button-color)] mt-0.5" />
              <div className="flex-1">
                <p className="text-sm font-medium">AI предлагает:</p>
                <p className="text-sm text-[var(--tg-theme-hint-color)] mt-1">
                  {suggestion.suggested_name} {suggestion.suggested_emoji}
                </p>
                <p className="text-xs text-[var(--tg-theme-hint-color)] mt-1">
                  {suggestion.reasoning}
                </p>
              </div>
              <Button size="sm" onClick={applySuggestion}>
                Применить
              </Button>
            </div>
          </motion.div>
        )}

        {/* Emoji */}
        <div className="space-y-2">
          <Label>Иконка</Label>
          <div className="grid grid-cols-8 gap-2">
            {EMOJIS.map((e) => (
              <button
                key={e}
                type="button"
                onClick={() => {
                  setEmoji(e);
                  hapticFeedback.selection();
                }}
                className={`w-10 h-10 rounded-lg text-xl transition-all ${
                  emoji === e
                    ? 'bg-[var(--tg-theme-button-color)] text-white scale-110'
                    : 'bg-[var(--tg-theme-secondary-bg-color)] hover:bg-[var(--tg-theme-button-color)]/10'
                }`}
              >
                {e}
              </button>
            ))}
          </div>
        </div>

        {/* Frequency */}
        <div className="space-y-2">
          <Label>Частота</Label>
          <div className="grid grid-cols-2 gap-2">
            {FREQUENCIES.map((f) => (
              <button
                key={f.value}
                type="button"
                onClick={() => {
                  setFrequency(f.value);
                  hapticFeedback.selection();
                }}
                className={`p-3 rounded-lg text-sm font-medium transition-all ${
                  frequency === f.value
                    ? 'bg-[var(--tg-theme-button-color)] text-white'
                    : 'bg-[var(--tg-theme-secondary-bg-color)] text-[var(--tg-theme-text-color)]'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {/* Reminder Time */}
        <div className="space-y-2">
          <Label className="flex items-center gap-2">
            <Clock className="w-4 h-4" />
            Время напоминания
          </Label>
          <Input
            type="time"
            value={reminderTime}
            onChange={(e) => setReminderTime(e.target.value)}
            className="h-12"
          />
        </div>

        {/* Description */}
        <div className="space-y-2">
          <Label>Описание (необязательно)</Label>
          <Input
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Дополнительные детали..."
          />
        </div>

        {/* Submit */}
        <Button 
          type="submit" 
          className="w-full h-12"
          disabled={!name.trim() || isLoading}
        >
          {habit ? 'Сохранить' : 'Создать привычку'}
        </Button>
      </form>
    </motion.div>
  );
}
