export interface TelegramUser {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  language_code?: string;
  photo_url?: string;
}

export interface Habit {
  id: number;
  name: string;
  description?: string;
  emoji: string;
  reminder_time?: string;
  frequency: string;
  target_days: number;
  is_active: boolean;
  current_streak: number;
  best_streak: number;
  total_completions: number;
  progress_percentage: number;
  is_completed_today: boolean;
  created_at: string;
}

export interface HabitLog {
  id: number;
  completed_date: string;
  status: 'completed' | 'skipped' | 'failed';
  notes?: string;
  mood?: number;
}

export interface WeeklySummary {
  week_start: string;
  week_end: string;
  total_habits: number;
  completed_count: number;
  skipped_count: number;
  best_streak: number;
  completion_rate: number;
  ai_summary: string;
  motivational_message: string;
  tips: string[];
  generated_at: string;
  is_cached: boolean;
  share_text: string;
}

export interface FailurePattern {
  day_of_week: string;
  time_of_day?: string;
  reason?: string;
  frequency: number;
}

export interface Strategy {
  title: string;
  description: string;
  action_steps: string[];
  difficulty: 'easy' | 'medium' | 'hard';
  estimated_effectiveness: number;
}

export interface FailureAnalysis {
  habit_id?: number;
  habit_name?: string;
  failure_count: number;
  failure_rate: number;
  common_patterns: FailurePattern[];
  skip_reasons: string[];
  empathetic_message: string;
  root_causes: string[];
  strategies: Strategy[];
  generated_at: string;
  is_cached: boolean;
}

export interface UserSettings {
  ai_enabled: boolean;
  notification_enabled: boolean;
  timezone: string;
  theme: 'light' | 'dark' | 'system';
}

export interface UserStats {
  total_habits: number;
  active_habits: number;
  total_completions: number;
  best_streak: number;
  current_streak: number;
  completion_rate_7d: number;
  completion_rate_30d: number;
}

export interface User {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  settings: UserSettings;
  stats: UserStats;
  created_at: string;
  last_active?: string;
}

export interface DayProgress {
  date: string;
  completed: number;
  total: number;
  percentage: number;
}

export interface WeeklyProgress {
  week_start: string;
  week_end: string;
  days: DayProgress[];
  total_completed: number;
  total_habits: number;
  average_percentage: number;
}
