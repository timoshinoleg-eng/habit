import axios, { AxiosInstance, AxiosError } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiClient {
  private client: AxiosInstance;
  private initData: string = '';

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        if (this.initData) {
          config.headers['X-Telegram-Init-Data'] = this.initData;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          // Обработка ошибки авторизации
          console.error('Telegram auth failed');
        }
        return Promise.reject(error);
      }
    );
  }

  setInitData(initData: string) {
    this.initData = initData;
  }

  // Habits
  async getHabits() {
    const { data } = await this.client.get('/api/habits');
    return data;
  }

  async createHabit(habit: {
    name: string;
    description?: string;
    emoji: string;
    reminder_time?: string;
    frequency: string;
  }) {
    const { data } = await this.client.post('/api/habits', habit);
    return data;
  }

  async updateHabit(id: number, updates: Partial<typeof habit>) {
    const { data } = await this.client.patch(`/api/habits/${id}`, updates);
    return data;
  }

  async deleteHabit(id: number) {
    const { data } = await this.client.delete(`/api/habits/${id}`);
    return data;
  }

  async completeHabit(id: number, notes?: string, mood?: number) {
    const { data } = await this.client.post(`/api/habits/${id}/complete`, {
      notes,
      mood,
    });
    return data;
  }

  async skipHabit(id: number, reason?: string) {
    const { data } = await this.client.post(`/api/habits/${id}/skip`, null, {
      params: { reason },
    });
    return data;
  }

  async getWeeklyProgress() {
    const { data } = await this.client.get('/api/habits/progress/weekly');
    return data;
  }

  // AI
  async getWeeklySummary() {
    const { data } = await this.client.get('/api/ai/weekly-summary');
    return data;
  }

  async analyzeFailures(habitId?: number, periodDays: number = 30) {
    const { data } = await this.client.post('/api/ai/failure-analysis', {
      habit_id: habitId,
      period_days: periodDays,
    });
    return data;
  }

  async getAdvice(context: string, habitId?: number) {
    const { data } = await this.client.post('/api/ai/advice', {
      context,
      habit_id: habitId,
    });
    return data;
  }

  async chatWithAI(message: string, history: any[] = []) {
    const { data } = await this.client.post('/api/ai/chat', {
      message,
      history,
    });
    return data;
  }

  async suggestHabit(query: string) {
    const { data } = await this.client.post('/api/ai/suggest-habit', null, {
      params: { query },
    });
    return data;
  }

  // User
  async getMe() {
    const { data } = await this.client.get('/api/me');
    return data;
  }

  async getUserProfile() {
    const { data } = await this.client.get('/api/user/me');
    return data;
  }

  async updateSettings(settings: {
    ai_enabled?: boolean;
    notification_enabled?: boolean;
    timezone?: string;
    theme?: string;
  }) {
    const { data } = await this.client.patch('/api/user/settings', settings);
    return data;
  }

  async completeOnboarding(data: { timezone: string; goals: string[] }) {
    const { data: response } = await this.client.post('/api/user/onboarding/complete', data);
    return response;
  }
}

export const api = new ApiClient();
