import os
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from services.database import DatabaseService

router = Router()

class FeedState(StatesGroup):
    waiting_content = State()
    confirm_post = State()

@router.callback_query(F.data == "menu_feed")
async def start_feed(callback: types.CallbackQuery, db: DatabaseService):
    user = await db.get_user(callback.from_user.id)
    
    # Hitung sisa kuota
    sisa_teks = 3 - user.text_posts_today
    sisa_foto = 1 - user.photo_posts_today
    
    text = (
        "📱 **Update Feed Channel**\n\n"
        "Bagikan aktivitas atau sapaanmu ke channel komunitas!\n"
        f"📝 Sisa kuota teks: {max(0, sisa_teks)}/3\n"
        f"📸 Sisa kuota foto: {max(0, sisa_foto)}/1\n\n"
        "Silakan kirim teks saja atau foto + caption sekarang:"
    )
    
    kb = [[types.InlineKeyboardButton(text="🔙 Batal", callback_data="main_menu")]]
    await callback.message.edit_text(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@router.message(F.text | F.photo)
async def process_feed_input(message: types.Message, state: FSMContext, db: DatabaseService):
    user = await db.get_user(message.from_user.id)
    
    # Cek kuota berdasarkan tipe input
    if message.photo:
        if not user.is_premium and user.photo_posts_today >= 1:
            return await message.answer("⚠️ Kuota foto harianmu sudah habis!")
        file_id = message.photo[-1].file_id
        caption = message.caption or ""
        post_type = "photo"
    else:
        if not user.is_premium and user.text_posts_today >= 3:
            return await message.answer("⚠️ Kuota teks harianmu sudah habis!")
        file_id = None
        caption = message.text
        post_type = "text"

    await state.update_data(f_file_id=file_id, f_caption=caption, f_type=post_type)
    
    kb = [
        [types.InlineKeyboardButton(text="👤 Tampilkan Profil", callback_data="p_visible")],
        [types.InlineKeyboardButton(text="🎭 Sembunyikan Profil (Anonim)", callback_data="p_hidden")],
        [types.InlineKeyboardButton(text="❌ Batalkan", callback_data="main_menu")]
    ]
    await message.answer("Bagaimana profilmu ingin ditampilkan di channel?", 
                         reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))
    await state.set_state(FeedState.confirm_post)

@router.callback_query(F.data.startswith("p_"), FeedState.confirm_post)
async def finalize_feed_post(callback: types.CallbackQuery, state: FSMContext, db: DatabaseService):
    data = await state.get_data()
    user = await db.get_user(callback.from_user.id)
    is_anon = callback.data == "p_hidden"
    channel_id = os.getenv("FEED_CHANNEL_ID")
    bot_user = os.getenv("BOT_USERNAME")

    # Susun Hashtag & Header
    header = "👤 **Anonim**" if is_anon else f"👤 **{user.full_name}**"
    location_tag = user.city_hashtag or "#Unknown"
    gender_tag = f"#{user.gender}"
    
    full_caption = (
        f"{header}\n"
        f"📍 {user.location_name}\n\n"
        f"{data['f_caption']}\n\n"
        f"{location_tag} {gender_tag} #PickMeFeed"
    )

    # Tombol Linkback ke Profil (Hanya jika tidak anonim)
    kb_list = []
    if not is_anon:
        kb_list.append([types.InlineKeyboardButton(text="💌 Kirim Pesan / Lihat Profil", 
                                                   url=f"https://t.me/{bot_user}?start=view_{user.id}")])
    
    markup = types.InlineKeyboardMarkup(inline_keyboard=kb_list)

    # Kirim ke Channel
    try:
        if data['f_type'] == "photo":
            await callback.bot.send_photo(channel_id, photo=data['f_file_id'], 
                                          caption=full_caption, reply_markup=markup)
            await db.increment_quota(user.id, "photo_post")
        else:
            await callback.bot.send_message(channel_id, full_caption, reply_markup=markup)
            await db.increment_quota(user.id, "text_post")
        
        await callback.message.edit_text("✅ Berhasil diposting ke channel!")
    except Exception as e:
        await callback.message.edit_text(f"❌ Gagal memposting: {str(e)}")
    
    await state.clear()
    from handlers.start import show_main_menu
    await show_main_menu(callback.message)
                
