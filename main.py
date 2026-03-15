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

# Import Layanan & Handlers (Menambahkan admin ke daftar import)
from services.database import DatabaseService
from handlers import start, register, feed, dating, admin

# Load Environment Variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

async def main():
    # 1. Konfigurasi Logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    logger = logging.getLogger(__name__)

    # 2. Inisialisasi Bot dengan ParseMode HTML
    bot = Bot(
        token=BOT_TOKEN, 
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # 3. Inisialisasi Database Postgres
    db = DatabaseService(DATABASE_URL)
    
    try:
        await db.init_db()
        logger.info("Database Postgres berhasil terhubung dan diinisialisasi.")
    except Exception as e:
        logger.error(f"Gagal inisialisasi database: {e}")
        return

    # 4. Setup Dispatcher & Storage
    dp = Dispatcher(storage=MemoryStorage())

    # 5. Dependency Injection
    dp["db"] = db

    # 6. Registrasi Routers (URUTAN FINAL & AMAN)
    # Admin ditaruh paling atas agar perintah ban tidak 'tercuri' oleh router lain
    dp.include_router(admin.router) 
    dp.include_router(register.router)
    dp.include_router(start.router)
    dp.include_router(feed.router)
    dp.include_router(dating.router)

    # --- PERBAIKAN DI SINI ---
    # Tambahkan filter agar Global Handler TIDAK menangkap perintah berawalan '/'
    @dp.message()
    async def global_unknown_handler(message: types.Message):
        # Jika pesan adalah command (seperti /start) atau dalam proses FSM, biarkan lewat
        if message.text and message.text.startswith("/"):
            return
        
        await message.answer(
            "❓ **Sorry guys, ini BOT bukan tempat curhat.**\n\n"
            "Silakan gunakan tombol menu yang tersedia atau klik /start untuk kembali ke menu utama."
        )

    # 7. Start Polling
    logger.info("PickMe Bot sedang online (v4.2 - MVP Final)!")
    
    # Drop_pending_updates=True mencegah spam pesan lama saat bot baru nyala
    await bot.delete_webhook(drop_pending_updates=True)
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Bot berhenti karena error: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot dimatikan secara manual.")
    
