# -*- coding: utf-8 -*-
"""
Finance reminder service - sends notifications for payments and deposits
"""
import logging
from datetime import date, timedelta
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Payment, PaymentReminder
from app.models.base import AsyncSessionLocal

logger = logging.getLogger(__name__)


class FinanceReminderService:
    """Service for checking and sending financial reminders"""
    
    def __init__(self, bot: Bot, scheduler: AsyncIOScheduler):
        self.bot = bot
        self.scheduler = scheduler
    
    async def check_and_send_reminders(self):
        """Check and send all types of reminders"""
        today = date.today()
        
        async with AsyncSessionLocal() as db:
            try:
                # 3 days reminder
                await self._send_reminders_for_date(
                    db, today + timedelta(days=3), '3d'
                )
                
                # 1 day reminder
                await self._send_reminders_for_date(
                    db, today + timedelta(days=1), '1d'
                )
                
                # Today reminder
                await self._send_today_reminders(db, today)
                
                await db.commit()
            except Exception as e:
                logger.error(f"Error in check_and_send_reminders: {e}")
                await db.rollback()
    
    async def _send_reminders_for_date(self, db: AsyncSession, target_date: date, reminder_type: str):
        """Send reminders for specific date"""
        
        # Select appropriate flag column
        if reminder_type == '3d':
            flag_column = Payment.reminder_3d_sent
        else:
            flag_column = Payment.reminder_1d_sent
        
        result = await db.execute(
            select(Payment).where(
                and_(
                    Payment.date == target_date,
                    Payment.is_completed == False,
                    flag_column == False
                )
            )
        )
        payments = result.scalars().all()
        
        for payment in payments:
            try:
                await self._send_reminder(payment, reminder_type)
                
                # Update flag
                if reminder_type == '3d':
                    payment.reminder_3d_sent = True
                else:
                    payment.reminder_1d_sent = True
                
                # Log reminder
                reminder_log = PaymentReminder(
                    payment_id=payment.id,
                    reminder_type=reminder_type
                )
                db.add(reminder_log)
                
                logger.info(f"Sent {reminder_type} reminder for payment {payment.id}")
            except Exception as e:
                logger.error(f"Error sending reminder for payment {payment.id}: {e}")
    
    async def _send_today_reminders(self, db: AsyncSession, today: date):
        """Send today's reminders with action buttons"""
        
        result = await db.execute(
            select(Payment).where(
                and_(
                    Payment.date == today,
                    Payment.is_completed == False,
                    Payment.reminder_today_sent == False
                )
            )
        )
        payments = result.scalars().all()
        
        for payment in payments:
            try:
                await self._send_today_reminder(payment)
                
                payment.reminder_today_sent = True
                
                reminder_log = PaymentReminder(
                    payment_id=payment.id,
                    reminder_type='today'
                )
                db.add(reminder_log)
                
                logger.info(f"Sent today reminder for payment {payment.id}")
            except Exception as e:
                logger.error(f"Error sending today reminder for payment {payment.id}: {e}")
    
    async def _send_reminder(self, payment: Payment, reminder_type: str):
        """Send single reminder notification"""
        
        days_text = "через 3 дня" if reminder_type == '3d' else "завтра"
        icon = "📅" if reminder_type == '3d' else "⚠️"
        
        text = f"{icon} <b>Напоминание: {days_text} платёж!</b>\n\n"
        text += f"{'💳' if payment.type == 'payment' else '🏦'} {payment.bank}\n"
        text += f"💵 {payment.amount:,} ₽\n"
        text += f"📅 {payment.date.strftime('%d.%m.%Y')}\n"
        
        if payment.description:
            text += f"📝 {payment.description}\n"
        
        if reminder_type == '1d':
            text += "\n<i>💡 Убедитесь, что средства на счёте</i>"
        
        await self.bot.send_message(
            payment.user_id,
            text,
            parse_mode="HTML"
        )
    
    async def _send_today_reminder(self, payment: Payment):
        """Send today's reminder with action buttons"""
        
        text = "🔔 <b>Сегодня день платежа!</b>\n\n"
        text += f"{'💳' if payment.type == 'payment' else '🏦'} {payment.bank}\n"
        text += f"💵 <b>{payment.amount:,} ₽</b>\n"
        
        if payment.description:
            text += f"📝 {payment.description}\n"
        
        kb = InlineKeyboardBuilder()
        kb.button(text="✅ Выполнено", callback_data=f"payment_done:{payment.id}")
        kb.button(text="❌ Пропустить", callback_data=f"payment_skip:{payment.id}")
        kb.adjust(2)
        
        await self.bot.send_message(
            payment.user_id,
            text,
            reply_markup=kb.as_markup(),
            parse_mode="HTML"
        )
    
    def schedule(self, hour: int = 9, minute: int = 0):
        """Schedule daily reminder check"""
        self.scheduler.add_job(
            self.check_and_send_reminders,
            CronTrigger(hour=hour, minute=minute),
            id="finance_reminders",
            replace_existing=True
        )
        logger.info(f"Scheduled finance reminders at {hour:02d}:{minute:02d}")


async def send_payment_reminder_manual(bot: Bot, payment_id: int, db: AsyncSession):
    """Send manual reminder for a specific payment (for admin use)"""
    result = await db.execute(
        select(Payment).where(Payment.id == payment_id)
    )
    payment = result.scalar_one_or_none()
    
    if not payment:
        return False
    
    text = f"🔔 <b>Напоминание о платеже</b>\n\n"
    text += f"{'💳' if payment.type == 'payment' else '🏦'} {payment.bank}\n"
    text += f"💵 <b>{payment.amount:,} ₽</b>\n"
    text += f"📅 {payment.date.strftime('%d.%m.%Y')}\n"
    
    if payment.description:
        text += f"📝 {payment.description}\n"
    
    days_left = (payment.date - date.today()).days
    if days_left > 0:
        text += f"\n⏳ Осталось: {days_left} дн."
    elif days_left == 0:
        text += "\n⚠️ <b>Сегодня!</b>"
    
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Выполнено", callback_data=f"payment_done:{payment.id}")
    kb.button(text="❌ Пропустить", callback_data=f"payment_skip:{payment.id}")
    kb.adjust(2)
    
    await bot.send_message(
        payment.user_id,
        text,
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )
    return True
