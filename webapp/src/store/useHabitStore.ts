import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import type { Habit, User, WeeklySummary, FailureAnalysis, WeeklyProgress } from '@/types';

interface HabitState {
  // Data
  habits: Habit[];
  user: User | null;
  weeklySummary: WeeklySummary | null;
  failureAnalysis: FailureAnalysis | null;
  weeklyProgress: WeeklyProgress | null;
  
  // UI State
  isLoading: boolean;
  error: string | null;
  selectedHabitId: number | null;
  
  // Actions
  setHabits: (habits: Habit[]) => void;
  addHabit: (habit: Habit) => void;
  updateHabit: (id: number, updates: Partial<Habit>) => void;
  removeHabit: (id: number) => void;
  completeHabit: (id: number) => void;
  setUser: (user: User) => void;
  setWeeklySummary: (summary: WeeklySummary) => void;
  setFailureAnalysis: (analysis: FailureAnalysis) => void;
  setWeeklyProgress: (progress: WeeklyProgress) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  selectHabit: (id: number | null) => void;
  
  // Computed
  getTodayProgress: () => number;
  getCompletedToday: () => number;
  getStreakData: () => { current: number; best: number };
}

export const useHabitStore = create<HabitState>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial state
        habits: [],
        user: null,
        weeklySummary: null,
        failureAnalysis: null,
        weeklyProgress: null,
        isLoading: false,
        error: null,
        selectedHabitId: null,

        // Actions
        setHabits: (habits) => set({ habits }),
        
        addHabit: (habit) => set((state) => ({
          habits: [...state.habits, habit],
        })),
        
        updateHabit: (id, updates) => set((state) => ({
          habits: state.habits.map((h) =>
            h.id === id ? { ...h, ...updates } : h
          ),
        })),
        
        removeHabit: (id) => set((state) => ({
          habits: state.habits.filter((h) => h.id !== id),
        })),
        
        completeHabit: (id) => set((state) => ({
          habits: state.habits.map((h) =>
            h.id === id
              ? {
                  ...h,
                  is_completed_today: true,
                  total_completions: h.total_completions + 1,
                  current_streak: h.current_streak + 1,
                }
              : h
          ),
        })),
        
        setUser: (user) => set({ user }),
        setWeeklySummary: (summary) => set({ weeklySummary: summary }),
        setFailureAnalysis: (analysis) => set({ failureAnalysis: analysis }),
        setWeeklyProgress: (progress) => set({ weeklyProgress: progress }),
        setLoading: (isLoading) => set({ isLoading }),
        setError: (error) => set({ error }),
        selectHabit: (id) => set({ selectedHabitId: id }),

        // Computed
        getTodayProgress: () => {
          const { habits } = get();
          if (habits.length === 0) return 0;
          const completed = habits.filter((h) => h.is_completed_today).length;
          return Math.round((completed / habits.length) * 100);
        },
        
        getCompletedToday: () => {
          return get().habits.filter((h) => h.is_completed_today).length;
        },
        
        getStreakData: () => {
          const { habits } = get();
          const current = habits.length > 0
            ? Math.min(...habits.map((h) => h.current_streak))
            : 0;
          const best = habits.length > 0
            ? Math.max(...habits.map((h) => h.best_streak))
            : 0;
          return { current, best };
        },
      }),
      {
        name: 'habitmax-storage',
        partialize: (state) => ({
          user: state.user,
          habits: state.habits,
        }),
      }
    )
  )
);
