import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv

# Memastikan Python bisa menemukan folder handlers, services, dan utils
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# 1. IMPORT SEMUA HANDLER DAN SERVICE (Sesuai Struktur File Kamu)
from services.database import DatabaseService
from handlers import start, register, feed, dating, admin

# Load Environment Variables dari Railway / .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

async def main():
    # 2. KONFIGURASI LOGGING (Agar kamu bisa pantau error di Railway)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    logger = logging.getLogger(__name__)

    # 3. INISIALISASI BOT
    # Menggunakan DefaultBotProperties agar semua pesan otomatis support HTML
    bot = Bot(
        token=BOT_TOKEN, 
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # 4. INISIALISASI DATABASE POSTGRES
    db = DatabaseService(DATABASE_URL)
    try:
        await db.init_db()
        logger.info("✅ Database Postgres berhasil terhubung dan tabel telah siap.")
    except Exception as e:
        logger.error(f"❌ Gagal inisialisasi database: {e}")
        return

    # 5. SETUP DISPATCHER & STORAGE (MemoryStorage untuk FSM/Pendaftaran)
    dp = Dispatcher(storage=MemoryStorage())

    # 6. DEPENDENCY INJECTION
    # Memasukkan objek 'db' agar bisa digunakan langsung di semua file handler
    dp["db"] = db

    # 7. REGISTRASI SEMUA ROUTER (URUTAN SANGAT KRUSIAL)
    # Kita urutkan agar fitur prioritas seperti Admin dan Register tidak tertutup Menu Utama
    dp.include_router(admin.router)    # Handler untuk Ban/Stats (Admin Only)
    dp.include_router(register.router) # Handler untuk Alur Pendaftaran
    dp.include_router(start.router)    # Handler untuk /start dan Menu Utama
    dp.include_router(feed.router)     # Handler untuk Posting ke Channel
    dp.include_router(dating.router)   # Handler untuk Swipe dan Pesan Instan

    # 8. GLOBAL UNKNOWN HANDLER (Jaring Pengaman)
    # Ini menangkap pesan teks yang bukan command dan user tidak sedang mengisi data
    @dp.message(F.text, ~F.text.startswith("/"))
    async def global_unknown_handler(message: types.Message, state: FSMContext):
        # Cek apakah user sedang dalam proses FSM (sedang daftar/isi feed)
        current_state = await state.get_state()
        if current_state is not None:
            # Jika user sedang dalam proses input, biarkan router yang bersangkutan bekerja
            return
        
        # Jika benar-benar pesan random di luar menu, beri tahu user
        await message.answer(
            "❓ **Maaf, saya tidak mengerti.**\n\n"
            "Silakan gunakan tombol menu yang tersedia atau ketik /start untuk kembali ke menu utama."
        )

    # 9. START POLLING
    logger.info("🚀 PickMe Bot v3.0 (Full MVP) is Online!")
    
    # Hapus webhook lama dan abaikan pesan tertunda saat bot sedang mati (mencegah spam)
    await bot.delete_webhook(drop_pending_updates=True)
    
    try:
        # Jalankan bot
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Terjadi kesalahan saat bot berjalan: {e}")
    finally:
        # Tutup sesi bot dengan aman saat dimatikan
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("ℹ️ Bot dimatikan secara manual.")
        
