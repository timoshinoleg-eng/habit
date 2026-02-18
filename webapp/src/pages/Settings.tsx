import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  ArrowLeft, 
  Moon, 
  Bell, 
  Brain, 
  Globe, 
  Download,
  LogOut,
  ChevronRight
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { useTelegramWebApp } from '@/hooks/useTelegramWebApp';
import { useHabitStore } from '@/store/useHabitStore';
import { api } from '@/api/client';
import { useToast } from '@/hooks/useToast';

export function Settings() {
  const navigate = useNavigate();
  const { theme, close } = useTelegramWebApp();
  const { toast } = useToast();
  const { user } = useHabitStore();

  const handleExport = async () => {
    try {
      // TODO: Implement export
      toast({
        title: 'Экспорт данных',
        description: 'Функция в разработке',
      });
    } catch (error) {
      toast({
        title: 'Ошибка',
        description: 'Не удалось экспортировать данные',
      });
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
          <h1 className="text-xl font-bold flex-1">Настройки</h1>
        </div>
      </div>

      {/* Content */}
      <div className="p-4 space-y-6">
        {/* Profile Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="w-16 h-16 rounded-full bg-[var(--tg-theme-button-color)] flex items-center justify-center text-white text-2xl font-bold">
                  {user?.first_name?.[0] || 'U'}
                </div>
                <div>
                  <h2 className="font-bold text-lg">
                    {user?.first_name} {user?.last_name}
                  </h2>
                  <p className="text-sm text-[var(--tg-theme-hint-color)]">
                    @{user?.username || 'username'}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Settings Groups */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="space-y-4"
        >
          {/* Appearance */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Moon className="w-4 h-4" />
                Внешний вид
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Темная тема</p>
                  <p className="text-sm text-[var(--tg-theme-hint-color)]">
                    Текущая: {theme === 'dark' ? 'Темная' : 'Светлая'}
                  </p>
                </div>
                <Switch checked={theme === 'dark'} disabled />
              </div>
            </CardContent>
          </Card>

          {/* Notifications */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Bell className="w-4 h-4" />
                Уведомления
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Включены</p>
                  <p className="text-sm text-[var(--tg-theme-hint-color)]">
                    Напоминания о привычках
                  </p>
                </div>
                <Switch defaultChecked />
              </div>
            </CardContent>
          </Card>

          {/* AI */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Brain className="w-4 h-4" />
                AI-Функции
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">AI-Помощник</p>
                  <p className="text-sm text-[var(--tg-theme-hint-color)]">
                    Персональные рекомендации
                  </p>
                </div>
                <Switch defaultChecked />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Еженедельное саммари</p>
                  <p className="text-sm text-[var(--tg-theme-hint-color)]">
                    Автоматический анализ
                  </p>
                </div>
                <Switch defaultChecked />
              </div>
            </CardContent>
          </Card>

          {/* Data */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Download className="w-4 h-4" />
                Данные
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Button 
                variant="outline" 
                className="w-full justify-between"
                onClick={handleExport}
              >
                <span>Экспорт данных</span>
                <ChevronRight className="w-4 h-4" />
              </Button>
            </CardContent>
          </Card>
        </motion.div>

        {/* Close Button */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
        >
          <Button 
            variant="outline" 
            className="w-full text-red-500 border-red-500/50"
            onClick={close}
          >
            <LogOut className="w-4 h-4 mr-2" />
            Закрыть приложение
          </Button>
        </motion.div>

        {/* Version */}
        <p className="text-center text-xs text-[var(--tg-theme-hint-color)]">
          HabitMax v1.0.0
        </p>
      </div>
    </div>
  );
}
