import asyncio
import os
import logging
from aiogram import Bot, Dispatcher, Router, types
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.client.default import DefaultBotProperties  # ← НОВОЕ
from aiohttp import web

# Настройка логгера
logging.basicConfig(level=logging.INFO)

# Переменные окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "my-secret")
BASE_URL = os.getenv("BASE_URL", "https://your-bot.onrender.com").rstrip("/")
PORT = int(os.getenv("PORT", 8000))

# ✅ Используем DefaultBotProperties
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)  # ← ПРАВИЛЬНО
)

dp = Dispatcher()
router = Router()

# Глобальные переменные
USER_CHAT_ID = None
COUNTER = 0

@router.message()
async def handle_start(message: types.Message):
    global USER_CHAT_ID
    USER_CHAT_ID = message.chat.id
    await message.answer("✅ Бот запущен! Теперь я буду присылать числа каждые 10 минут.")
    logging.info(f"Chat ID сохранён: {USER_CHAT_ID}")

# Фоновая задача
async def send_numbers_periodically():
    global COUNTER
    while True:
        await asyncio.sleep(600)  # 10 минут
        if USER_CHAT_ID is not None:
            COUNTER += 1
            try:
                await bot.send_message(USER_CHAT_ID, str(COUNTER))
                logging.info(f"Отправлено: {COUNTER}")
            except Exception as e:
                logging.error(f"Ошибка при отправке: {e}")

# События запуска/остановки
async def on_startup(app):
    await bot.set_webhook(
        f"{BASE_URL}{WEBHOOK_PATH}",
        secret_token=WEBHOOK_SECRET
    )
    asyncio.create_task(send_numbers_periodically())

async def on_shutdown(app):
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.session.close()

def main():
    app = web.Application()
    webhook_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET,
    )
    webhook_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    app.on_startup.append(lambda _app: on_startup(_app))
    app.on_shutdown.append(lambda _app: on_shutdown(_app))

    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    dp.include_router(router)
    main()
