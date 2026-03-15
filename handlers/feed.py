import os
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from services.database import DatabaseService
from utils.filters import is_clean_text

router = Router()

class FeedState(StatesGroup):
    input_content = State()
    anon_toggle = State()

@router.callback_query(F.data == "menu_feed")
async def start_feed(callback: types.CallbackQuery, db: DatabaseService, state: FSMContext):
    user = await db.get_user(callback.from_user.id)
    
    # CEK KUOTA HARIAN (3 Teks, 1 Foto untuk Non-Premium)
    if not user.is_premium:
        if user.text_posts_today >= 3:
            return await callback.message.answer("⚠️ Kuota posting TEKS kamu hari ini sudah habis (Maks 3).\n\n✨ Upgrade Premium untuk unlimited post!")
        if user.photo_posts_today >= 1:
            return await callback.message.answer("⚠️ Kuota posting FOTO kamu hari ini sudah habis (Maks 1).\n\n✨ Upgrade Premium untuk unlimited post!")

    kb = [
        [types.InlineKeyboardButton(text="📝 Kirim Postingan (Teks/Foto)", callback_data="feed_input")]
    ]
    await callback.message.edit_text(
        "Silakan kirim teks atau foto yang ingin kamu posting ke channel.\n\n"
        "Sisa kuota kamu:\n"
        f"📝 Teks: {3 - user.text_posts_today}/3\n"
        f"📸 Foto: {1 - user.photo_posts_today}/1",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb)
    )
    await state.set_state(FeedState.input_content)

@router.message(FeedState.input_content)
async def process_content(message: types.Message, state: FSMContext):
    content = message.text or message.caption
    
    # Validasi Teks (Sensor)
    if content and not is_clean_text(content):
        return await message.answer("❌ Maaf, postinganmu mengandung kata-kata yang dilarang. Silakan ketik ulang dengan bahasa yang sopan.")

    photo_id = message.photo[-1].file_id if message.photo else None
    await state.update_data(content=content, photo_id=photo_id)
    
    # Opsi Privasi
    kb = [
        [types.InlineKeyboardButton(text="🔓 Tampilkan Profil", callback_data="p_public"),
         types.InlineKeyboardButton(text="🔒 Anonim (Sembunyikan)", callback_data="p_anon")]
    ]
    await message.answer("Apakah kamu ingin orang lain bisa melihat profilmu melalui postingan ini?", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))
    await state.set_state(FeedState.anon_toggle)

@router.callback_query(FeedState.anon_toggle, F.data.startswith("p_"))
async def finalize_post(callback: types.CallbackQuery, state: FSMContext, db: DatabaseService):
    data = await state.get_data()
    user = await db.get_user(callback.from_user.id)
    is_anon = callback.data == "p_anon"
    
    # Format Tampilan
    icon = "👨" if user.gender == "Pria" else "👩"
    header = f"{icon} **{user.full_name}** | 📍 {user.location_name}"
    body = f"\n\n📝 {data['content']}" if data['content'] else ""
    tags = f"\n\n{user.city_hashtag} #{user.gender} #PickMeFeed"
    
    full_post = f"{header}{body}{tags}"
    
    # Tombol Lihat Profil (Hanya jika tidak anonim)
    kb_list = []
    if not is_anon:
        bot_user = os.getenv("BOT_USERNAME")
        kb_list.append([types.InlineKeyboardButton(text="👤 Lihat Profil", url=f"https://t.me/{bot_user}?start=view_{user.id}")])
    
    markup = types.InlineKeyboardMarkup(inline_keyboard=kb_list)
    channel_id = os.getenv("FEED_CHANNEL_ID")

    # Eksekusi Posting
    if data['photo_id']:
        await callback.bot.send_photo(channel_id, data['photo_id'], caption=full_post, reply_markup=markup)
        await db.increment_quota(user.id, "photo")
    else:
        await callback.bot.send_message(channel_id, full_post, reply_markup=markup)
        await db.increment_quota(user.id, "text")

    await callback.message.answer("🚀 Berhasil! Postingan kamu sudah terbit di channel.")
    await state.clear()
    
