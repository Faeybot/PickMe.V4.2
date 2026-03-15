from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from services.database import DatabaseService
from utils.filters import is_clean_text
import os
from datetime import datetime

router = Router()

class FeedState(StatesGroup):
    choosing_type = State()
    input_content = State()
    anon_toggle = State()

@router.callback_query(F.data == "menu_feed")
async def start_feed(callback: types.CallbackQuery, state: FSMContext, db: DatabaseService):
    user = await db.get_user(callback.from_user.id)
    
    # CEK KUOTA (Hanya untuk non-premium)
    if not user.is_premium:
        if user.text_posts_today >= 3 and user.photo_posts_today >= 1:
            return await callback.message.answer("⚠️ Kuota harianmu habis! (3 Teks, 1 Foto).\n\n✨ Upgrade Premium untuk unlimited post!")

    kb = [
        [types.InlineKeyboardButton(text="📝 Post Teks", callback_data="feed_text")],
        [types.InlineKeyboardButton(text="📸 Post Foto", callback_data="feed_photo")]
    ]
    await callback.message.edit_text("Pilih jenis postingan:", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))
    await state.set_state(FeedState.input_content)

@router.message(FeedState.input_content)
async def process_feed_content(message: types.Message, state: FSMContext, db: DatabaseService):
    content = message.text or message.caption
    
    # 1. FILTER KATA KASAR
    if not is_clean_text(content):
        return await message.answer("❌ Pesanmu mengandung kata terlarang. Yuk, pakai bahasa yang sopan!")

    await state.update_data(content=content, photo_id=message.photo[-1].file_id if message.photo else None)
    
    # 2. TANYA PRIVASI
    kb = [
        [types.InlineKeyboardButton(text="🔓 Tampilkan Profil", callback_data="priv_public")],
        [types.InlineKeyboardButton(text="🔒 Anonim", callback_data="priv_anon")]
    ]
    await message.answer("Apakah ingin menampilkan profil kamu di postingan ini?", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))
    await state.set_state(FeedState.anon_toggle)

@router.callback_query(F.data.startswith("priv_"), FeedState.anon_toggle)
async def finalize_feed(callback: types.CallbackQuery, state: FSMContext, db: DatabaseService):
    user_data = await state.get_data()
    user = await db.get_user(callback.from_user.id)
    is_anon = callback.data == "priv_anon"
    
    # FORMAT POSTINGAN
    gender_icon = "👨" if user.gender == "Pria" else "👩"
    post_text = (
        f"{gender_icon} **{user.full_name}** | 📍 {user.location_name}\n\n"
        f"📝 {user_data['content']}\n\n"
        f"{user.city_hashtag} #{user.gender} #PickMeFeed"
    )
    
    # JALUR POSTING
    FEED_CHANNEL_ID = os.getenv("FEED_CHANNEL_ID")
    
    if user_data['photo_id']:
        # FOTO: Kirim ke Admin dulu (Moderasi)
        ADMIN_GROUP_ID = os.getenv("ADMIN_GROUP_ID")
        kb = [[types.InlineKeyboardButton(text="✅ Approve", callback_data=f"app_{user.id}"),
               types.InlineKeyboardButton(text="❌ Reject", callback_data=f"rej_{user.id}")]]
        await callback.bot.send_photo(ADMIN_GROUP_ID, user_data['photo_id'], caption=f"MODERASI FOTO\n\n{post_text}", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))
        await callback.message.answer("📸 Foto terkirim ke admin untuk diperiksa!")
    else:
        # TEKS: Langsung ke Channel
        kb = []
        if not is_anon:
            kb.append([types.InlineKeyboardButton(text="👤 Lihat Profil", url=f"https://t.me/{os.getenv('BOT_USERNAME')}?start=view_{user.id}")])
        
        await callback.bot.send_message(FEED_CHANNEL_ID, post_text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))
        await callback.message.answer("🚀 Postingan teks kamu sudah terbit di channel!")
        
        # UPDATE KUOTA
        await db.increment_quota(user.id, "text")

    await state.clear()
  
