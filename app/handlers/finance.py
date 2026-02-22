# -*- coding: utf-8 -*-
"""
Finance handlers - payments and deposits management
"""
import asyncio
import logging
from datetime import datetime, date, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Payment, PaymentReminder
from app.models.user import User
from config.settings import BANKS

logger = logging.getLogger(__name__)
router = Router()


class AddPaymentFSM(StatesGroup):
    """FSM for adding payment/deposit"""
    type = State()       # payment or deposit
    bank = State()       # bank selection
    amount = State()     # amount
    date = State()       # due/closing date
    open_date = State()  # deposit open date (only for deposits)
    description = State() # description
    confirm = State()    # confirmation


# ============================================================================
# Command handlers
# ============================================================================

@router.message(Command("add_payment"))
async def cmd_add_payment(message: Message, state: FSMContext):
    """Start adding payment/deposit"""
    kb = InlineKeyboardBuilder()
    kb.button(text="💳 Платёж", callback_data="payment_type:payment")
    kb.button(text="🏦 Вклад", callback_data="payment_type:deposit")
    kb.adjust(2)
    
    await message.answer(
        "💰 <b>Добавление финансового напоминания</b>\n\n"
        "Выберите тип:",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )
    await state.set_state(AddPaymentFSM.type)


@router.message(Command("my_finances"))
async def cmd_my_finances(message: Message, db: AsyncSession):
    """Show all financial reminders"""
    await show_finances_list(message, db, message.from_user.id)


async def show_finances_list(message_or_callback, db: AsyncSession, user_id: int, edit=False):
    """Helper to show finances list"""
    
    # Get active payments
    result = await db.execute(
        select(Payment).where(
            Payment.user_id == user_id,
            Payment.is_completed == False,
            Payment.date >= date.today()
        ).order_by(Payment.date)
    )
    payments = result.scalars().all()
    
    # Get completed payments (last 5)
    completed_result = await db.execute(
        select(Payment).where(
            Payment.user_id == user_id,
            Payment.is_completed == True
        ).order_by(desc(Payment.completed_at)).limit(5)
    )
    completed_payments = completed_result.scalars().all()
    
    if not payments and not completed_payments:
        text = (
            "💰 <b>Ваши финансы</b>\n\n"
            "У вас нет активных финансовых напоминаний.\n\n"
            "Добавить: /add_payment"
        )
        kb = InlineKeyboardBuilder()
        kb.button(text="➕ Добавить", callback_data="finance:add")
        
        if isinstance(message_or_callback, Message):
            await message_or_callback.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")
        else:
            await message_or_callback.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")
        return
    
    text = "💰 <b>Ваши финансовые напоминания</b>\n\n"
    
    # Active payments
    if payments:
        text += "<b>📋 Активные:</b>\n"
        for p in payments:
            icon = "💳" if p.type == 'payment' else '🏦'
            days_left = (p.date - date.today()).days
            
            text += f"\n{icon} <b>{p.bank}</b>\n"
            text += f"💵 {p.amount:,} ₽\n"
            text += f"📅 {p.date.strftime('%d.%m.%Y')}"
            
            if days_left > 0:
                text += f" (через {days_left} дн.)"
            elif days_left == 0:
                text += " 🔔 Сегодня!"
            
            if p.description:
                text += f"\n📝 {p.description}"
            text += "\n"
    
    # Recently completed
    if completed_payments:
        text += f"\n<b>✅ Недавно выполнено:</b>\n"
        for p in completed_payments:
            icon = "💳" if p.type == 'payment' else '🏦'
            text += f"\n{icon} {p.bank} - {p.amount:,} ₽"
    
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Добавить", callback_data="finance:add")
    kb.button(text="🗑 Архив", callback_data="finance:archive")
    kb.adjust(2)
    
    if isinstance(message_or_callback, Message):
        await message_or_callback.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    else:
        await message_or_callback.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")


# ============================================================================
# FSM Handlers
# ============================================================================

@router.callback_query(AddPaymentFSM.type, F.data.startswith("payment_type:"))
async def process_type(callback: CallbackQuery, state: FSMContext):
    """Process payment type selection"""
    ptype = callback.data.split(":")[1]
    await state.update_data(type=ptype)
    
    kb = InlineKeyboardBuilder()
    for bank in BANKS:
        kb.button(text=bank, callback_data=f"payment_bank:{bank}")
    kb.adjust(2)
    
    type_text = "💳 Платёж" if ptype == 'payment' else "🏦 Вклад"
    await callback.message.edit_text(
        f"{type_text}\n\n"
        "🏦 Выберите банк:",
        reply_markup=kb.as_markup()
    )
    await state.set_state(AddPaymentFSM.bank)


@router.callback_query(AddPaymentFSM.bank, F.data.startswith("payment_bank:"))
async def process_bank(callback: CallbackQuery, state: FSMContext):
    """Process bank selection"""
    bank = callback.data.split(":")[1]
    await state.update_data(bank=bank)
    
    await callback.message.edit_text(
        f"🏦 Банк: <b>{bank}</b>\n\n"
        "💵 Введите сумму (например: 150000):",
        parse_mode="HTML"
    )
    await state.set_state(AddPaymentFSM.amount)


@router.message(AddPaymentFSM.amount)
async def process_amount(message: Message, state: FSMContext):
    """Process amount input"""
    try:
        # Clean input
        amount_text = message.text.replace(" ", "").replace("₽", "").replace(",", "")
        amount = int(amount_text)
        if amount <= 0:
            raise ValueError
        await state.update_data(amount=amount)
    except ValueError:
        await message.answer("❌ Введите корректную сумму (например: 150000)")
        return
    
    data = await state.get_data()
    
    if data['type'] == 'deposit':
        await message.answer(
            "📅 Введите дату <b>открытия</b> вклада (ДД.ММ.ГГГГ):",
            parse_mode="HTML"
        )
        await state.set_state(AddPaymentFSM.open_date)
    else:
        await message.answer(
            "📅 Введите дату платежа (ДД.ММ.ГГГГ):",
            parse_mode="HTML"
        )
        await state.set_state(AddPaymentFSM.date)


@router.message(AddPaymentFSM.open_date)
async def process_open_date(message: Message, state: FSMContext):
    """Process deposit open date"""
    try:
        open_date = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
        await state.update_data(open_date=open_date)
        await message.answer(
            "📅 Введите дату <b>закрытия</b> вклада (ДД.ММ.ГГГГ):",
            parse_mode="HTML"
        )
        await state.set_state(AddPaymentFSM.date)
    except ValueError:
        await message.answer("❌ Неверный формат. Используйте: <b>ДД.ММ.ГГГГ</b>", parse_mode="HTML")


@router.message(AddPaymentFSM.date)
async def process_date(message: Message, state: FSMContext):
    """Process date input"""
    try:
        pdate = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
        await state.update_data(date=pdate)
    except ValueError:
        await message.answer("❌ Неверный формат. Используйте: <b>ДД.ММ.ГГГГ</b>", parse_mode="HTML")
        return
    
    await message.answer(
        "📝 Введите описание (например: 'Кредит', 'Аренда', 'Подписка')\n"
        "Или отправьте '-' если не нужно:"
    )
    await state.set_state(AddPaymentFSM.description)


@router.message(AddPaymentFSM.description)
async def process_description(message: Message, state: FSMContext):
    """Process description and show confirmation"""
    description = None if message.text.strip() == "-" else message.text.strip()
    await state.update_data(description=description)
    
    data = await state.get_data()
    
    # Build confirmation text
    type_text = "💳 Платёж" if data['type'] == 'payment' else "🏦 Вклад"
    text = f"<b>🔍 Проверьте данные:</b>\n\n"
    text += f"{type_text}\n"
    text += f"🏦 Банк: <b>{data['bank']}</b>\n"
    text += f"💵 Сумма: <b>{data['amount']:,} ₽</b>\n"
    text += f"📅 Дата: <b>{data['date'].strftime('%d.%m.%Y')}</b>\n"
    
    if data.get('open_date'):
        text += f"📂 Открыт: <b>{data['open_date'].strftime('%d.%m.%Y')}</b>\n"
    
    if data.get('description'):
        text += f"📝 {data['description']}\n"
    
    text += "\n<i>🔔 Напоминания: за 3 дня, 1 день, в день</i>"
    
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Сохранить", callback_data="payment_confirm:yes")
    kb.button(text="❌ Отменить", callback_data="payment_confirm:no")
    kb.adjust(2)
    
    await message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    await state.set_state(AddPaymentFSM.confirm)


@router.callback_query(AddPaymentFSM.confirm, F.data == "payment_confirm:yes")
async def save_payment(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    """Save payment to database"""
    data = await state.get_data()
    
    try:
        payment = Payment(
            user_id=callback.from_user.id,
            type=data['type'],
            bank=data['bank'],
            amount=data['amount'],
            date=data['date'],
            open_date=data.get('open_date'),
            description=data.get('description')
        )
        
        db.add(payment)
        await db.commit()
        
        type_text = "💳 Платёж" if data['type'] == 'payment' else "🏦 Вклад"
        await callback.message.edit_text(
            f"✅ <b>Сохранено!</b>\n\n"
            f"{type_text} добавлен.\n"
            f"Я напомню за 3 дня, за 1 день и в день события.",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error saving payment: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при сохранении. Попробуйте позже."
        )
    
    await state.clear()


@router.callback_query(AddPaymentFSM.confirm, F.data == "payment_confirm:no")
async def cancel_payment(callback: CallbackQuery, state: FSMContext):
    """Cancel payment creation"""
    await callback.message.edit_text("❌ Добавление отменено.")
    await state.clear()


# ============================================================================
# Payment action handlers
# ============================================================================

@router.callback_query(F.data.startswith("payment_done:"))
async def mark_payment_done(callback: CallbackQuery, db: AsyncSession):
    """Mark payment as completed"""
    payment_id = int(callback.data.split(":")[1])
    
    result = await db.execute(
        select(Payment).where(
            Payment.id == payment_id,
            Payment.user_id == callback.from_user.id
        )
    )
    payment = result.scalar_one_or_none()
    
    if payment:
        payment.is_completed = True
        payment.completed_at = datetime.utcnow()
        await db.commit()
        
        await callback.answer("✅ Отмечено выполненным!")
        
        # Update message
        new_text = callback.message.text + "\n\n✅ <b>Выполнено</b>"
        await callback.message.edit_text(new_text, parse_mode="HTML")
    else:
        await callback.answer("❌ Платёж не найден")


@router.callback_query(F.data.startswith("payment_skip:"))
async def skip_payment(callback: CallbackQuery, db: AsyncSession):
    """Skip payment reminder"""
    payment_id = int(callback.data.split(":")[1])
    
    result = await db.execute(
        select(Payment).where(
            Payment.id == payment_id,
            Payment.user_id == callback.from_user.id
        )
    )
    payment = result.scalar_one_or_none()
    
    if payment:
        await callback.answer("⏭ Пропущено")
        new_text = callback.message.text + "\n\n⏭ <b>Пропущено</b>"
        await callback.message.edit_text(new_text, parse_mode="HTML")
    else:
        await callback.answer("❌ Платёж не найден")


@router.callback_query(F.data == "finance:add")
async def finance_add(callback: CallbackQuery, state: FSMContext):
    """Add new finance from callback"""
    await cmd_add_payment(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == "finance:archive")
async def finance_archive(callback: CallbackQuery, db: AsyncSession):
    """Show payment archive"""
    user_id = callback.from_user.id
    
    result = await db.execute(
        select(Payment).where(
            Payment.user_id == user_id,
            Payment.is_completed == True
        ).order_by(desc(Payment.completed_at)).limit(10)
    )
    payments = result.scalars().all()
    
    if not payments:
        await callback.answer("Архив пуст")
        return
    
    text = "<b>🗑 Архив платежей</b>\n\n"
    for p in payments:
        icon = "💳" if p.type == 'payment' else '🏦'
        text += f"{icon} {p.bank} - {p.amount:,} ₽ ({p.date.strftime('%d.%m.%Y')})\n"
    
    kb = InlineKeyboardBuilder()
    kb.button(text="« Назад", callback_data="finance:back")
    
    await callback.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "finance:back")
async def finance_back(callback: CallbackQuery, db: AsyncSession):
    """Back to finance list"""
    await show_finances_list(callback, db, callback.from_user.id)
    await callback.answer()
