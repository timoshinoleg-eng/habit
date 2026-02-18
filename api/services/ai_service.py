"""
Сервис для работы с AI (OpenRouter).
Кэширование, rate limiting, fallback.
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional

import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete

from app.config import settings
from api.models.base import AIRequestCache
from api.schemas.ai import (
    AIAdviceResponse,
    AIChatResponse,
    FailureAnalysisResponse,
    FailurePattern,
    Strategy,
    WeeklySummaryData,
    WeeklySummaryResponse,
)

logger = logging.getLogger(__name__)


class AIService:
    """Сервис для AI-запросов с кэшированием."""
    
    def __init__(self):
        self.api_key = settings.openrouter_api_key
        self.base_url = settings.openrouter_base_url
        self.model = settings.openrouter_model
        self.fallback_model = settings.openrouter_fallback_model
        self.max_tokens = 500
        self.cache_ttl_hours = 1
        
        # Fallback шаблоны
        self.fallback_summaries = [
            "📊 Отличная неделя! Ты на верном пути к формированию устойчивых привычек. Продолжай в том же духе!",
            "🌟 Хороший прогресс! Каждый день приближает тебя к цели. Не останавливайся!",
            "💪 Ты делаешь важные шаги к лучшей версии себя. Сохраняй этот ритм!",
        ]
        
        self.fallback_strategies = [
            Strategy(
                title="Начни с малого",
                description="Разбей привычку на очень маленькие шаги",
                action_steps=["Сделай минимум 2 минуты", "Отметь выполнение", "Постепенно увеличивай"],
                difficulty="easy",
                estimated_effectiveness=4
            ),
            Strategy(
                title="Привяжи к существующей привычке",
                description="Используй метод 'stacking' - прикрепи новую привычку к уже существующей",
                action_steps=["Вырай якорь", "Свяжи действия", "Практикуй 7 дней"],
                difficulty="easy",
                estimated_effectiveness=5
            ),
            Strategy(
                title="Измени окружение",
                description="Сделай выполнение привычки максимально удобным",
                action_steps=["Убери препятствия", "Подготовь всё заранее", "Установи напоминания"],
                difficulty="medium",
                estimated_effectiveness=4
            ),
        ]
    
    def _generate_cache_key(self, request_type: str, params: dict) -> str:
        """Генерация ключа кэша."""
        data = json.dumps(params, sort_keys=True, default=str)
        return hashlib.sha256(f"{request_type}:{data}".encode()).hexdigest()
    
    async def _get_cached_response(
        self,
        session: AsyncSession,
        user_id: int,
        request_type: str,
        params: dict
    ) -> Optional[dict]:
        """Получение закэшированного ответа."""
        cache_key = self._generate_cache_key(request_type, params)
        
        from api.models.base import AIRequestCache
        result = await session.execute(
            select(AIRequestCache).where(
                and_(
                    AIRequestCache.user_id == user_id,
                    AIRequestCache.request_type == request_type,
                    AIRequestCache.request_hash == cache_key,
                    AIRequestCache.expires_at > datetime.utcnow()
                )
            )
        )
        cache = result.scalar_one_or_none()
        
        if cache:
            logger.info(f"Cache hit for {request_type}, user {user_id}")
            return json.loads(cache.response_data)
        return None
    
    async def _cache_response(
        self,
        session: AsyncSession,
        user_id: int,
        request_type: str,
        params: dict,
        response: dict
    ):
        """Сохранение ответа в кэш."""
        cache_key = self._generate_cache_key(request_type, params)
        
        # Удаляем старый кэш
        await session.execute(
            delete(AIRequestCache).where(
                and_(
                    AIRequestCache.user_id == user_id,
                    AIRequestCache.request_type == request_type
                )
            )
        )
        
        # Создаем новый
        cache = AIRequestCache(
            user_id=user_id,
            request_type=request_type,
            request_hash=cache_key,
            response_data=json.dumps(response),
            expires_at=datetime.utcnow() + timedelta(hours=self.cache_ttl_hours)
        )
        session.add(cache)
        await session.commit()
    
    async def _make_request(
        self,
        messages: List[dict],
        max_tokens: int = 500,
        model: Optional[str] = None
    ) -> Optional[str]:
        """Отправка запроса в OpenRouter."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://t.me/habitmax_bot",
            "X-Title": "HabitMax"
        }
        
        payload = {
            "model": model or self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data["choices"][0]["message"]["content"]
                    elif response.status == 429:
                        logger.warning("Rate limit exceeded")
                        return None
                    else:
                        text = await response.text()
                        logger.error(f"OpenRouter error: {response.status} - {text}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error making AI request: {e}")
            return None
    
    async def generate_weekly_summary(
        self,
        session: AsyncSession,
        user_id: int,
        data: WeeklySummaryData
    ) -> WeeklySummaryResponse:
        """Генерация еженедельного саммари."""
        
        # Проверяем кэш
        params = {
            "week_start": data.week_start.isoformat(),
            "week_end": data.week_end.isoformat(),
            "completed": data.completed_count,
            "total": data.total_habits
        }
        
        cached = await self._get_cached_response(session, user_id, "weekly_summary", params)
        if cached:
            return WeeklySummaryResponse(**cached, is_cached=True)
        
        # Подготовка промпта (pre-summary)
        completion_rate = data.completed_count / max(data.total_habits * 7, 1) * 100
        
        prompt = f"""Ты — мотивирующий коуч по привычкам. Проанализируй неделю пользователя:

СТАТИСТИКА:
- Привычек: {data.total_habits}
- Выполнено: {data.completed_count}
- Пропущено: {data.skipped_count}
- Лучшая серия: {data.best_streak} дней
- Процент выполнения: {completion_rate:.1f}%
- Лучшая привычка: {data.best_habit or 'не определена'}

Напиши:
1. Один мотивирующий абзац (3-4 предложения) — похвали за успехи, поддержи при неудачах
2. Три конкретных совета на следующую неделю
3. Краткий текст для шеринга (до 100 символов)

Тон: дружелюбный, энергичный, без осуждения."""

        messages = [
            {"role": "system", "content": "Ты — дружелюбный коуч по привычкам. Пиши кратко, мотивирующе, на русском языке."},
            {"role": "user", "content": prompt}
        ]
        
        response = await self._make_request(messages, max_tokens=400)
        
        if response:
            # Парсим ответ
            lines = response.strip().split("\n")
            summary = lines[0] if lines else self.fallback_summaries[0]
            
            # Извлекаем советы
            tips = [line.strip("- •") for line in lines if line.strip().startswith(("-", "•", "1.", "2.", "3."))]
            tips = tips[:3] if tips else ["Продолжай отслеживать привычки", "Отмечай выполнение каждый день", "Не сдавайся при срывах"]
            
            # Шеринг текст
            share_text = f"🔥 {data.best_streak} дней серии! {data.completed_count} выполнений на этой неделе. #HabitMax"
            
            result = WeeklySummaryResponse(
                week_start=data.week_start,
                week_end=data.week_end,
                total_habits=data.total_habits,
                completed_count=data.completed_count,
                skipped_count=data.skipped_count,
                best_streak=data.best_streak,
                completion_rate=completion_rate,
                ai_summary=summary,
                motivational_message=summary,
                tips=tips,
                generated_at=datetime.utcnow(),
                is_cached=False,
                share_text=share_text
            )
        else:
            # Fallback
            import random
            result = WeeklySummaryResponse(
                week_start=data.week_start,
                week_end=data.week_end,
                total_habits=data.total_habits,
                completed_count=data.completed_count,
                skipped_count=data.skipped_count,
                best_streak=data.best_streak,
                completion_rate=completion_rate,
                ai_summary=random.choice(self.fallback_summaries),
                motivational_message="Ты на правильном пути! Каждый день — это шаг вперед.",
                tips=[
                    "Отмечай привычки сразу после выполнения",
                    "Установи напоминания на удобное время",
                    "Начни с одной привычки, а не нескольких"
                ],
                generated_at=datetime.utcnow(),
                is_cached=False,
                share_text=f"💪 {data.completed_count} выполнений на этой неделе! #HabitMax"
            )
        
        # Кэшируем
        await self._cache_response(session, user_id, "weekly_summary", params, result.model_dump())
        
        return result
    
    async def analyze_failures(
        self,
        session: AsyncSession,
        user_id: int,
        habit_name: Optional[str],
        failure_count: int,
        skip_reasons: List[str],
        patterns: List[FailurePattern]
    ) -> FailureAnalysisResponse:
        """Анализ срывов привычки."""
        
        # Проверяем кэш
        params = {
            "habit": habit_name or "all",
            "failures": failure_count,
            "reasons": skip_reasons
        }
        
        cached = await self._get_cached_response(session, user_id, "failure_analysis", params)
        if cached:
            return FailureAnalysisResponse(**cached, is_cached=True)
        
        # Подготовка промпта
        patterns_text = "\n".join([
            f"- {p.day_of_week}, {p.time_of_day or 'не указано'}: {p.reason or 'причина не указана'} ({p.frequency} раз)"
            for p in patterns[:5]
        ])
        
        reasons_text = "\n".join([f"- {r}" for r in skip_reasons[:5]]) if skip_reasons else "Причины не указаны"
        
        prompt = f"""Проанализируй срывы привычки и предложи стратегии.

ПРИВЫЧКА: {habit_name or 'Общий анализ'}
ПРОПУСКОВ: {failure_count}

ПАТТЕРНЫ ПРОПУСКОВ:
{patterns_text}

УКАЗАННЫЕ ПРИЧИНЫ:
{reasons_text}

Сформи ответ:
1. Эмпатичное сообщение поддержки (1-2 предложения)
2. 3 возможные причины срывов
3. 3 конкретные стратегии с actionable steps

Тон: поддерживающий, никакого осуждения."""

        messages = [
            {"role": "system", "content": "Ты — поддерживающий психолог-коуч. Помогай преодолевать трудности без осуждения."},
            {"role": "user", "content": prompt}
        ]
        
        response = await self._make_request(messages, max_tokens=500)
        
        if response:
            # Парсим ответ (упрощенно)
            lines = response.strip().split("\n")
            
            # Ищем эмпатичное сообщение
            empathetic = "Все мы иногда спотыкаемся. Главное — не сдаваться!"
            root_causes = []
            strategies = []
            
            current_section = None
            for line in lines:
                line = line.strip()
                if "причина" in line.lower() or "почему" in line.lower():
                    current_section = "causes"
                    continue
                if "стратег" in line.lower() or "решени" in line.lower():
                    current_section = "strategies"
                    continue
                
                if line.startswith(("-", "•", "1.", "2.", "3.")):
                    text = line.strip("- •123. ")
                    if current_section == "causes":
                        root_causes.append(text)
                    elif current_section == "strategies":
                        strategies.append(text)
            
            if not root_causes:
                root_causes = ["Недостаточно мотивации", "Слишком сложная цель", "Отсутствие напоминаний"]
            
            # Создаем стратегии
            ai_strategies = []
            for i, s in enumerate(strategies[:3]):
                ai_strategies.append(Strategy(
                    title=f"Стратегия {i+1}",
                    description=s,
                    action_steps=["Начни сегодня", "Отслеживай прогресс", "Не сдавайся"],
                    difficulty="medium",
                    estimated_effectiveness=4
                ))
            
            if not ai_strategies:
                ai_strategies = self.fallback_strategies[:3]
            
            result = FailureAnalysisResponse(
                habit_id=None,
                habit_name=habit_name,
                failure_count=failure_count,
                failure_rate=failure_count / 30 * 100,  # Примерный расчет
                common_patterns=patterns,
                skip_reasons=skip_reasons,
                empathetic_message=empathetic,
                root_causes=root_causes[:3],
                strategies=ai_strategies,
                generated_at=datetime.utcnow(),
                is_cached=False
            )
        else:
            # Fallback
            result = FailureAnalysisResponse(
                habit_id=None,
                habit_name=habit_name,
                failure_count=failure_count,
                failure_rate=failure_count / 30 * 100,
                common_patterns=patterns,
                skip_reasons=skip_reasons,
                empathetic_message="Все мы иногда спотыкаемся. Главное — не сдаваться и учиться на ошибках! 💪",
                root_causes=["Слишком амбициозная цель", "Неудобное время", "Отсутствие поддержки"],
                strategies=self.fallback_strategies[:3],
                generated_at=datetime.utcnow(),
                is_cached=False
            )
        
        # Кэшируем
        await self._cache_response(session, user_id, "failure_analysis", params, result.model_dump())
        
        return result
    
    async def get_advice(
        self,
        session: AsyncSession,
        user_id: int,
        context: str,
        habit_name: Optional[str] = None
    ) -> AIAdviceResponse:
        """Получение AI-совета."""
        
        # Проверяем кэш
        params = {"context": context, "habit": habit_name}
        cached = await self._get_cached_response(session, user_id, "advice", params)
        if cached:
            return AIAdviceResponse(**cached, is_cached=True)
        
        prompt = f"""Дай краткий совет по формированию привычки.

КОНТЕКСТ: {context}
ПРИВЫЧКА: {habit_name or 'не указана'}

Ответь одним абзацем (2-3 предложения) с конкретным actionable советом."""

        messages = [
            {"role": "system", "content": "Ты — эксперт по привычкам. Давай краткие, практичные советы."},
            {"role": "user", "content": prompt}
        ]
        
        response = await self._make_request(messages, max_tokens=200)
        
        if response:
            result = AIAdviceResponse(
                advice=response.strip(),
                category="strategy",
                confidence=0.8,
                is_cached=False
            )
        else:
            result = AIAdviceResponse(
                advice="Начни с малого — даже 2 минуты лучше, чем ничего. Постепенно увеличивай время!",
                category="motivation",
                confidence=0.5,
                is_cached=False
            )
        
        # Кэшируем на час
        await self._cache_response(session, user_id, "advice", params, result.model_dump())
        return result
