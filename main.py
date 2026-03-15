import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv

# Memastikan folder root terbaca oleh Python
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Import Layanan & Handlers
from services.database import DatabaseService
from handlers import admin, register, start, feed, dating

# Load Environment Variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

async def main():
    # 1. Konfigurasi Logging (Cek log ini di Railway jika bot stuck)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    logger = logging.getLogger(__name__)

    # 2. Inisialisasi Bot
    bot = Bot(
        token=BOT_TOKEN, 
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # 3. Inisialisasi Database
    db = DatabaseService(DATABASE_URL)
    try:
        await db.init_db()
        logger.info("✅ Database terhubung.")
    except Exception as e:
        logger.error(f"❌ Database Error: {e}")
        return

    # 4. Setup Dispatcher
    dp = Dispatcher(storage=MemoryStorage())

    # 5. Dependency Injection
    dp["db"] = db

    # 6. Registrasi Routers (URUTAN FINAL)
    # Kita lepaskan Global Handler dulu agar tidak menghalangi perintah /start
    dp.include_router(admin.router)
    dp.include_router(register.router)
    dp.include_router(start.router)
    dp.include_router(feed.router)
    dp.include_router(dating.router)

    # 7. Start Polling
    logger.info("🚀 PickMe Bot AKTIF. Silakan tekan /start")
    
    # Hapus pesan tertunda (drop_pending_updates) agar bot tidak stuck saat start
    await bot.delete_webhook(drop_pending_updates=True)
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Polling Error: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot dimatikan.")
