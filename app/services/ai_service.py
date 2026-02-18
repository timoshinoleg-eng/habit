"""
Сервис для интеграции с OpenRouter API.
Обеспечивает AI-рекомендации и персонализированные напоминания.
"""

import json
import logging
from datetime import datetime, date
from typing import List, Optional, Dict, Any

import aiohttp

from app.config import settings
from app.models import User, Habit, HabitLog, AIContext
from app.services.database import DatabaseService

logger = logging.getLogger(__name__)


class AIService:
    """Сервис для работы с AI через OpenRouter API."""
    
    # Бесплатные модели OpenRouter (можно менять)
    DEFAULT_MODEL = "meta-llama/llama-3.1-8b-instruct"
    FALLBACK_MODEL = "mistralai/mistral-7b-instruct"
    
    def __init__(self, db_service: DatabaseService):
        self.db = db_service
        self.api_key = settings.openrouter_api_key or ""
        self.base_url = settings.openrouter_base_url
        self.model = settings.openrouter_model or self.DEFAULT_MODEL
        self.enabled = bool(settings.openrouter_api_key)
        
        # Сессия будет создаваться при необходимости
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Получение HTTP-сессии (lazy initialization)."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://habitmax-bot.local",
                    "X-Title": "HabitMax Telegram Bot"
                },
                timeout=timeout
            )
        return self._session
    
    async def close(self) -> None:
        """Закрытие HTTP-сессии."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def _make_request(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 500,
        model: Optional[str] = None
    ) -> Optional[str]:
        """
        Выполнение запроса к OpenRouter API.
        
        Returns None if AI is disabled.
        
        Args:
            messages: Список сообщений для chat completion
            temperature: Температура генерации (0-1)
            max_tokens: Максимальное количество токенов
            model: Модель (если None - используется дефолтная)
        
        Returns:
            Текст ответа или None при ошибке
        """
        if not self.enabled:
            return None
            
        session = await self._get_session()
        
        payload = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            async with session.post(
                f"{self.base_url}/chat/completions",
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"OpenRouter API error: {response.status} - {error_text}")
                    
                    # Пробуем fallback модель
                    if model != self.FALLBACK_MODEL:
                        logger.info(f"Trying fallback model: {self.FALLBACK_MODEL}")
                        return await self._make_request(
                            messages, temperature, max_tokens, self.FALLBACK_MODEL
                        )
                    return None
                
                data = await response.json()
                
                if "choices" in data and len(data["choices"]) > 0:
                    return data["choices"][0]["message"]["content"].strip()
                else:
                    logger.error(f"Unexpected response format: {data}")
                    return None
                    
        except aiohttp.ClientError as e:
            logger.error(f"Network error when calling OpenRouter: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in AI request: {e}")
            return None
    
    # ==================== AI Рекомендации ====================
    
    async def get_habit_recommendation(
        self,
        user: User,
        habit: Optional[Habit] = None,
        recent_logs: Optional[List[HabitLog]] = None
    ) -> str:
        """
        Генерация AI-рекомендации по привычке на основе истории.
        
        Args:
            user: Пользователь
            habit: Конкретная привычка (если None - общая рекомендация)
            recent_logs: Недавние логи (если None - загружаются из БД)
        
        Returns:
            Текст рекомендации
        """
        # Проверяем, включен ли AI
        if not self.enabled:
            return self._get_fallback_recommendation(habit)
        
        # Получаем AI-контекст пользователя
        ai_context = await self.db.get_or_create_ai_context(user.id)
        
        # Формируем контекст для промпта
        context_summary = ai_context.get_summary_for_prompt()
        
        # Получаем логи если не переданы
        if habit and not recent_logs:
            recent_logs = await self.db.get_habit_logs(habit.id, user.id, days=14)
        
        # Формируем историю выполнения (кратко для экономии токенов)
        history_summary = self._format_history_summary(recent_logs or [])
        
        # Формируем промпт
        if habit:
            system_prompt = """Ты - дружелюбный помощник по формированию привычек. 
Давай краткие, конкретные советы на русском языке (2-3 предложения).
Будь мотивирующим, но не навязчивым."""
            
            user_prompt = f"""Привычка: {habit.name}
Эмодзи: {habit.emoji}
Текущая серия: {habit.current_streak} дней
Лучшая серия: {habit.best_streak} дней
История (14 дней): {history_summary}
Контекст пользователя: {context_summary}

Дай персонализированный совет по улучшению выполнения этой привычки."""
        else:
            # Общая рекомендация
            habits = await self.db.get_user_habits(user.id)
            habits_info = ", ".join([f"{h.emoji} {h.name} (серия: {h.current_streak})" for h in habits[:5]])
            
            system_prompt = """Ты - мотиватор по формированию привычек. 
Дай один конкретный, вдохновляющий совет на русском языке (2-3 предложения)."""
            
            user_prompt = f"""Привычки пользователя: {habits_info or "пока нет"}
Контекст: {context_summary}

Дай общий совет по формированию полезных привычек."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = await self._make_request(messages, temperature=0.8, max_tokens=300)
        
        if response:
            # Сохраняем рекомендацию в контекст
            await self._save_recommendation_to_context(user.id, response)
            return response
        
        # Fallback на шаблонный ответ
        return self._get_fallback_recommendation(habit)
    
    async def get_personalized_reminder(
        self,
        user: User,
        habit: Habit,
        day_of_week: Optional[str] = None,
        time_of_day: Optional[str] = None
    ) -> str:
        """
        Генерация персонализированного напоминания от AI.
        
        Args:
            user: Пользователь
            habit: Привычка для напоминания
            day_of_week: День недели (для контекста)
            time_of_day: Время суток (morning/afternoon/evening)
        
        Returns:
            Текст напоминания
        """
        # Если AI не настроен, возвращаем стандартное напоминание
        if not self.enabled:
            return (
                f"{habit.emoji} Не забудь про привычку \"{habit.name}\"! "
                f"Текущая серия: {habit.current_streak} дней 💪"
            )
        
        # Получаем AI-контекст
        ai_context = await self.db.get_or_create_ai_context(user.id)
        
        # Определяем время суток
        if not time_of_day and habit.reminder_time:
            hour = habit.reminder_time.hour
            if 5 <= hour < 12:
                time_of_day = "morning"
            elif 12 <= hour < 17:
                time_of_day = "afternoon"
            else:
                time_of_day = "evening"
        
        # Определяем день недели
        if not day_of_week:
            days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            day_of_week = days[datetime.now().weekday()]
        
        # Определяем стиль напоминания
        style = ai_context.preferred_reminder_style or "friendly"
        
        # Формируем промпт в зависимости от стиля
        if style == "strict":
            system_prompt = """Ты строгий, но заботливый тренер. 
Напомни о привычке кратко и по делу (1-2 предложения). Без воды."""
        elif style == "motivational":
            system_prompt = """Ты энергичный мотиватор. 
Напомни о привычке с энтузиазмом и позитивом (2-3 предложения)."""
        else:  # friendly
            system_prompt = """Ты дружелюбный помощник. 
Напомни о привычке тепло и поддерживающе (2 предложения)."""
        
        # Контекст для персонализации
        context_parts = [f"серия: {habit.current_streak} дней"]
        if habit.current_streak > habit.best_streak * 0.8:
            context_parts.append("близко к рекорду!")
        elif habit.current_streak == 0:
            context_parts.append("начинаем заново")
        
        user_prompt = f"""Напомни пользователю {user.first_name} о привычке "{habit.emoji} {habit.name}".
Время: {time_of_day}, День: {day_of_week}
Статус: {', '.join(context_parts)}

Напиши персонализированное напоминание на русском языке."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = await self._make_request(messages, temperature=0.7, max_tokens=200)
        
        if response:
            return response
        
        # Fallback
        return f"{habit.emoji} Не забудь про привычку \"{habit.name}\"! Текущая серия: {habit.current_streak} дней 💪"
    
    async def analyze_user_patterns(self, user_id: int) -> Dict[str, Any]:
        """
        Анализ паттернов пользователя для обновления AI-контекста.
        
        Args:
            user_id: ID пользователя
        
        Returns:
            Словарь с выявленными паттернами
        """
        # Получаем все привычки и логи
        habits = await self.db.get_user_habits(user_id)
        
        if not habits:
            return {}
        
        # Анализируем логи
        all_logs = []
        for habit in habits:
            logs = await self.db.get_habit_logs(habit.id, user_id, days=90)
            all_logs.extend(logs)
        
        if not all_logs:
            return {}
        
        # Определяем самый продуктивный день
        day_counts = {i: 0 for i in range(7)}
        for log in all_logs:
            if log.status == "completed":
                day_counts[log.completed_date.weekday()] += 1
        
        best_day = max(day_counts, key=day_counts.get)
        day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        most_productive_day = day_names[best_day]
        
        # Определяем самое продуктивное время
        hour_counts = {}
        for log in all_logs:
            if log.status == "completed":
                hour = log.completed_at.hour if log.completed_at else 12
                hour_counts[hour] = hour_counts.get(hour, 0) + 1
        
        if hour_counts:
            best_hour = max(hour_counts, key=hour_counts.get)
            if 5 <= best_hour < 12:
                most_productive_time = "morning"
            elif 12 <= best_hour < 17:
                most_productive_time = "afternoon"
            else:
                most_productive_time = "evening"
        else:
            most_productive_time = None
        
        # Определяем проблемные привычки
        struggling_habits = []
        for habit in habits:
            logs = await self.db.get_habit_logs(habit.id, user_id, days=30)
            if not logs:
                continue
            
            failed_count = sum(1 for log in logs if log.status in ["failed", "skipped"])
            total_count = len(logs)
            
            if total_count > 5 and failed_count / total_count > 0.5:
                struggling_habits.append(habit.name)
        
        # Обновляем AI-контекст
        ai_context = await self.db.get_or_create_ai_context(user_id)
        
        update_data = {
            "most_productive_day": most_productive_day,
            "most_productive_time": most_productive_time,
        }
        
        if struggling_habits:
            ai_context.set_struggling_habits(struggling_habits)
            update_data["struggling_habits"] = ai_context.struggling_habits
        
        await self.db.update_ai_context(user_id, **update_data)
        
        return {
            "most_productive_day": most_productive_day,
            "most_productive_time": most_productive_time,
            "struggling_habits": struggling_habits,
        }
    
    # ==================== Helper Methods ====================
    
    def _format_history_summary(self, logs: List[HabitLog]) -> str:
        """Форматирование истории в краткую строку для промпта."""
        if not logs:
            return "нет данных"
        
        # Группируем по статусу
        completed = sum(1 for log in logs if log.status == "completed")
        failed = sum(1 for log in logs if log.status in ["failed", "skipped"])
        
        # Проверяем паттерн (последние 3 записи)
        recent = sorted(logs, key=lambda x: x.completed_date, reverse=True)[:3]
        recent_pattern = ", ".join([log.status[:3] for log in recent])
        
        return f"выполнено:{completed}, пропущено:{failed}, последние:[{recent_pattern}]"
    
    def _get_fallback_recommendation(self, habit: Optional[Habit]) -> str:
        """Шаблонная рекомендация при недоступности AI."""
        if habit:
            if habit.current_streak == 0:
                return f"💡 Не переживай из-за пропуска! Попробуй выполнить '{habit.name}' прямо сейчас или установи напоминание на более удобное время."
            elif habit.current_streak < 7:
                return f"💡 Отлично, что продолжаешь! Чтобы закрепить '{habit.name}', попробуй привязать её к уже существующей привычке."
            else:
                return f"🔥 Крутая серия в {habit.current_streak} дней! Продолжай в том же духе с '{habit.name}'."
        return "💡 Регулярность важнее интенсивности. Даже 5 минут в день лучше, чем час раз в неделю!"
    
    async def _save_recommendation_to_context(
        self,
        user_id: int,
        recommendation: str
    ) -> None:
        """Сохранение рекомендации в контекст (храним последние 5)."""
        ai_context = await self.db.get_or_create_ai_context(user_id)
        
        try:
            existing = json.loads(ai_context.last_ai_recommendations or "[]")
        except json.JSONDecodeError:
            existing = []
        
        # Добавляем новую и храним только последние 5
        existing.append({
            "date": datetime.now().isoformat(),
            "text": recommendation[:200]  # Только начало для экономии места
        })
        existing = existing[-5:]
        
        await self.db.update_ai_context(
            user_id,
            last_ai_recommendations=json.dumps(existing, ensure_ascii=False)
        )
