import { useEffect, useState, useCallback } from 'react';
import WebApp from '@twa-dev/sdk';
import type { TelegramUser } from '@/types';

interface UseTelegramWebAppReturn {
  ready: boolean;
  user: TelegramUser | null;
  initData: string;
  isExpanded: boolean;
  theme: 'light' | 'dark';
  expand: () => void;
  close: () => void;
  showMainButton: (text: string, onClick: () => void) => void;
  hideMainButton: () => void;
  showBackButton: (onClick: () => void) => void;
  hideBackButton: () => void;
  showPopup: (title: string, message: string) => void;
  showConfirm: (message: string) => Promise<boolean>;
  hapticFeedback: {
    impact: (style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft') => void;
    notification: (type: 'error' | 'success' | 'warning') => void;
    selection: () => void;
  };
}

export function useTelegramWebApp(): UseTelegramWebAppReturn {
  const [ready, setReady] = useState(false);
  const [user, setUser] = useState<TelegramUser | null>(null);
  const [initData, setInitData] = useState('');
  const [isExpanded, setIsExpanded] = useState(false);
  const [theme, setTheme] = useState<'light' | 'dark'>('light');

  useEffect(() => {
    // Инициализация Telegram Web App
    WebApp.ready();
    WebApp.expand();

    // Получаем данные пользователя
    const tgUser = WebApp.initDataUnsafe.user;
    if (tgUser) {
      setUser({
        id: tgUser.id,
        first_name: tgUser.first_name,
        last_name: tgUser.last_name,
        username: tgUser.username,
        language_code: tgUser.language_code,
        photo_url: tgUser.photo_url,
      });
    }

    setInitData(WebApp.initData);
    setIsExpanded(true);
    setTheme(WebApp.colorScheme === 'dark' ? 'dark' : 'light');
    setReady(true);

    // Устанавливаем цвета из темы Telegram
    if (WebApp.setHeaderColor) {
      WebApp.setHeaderColor('secondary_bg_color');
    }
    if (WebApp.setBackgroundColor) {
      WebApp.setBackgroundColor('secondary_bg_color');
    }

    // Слушаем изменение темы
    WebApp.onEvent('themeChanged', () => {
      setTheme(WebApp.colorScheme === 'dark' ? 'dark' : 'light');
    });

    return () => {
      WebApp.offEvent('themeChanged', () => {});
    };
  }, []);

  const expand = useCallback(() => {
    WebApp.expand();
  }, []);

  const close = useCallback(() => {
    WebApp.close();
  }, []);

  const showMainButton = useCallback((text: string, onClick: () => void) => {
    WebApp.MainButton.setText(text);
    WebApp.MainButton.onClick(onClick);
    WebApp.MainButton.show();
  }, []);

  const hideMainButton = useCallback(() => {
    WebApp.MainButton.hide();
    WebApp.MainButton.offClick(() => {});
  }, []);

  const showBackButton = useCallback((onClick: () => void) => {
    WebApp.BackButton.onClick(onClick);
    WebApp.BackButton.show();
  }, []);

  const hideBackButton = useCallback(() => {
    WebApp.BackButton.hide();
    WebApp.BackButton.offClick(() => {});
  }, []);

  const showPopup = useCallback((title: string, message: string) => {
    WebApp.showPopup({
      title,
      message,
      buttons: [{ id: 'ok', text: 'OK', type: 'default' }],
    });
  }, []);

  const showConfirm = useCallback((message: string): Promise<boolean> => {
    return new Promise((resolve) => {
      WebApp.showConfirm(message, (confirmed) => {
        resolve(confirmed);
      });
    });
  }, []);

  const hapticFeedback = {
    impact: (style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft') => {
      WebApp.HapticFeedback.impactOccurred(style);
    },
    notification: (type: 'error' | 'success' | 'warning') => {
      WebApp.HapticFeedback.notificationOccurred(type);
    },
    selection: () => {
      WebApp.HapticFeedback.selectionChanged();
    },
  };

  return {
    ready,
    user,
    initData,
    isExpanded,
    theme,
    expand,
    close,
    showMainButton,
    hideMainButton,
    showBackButton,
    hideBackButton,
    showPopup,
    showConfirm,
    hapticFeedback,
  };
}
