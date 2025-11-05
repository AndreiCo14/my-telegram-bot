import asyncio
import os
import logging
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.client.default import DefaultBotProperties
from aiohttp import web

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Переменные окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = os.getenv("BASE_URL", "https://your-bot.onrender.com").rstrip("/")
PORT = int(os.getenv("PORT", 10000))  # Render использует 10000 по умолчанию

# Инициализация бота (aiogram ≥ 3.7.0)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()

# Глобальные переменные
USER_CHAT_ID = None
COUNTER = 0

@router.message()
async def handle_start(message: Message):
    global USER_CHAT_ID
    USER_CHAT_ID = message.chat.id
    await message.answer("✅ Бот активирован! Первое число придет через 10 минут.")
    logger.info(f"Chat ID сохранён: {USER_CHAT_ID}")

# Эндпоинт для внешнего триггера (например, от UptimeRobot)
async def tick_handler(request):
    global COUNTER
    if USER_CHAT_ID is not None:
        COUNTER += 1
        try:
            await bot.send_message(USER_CHAT_ID, str(COUNTER))
            logger.info(f"Отправлено число: {COUNTER}")
        except Exception as e:
            logger.error(f"Ошибка отправки: {e}")
    return web.json_response({"status": "ok", "counter": COUNTER})

# Установка вебхука при старте
async def on_startup(app):
    webhook_url = f"{BASE_URL}/webhook"
    await bot.set_webhook(webhook_url)
    logger.info(f"Вебхук установлен на: {webhook_url}")

# Очистка при остановке
async def on_shutdown(app):
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.session.close()

def main():
    app = web.Application()

    # Регистрация вебхука для Telegram
    webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_handler.register(app, path="/webhook")

    # Добавляем эндпоинт /tick для внешнего запуска отправки
    app.router.add_get("/tick", tick_handler)

    # Подключаем события
    setup_application(app, dp, bot=bot)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    # Запуск сервера
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    dp.include_router(router)
    main()
