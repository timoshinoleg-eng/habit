# HabitMax Mini App

Telegram Mini App для трекера привычек с AI-функциями.

## Архитектура

```
habitmax_telegram_bot/
├── api/                    # FastAPI бэкенд
│   ├── main.py            # Точка входа
│   ├── middleware/        # Middleware (Telegram auth)
│   ├── models/            # SQLAlchemy модели
│   ├── routers/           # API endpoints
│   ├── schemas/           # Pydantic схемы
│   └── services/          # Бизнес-логика
├── webapp/                # React фронтенд
│   ├── src/
│   │   ├── components/    # UI компоненты
│   │   ├── hooks/         # React hooks
│   │   ├── pages/         # Страницы
│   │   ├── store/         # Zustand store
│   │   └── api/           # API клиент
│   └── package.json
└── app/                   # Существующий бот
```

## Быстрый старт

### 1. Бэкенд (FastAPI)

```bash
cd api

# Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Установить зависимости
pip install fastapi uvicorn sqlalchemy aiosqlite pydantic-settings aiohttp

# Настроить переменные окружения
cp .env.example .env
# Отредактировать .env

# Запустить
uvicorn main:app --reload --port 8000
```

### 2. Фронтенд (React)

```bash
cd webapp

# Установить зависимости
npm install

# Настроить API URL
cp .env.example .env.local
# Отредактировать VITE_API_URL

# Запустить dev сервер
npm run dev
```

### 3. Настройка Telegram Bot

1. Откройте @BotFather
2. Отправьте `/mybots`
3. Выберите ваш бот
4. Нажмите **Menu Button** → **Configure menu button**
5. Установите URL: `https://your-domain.com` (или `http://localhost:3000` для разработки)

## Функции

### AI-Функции

1. **Еженедельное саммари** - AI анализирует неделю и генерирует мотивирующий отчет
2. **Анализ срывов** - Помогает понять причины пропусков и предлагает стратегии
3. **AI-Чат** - Задавайте вопросы о привычках
4. **Smart Suggestions** - AI предлагает иконки и время при создании привычки

### Кэширование

- AI-ответы кэшируются на 1 час
- Повторные запросы отдают закэшированный результат
- Fallback на шаблоны при недоступности OpenRouter

## Деплой

### Backend (Railway/Render)

```bash
# Procfile
web: uvicorn api.main:app --host 0.0.0.0 --port $PORT
```

### Frontend (Vercel)

```bash
# Настройки сборки
Build Command: npm run build
Output Directory: dist
Root Directory: webapp
```

### Environment Variables

**Backend:**
- `BOT_TOKEN` - Токен Telegram бота
- `DATABASE_URL` - URL базы данных
- `OPENROUTER_API_KEY` - API ключ OpenRouter

**Frontend:**
- `VITE_API_URL` - URL бэкенда API

## Безопасность

- Валидация `initData` через HMAC-SHA256
- Проверка подписи Telegram
- CORS настроен для конкретных доменов
- Rate limiting через кэширование AI-запросов

## Лицензия

MIT
