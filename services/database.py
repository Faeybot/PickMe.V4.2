from aiogram import Router, F, types
from aiogram.filters import Command
from services.database import DatabaseService
import os

router = Router()

# Pastikan hanya ID kamu (Admin) yang bisa akses
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

@router.callback_query(F.data.startswith("ban_"))
async def admin_ban_user(callback: types.CallbackQuery, db: DatabaseService):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("❌ Akses ditolak.")
    
    target_id = int(callback.data.split("_")[1])
    async with db.async_session() as session:
        user = await session.get(User, target_id)
        if user:
            user.status = 'banned'
            await session.commit()
    
    await callback.message.edit_caption(caption=callback.message.caption + "\n\n🚫 **USER INI TELAH DI-BAN**")
    await callback.answer("User berhasil di-ban!")

@router.message(Command("stats"))
async def get_stats(message: types.Message, db: DatabaseService):
    if message.from_user.id != ADMIN_ID: return
    # Logika sederhana hitung total user
    async with db.async_session() as session:
        from sqlalchemy import func
        from services.database import User
        count = await session.scalar(select(func.count()).select_from(User))
        await message.answer(f"📊 **Statistik Bot**\nTotal User Terdaftar: {count}")
        
