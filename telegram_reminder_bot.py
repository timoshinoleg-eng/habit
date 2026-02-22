#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
import datetime
import json
import os
import spacy
import re
import subprocess
from ocr_receipt_processor import OCRSpaceClient

# Initialize OCRSpaceClient (API key will be loaded from environment variable)
OCR_SPACE_API_KEY = os.getenv("OCR_SPACE_API_KEY", "K87667637889876") # Default key for testing, replace with actual in production
ocr_client = OCRSpaceClient(OCR_SPACE_API_KEY)


# Load SpaCy Russian language model
try:
    nlp = spacy.load("ru_core_news_sm")
except OSError:
    print("Downloading SpaCy model 'ru_core_news_sm'...")
    spacy.cli.download("ru_core_news_sm")
    nlp = spacy.load("ru_core_news_sm")

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# File to store user schedules
SCHEDULE_FILE = 'schedules.json'

def load_schedules():
    if os.path.exists(SCHEDULE_FILE):
        with open(SCHEDULE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_schedules(schedules):
    with open(SCHEDULE_FILE, 'w') as f:
        json.dump(schedules, f, indent=4)

user_schedules = load_schedules()

scheduler = BackgroundScheduler()
scheduler.start()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        f"Привет, {user.mention_html()}! Я бот-напоминалка для приема лекарств и витаминов. "
        "Просто напиши мне, что и когда принимать, например: \'Напоминай мне принимать аспирин в 8 утра\'."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message when the command /help is issued."""
    await update.message.reply_text(
        "Я могу помочь тебе не забывать принимать лекарства и витамины. "
        "Просто напиши мне в свободной форме, что и когда тебе нужно принять. "
        "Например: 'Принимать фестал каждый день утром после еды в 9 утра'\n\n"

        "Также доступны команды:\n" 
        "/list - Показать все твои текущие напоминания\n" 
        "/delete <ID напоминания> - Удалить напоминание по его ID (можно узнать через /list)\n" 
        "/stop - Остановить бота (удалит все твои напоминания)"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle natural language messages to set reminders."""
    text = update.message.text
    chat_id = str(update.effective_chat.id)

    time_str, medication = parse_natural_language_reminder(text)

    if time_str and medication:
        if chat_id not in user_schedules:
            user_schedules[chat_id] = []

        reminder_id = len(user_schedules[chat_id]) + 1

        user_schedules[chat_id].append({
            'id': reminder_id,
            'time': time_str,
            'medication': medication
        })
        save_schedules(user_schedules)

        await update.message.reply_text(
            f"Напоминание для '{medication}' установлено на {time_str} ежедневно. ID напоминания: {reminder_id}"
        )
        
        schedule_daily_reminder(context.bot, chat_id, reminder_id, time_str, medication)
    else:
        await update.message.reply_text(
            "Не удалось распознать время или название лекарства в вашем сообщении. Попробуйте еще раз, например: 'Напоминай мне принимать аспирин в 8 утра'."
        )



def parse_natural_language_reminder(text: str) -> (str | None, str | None):
    """Parse natural language text to extract time and medication."""
    # Simple regex for time, e.g., 9:00, 9 утра, в 9
    time_match = re.search(r'(\d{1,2}:\d{2})|(\d{1,2})', text)
    if time_match:
        time_str = time_match.group(0)
        if ':' not in time_str:
            time_str = f"{time_str}:00"
    else:
        return None, None

    # Use SpaCy for more robust entity recognition in a real scenario
    # For this example, we'll use a simpler approach: assume the rest of the message is the medication
    doc = nlp(text)
    medication = text
    # A simple way to extract medication is to remove the time part
    medication = medication.replace(time_match.group(0), '').strip()
    # Further clean up common reminder phrases
    medication = re.sub(r'^(напоминай|принимать|напомни|напоминание|напомнить)\s*(мне)?\s*', '', medication, flags=re.IGNORECASE).strip()
    medication = re.sub(r'^(каждый день|ежедневно|утром|вечером|днем|в|после еды)\s*', '', medication, flags=re.IGNORECASE).strip()
    medication = re.sub(r'\s*(в|утром|вечером|днем)$', '', medication, flags=re.IGNORECASE).strip()

    if not medication:
        return time_str, "лекарство"

    return time_str, medication

def schedule_daily_reminder(bot_instance, chat_id, reminder_id, time_str, medication):
    hour, minute = map(int, time_str.split(':'))
    job_id = f"reminder_{chat_id}_{reminder_id}"

    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    scheduler.add_job(
        send_reminder_message,
        'cron',
        hour=hour,
        minute=minute,
        args=[bot_instance, chat_id, medication],
        id=job_id
    )
    logger.info(f"Scheduled job {job_id} for {time_str} with medication '{medication}'")

async def send_reminder_message(bot_instance, chat_id: str, medication: str) -> None:
    """Sends the reminder message to the user."""
    await bot_instance.send_message(chat_id=chat_id, text=f"Пора принять {medication}!")
    logger.info(f"Reminder sent to {chat_id}: Пора принять {medication}!")

async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lists all active reminders for the user."""
    chat_id = str(update.effective_chat.id)

    if chat_id not in user_schedules or not user_schedules[chat_id]:
        await update.message.reply_text("У тебя пока нет активных напоминаний.")
        return

    message = "Твои текущие напоминания:\n"
    for reminder in user_schedules[chat_id]:
        message += f"ID: {reminder['id']}, Время: {reminder['time']}, Лекарство: {reminder['medication']}\n"
    await update.message.reply_text(message)

async def delete_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Deletes a reminder by its ID."""
    chat_id = str(update.effective_chat.id)
    args = context.args

    if len(args) != 1:
        await update.message.reply_text(
            "Неверный формат. Используй: /delete <ID напоминания>. Например: /delete 1"
        )
        return

    try:
        reminder_id_to_delete = int(args[0])
    except ValueError:
        await update.message.reply_text("ID напоминания должен быть числом.")
        return

    if chat_id not in user_schedules or not user_schedules[chat_id]:
        await update.message.reply_text("У тебя нет напоминаний для удаления.")
        return

    initial_len = len(user_schedules[chat_id])
    user_schedules[chat_id] = [
        r for r in user_schedules[chat_id] if r['id'] != reminder_id_to_delete
    ]

    if len(user_schedules[chat_id]) < initial_len:
        job_id = f"reminder_{chat_id}_{reminder_id_to_delete}"
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
            logger.info(f"Removed job {job_id} from scheduler.")

        save_schedules(user_schedules)
        await update.message.reply_text(f"Напоминание с ID {reminder_id_to_delete} удалено.")
    else:
        await update.message.reply_text(f"Напоминание с ID {reminder_id_to_delete} не найдено.")

async def handle_receipt_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles incoming photos, processes them as receipts using OCR, and saves the expense."""
    chat_id = str(update.effective_chat.id)
    await update.message.reply_text("Получил фото. Обрабатываю чек...")

    # Get the largest photo
    photo_file = await update.message.photo[-1].get_file()
    photo_path = f"receipt_{chat_id}_{photo_file.file_id}.jpg"
    await photo_file.download_to_drive(photo_path)

    try:
        ocr_result = ocr_client.parse_receipt(photo_path)
        if "error" in ocr_result:
            await update.message.reply_text(f"Ошибка при распознавании чека: {ocr_result["error"]}")
            logger.error(f"OCR error for chat_id {chat_id}: {ocr_result["error"]}")
            return

        extracted_data = ocr_client.extract_info_from_ocr_result(ocr_result)
        raw_text = extracted_data["raw_text"]
        total_amount = extracted_data["total_amount"]
        category = extracted_data["category"] # This will be 'Неизвестно' for now

        # TODO: Integrate NLP for better categorization here
        # For now, we'll just use the default 'Неизвестно' or try to infer from raw_text
        if total_amount is None:
            await update.message.reply_text(
                f"Не удалось извлечь сумму из чека. Распознанный текст:\n```\n{raw_text[:500]}...\n```\nПожалуйста, введите сумму вручную или попробуйте другое фото."
            )
            # Optionally, ask user to manually input amount and category
            return

        # TODO: Save to Yandex Forms instead of local storage
        # For now, we'll just confirm the extraction
        await update.message.reply_text(
            f"Чек распознан!\nСумма: {total_amount} руб.\nКатегория: {category}\n\n" # Placeholder for Yandex Forms integration
            f"(Данные будут сохранены в Яндекс.Формы после интеграции.)"
        )
        logger.info(f"Receipt processed for chat_id {chat_id}: Amount={total_amount}, Category={category}")

    except Exception as e:
        await update.message.reply_text(f"Произошла непредвиденная ошибка при обработке чека: {e}")
        logger.error(f"Unexpected error processing receipt for chat_id {chat_id}: {e}", exc_info=True)
    finally:
        # Clean up the downloaded photo file
        if os.path.exists(photo_path):
            os.remove(photo_path)

async def stop_bot_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Stops the bot and removes all user's reminders."""
    chat_id = str(update.effective_chat.id)

    if chat_id in user_schedules:
        for reminder in user_schedules[chat_id]:
            job_id = f"reminder_{chat_id}_{reminder['id']}"
            if scheduler.get_job(job_id):
                scheduler.remove_job(job_id)
                logger.info(f"Removed job {job_id} from scheduler.")
        del user_schedules[chat_id]
        save_schedules(user_schedules)

    await update.message.reply_text("Бот остановлен, все твои напоминания удалены. До свидания!")

async def post_init(application: Application) -> None:
    """Post initialization hook to re-schedule jobs after bot restart."""
    global user_schedules
    user_schedules = load_schedules()
    for chat_id, reminders in user_schedules.items():
        for reminder in reminders:
            schedule_daily_reminder(application.bot, chat_id, reminder["id"], reminder["time"], reminder["medication"])
    logger.info("All existing reminders re-scheduled.")

def main() -> None:
    """Start the bot."""
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set.")
        print("Ошибка: Токен Telegram бота не установлен. Пожалуйста, установите переменную окружения TELEGRAM_BOT_TOKEN.")
        return

    application = Application.builder().token(TOKEN).post_init(post_init).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("list", list_reminders))
    application.add_handler(CommandHandler("delete", delete_reminder))
    application.add_handler(CommandHandler("stop", stop_bot_command))

        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_receipt_photo))

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

