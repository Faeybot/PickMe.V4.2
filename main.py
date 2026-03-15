import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

# Fix agar Python bisa membaca folder modul kita
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Import layanan kita
from services.database import DatabaseService
from handlers import start, register, feed, dating

# Load variabel dari Railway/Env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

async def main():
    # Setup Logging
    logging.basicConfig(level=logging.INFO)

    # Inisialisasi Bot dan Database
    bot = Bot(token=BOT_TOKEN)
    db = DatabaseService(DATABASE_URL)
    
    # Pastikan Tabel Database Terbuat
    await db.init_db()

    # Setup Dispatcher & Storage (Memory untuk FSM)
    dp = Dispatcher(storage=MemoryStorage())

    # Dependency Injection: Masukkan 'db' ke setiap handler secara otomatis
    dp["db"] = db

    # Registrasi Router (Menyambungkan file di folder handlers)
    dp.include_router(start.router)
    dp.include_router(register.router)
    dp.include_router(feed.router)
    dp.include_router(dating.router)

    # Mulai Bot (Polling)
    logging.info("PickMe Bot sedang berjalan...")
    await bot.delete_webhook(drop_pending_updates=True)
    await asyncio.gather(
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot dimatikan.")
