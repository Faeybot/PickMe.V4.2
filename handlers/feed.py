import os
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from services.database import DatabaseService

router = Router()

class FeedState(StatesGroup):
    waiting_content = State()
    confirm_post = State()

@router.callback_query(F.data == "menu_feed")
async def start_feed(callback: types.CallbackQuery, db: DatabaseService, state: FSMContext):
    user = await db.get_user(callback.from_user.id)
    sisa_teks = 3 - user.text_posts_today
    sisa_foto = 1 - user.photo_posts_today
    
    text = (
        "📱 **UPDATE FEED CHANNEL**\n\n"
        "Bagikan aktivitas atau sapaanmu ke channel komunitas!\n"
        f"📝 Sisa kuota teks: **{max(0, sisa_teks)}/3**\n"
        f"📸 Sisa kuota foto: **{max(0, sisa_foto)}/1**\n\n"
        "Silakan kirim **Teks** saja atau **Foto + Caption** sekarang:"
    )
    
    kb = [[InlineKeyboardButton(text="🔙 Batal", callback_data="main_menu")]]
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await state.set_state(FeedState.waiting_content)
    await callback.answer()

@router.message(FeedState.waiting_content, F.text | F.photo)
async def process_feed_input(message: types.Message, state: FSMContext, db: DatabaseService):
    user = await db.get_user(message.from_user.id)
    
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
        [InlineKeyboardButton(text="👤 Tampilkan Profil", callback_data="p_visible")],
        [InlineKeyboardButton(text="🎭 Sembunyikan Profil (Anonim)", callback_data="p_hidden")],
        [InlineKeyboardButton(text="❌ Batalkan", callback_data="main_menu")]
    ]
    await message.answer("Bagaimana profilmu ingin ditampilkan di channel?", 
                         reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await state.set_state(FeedState.confirm_post)

@router.callback_query(F.data.startswith("p_"), FeedState.confirm_post)
async def finalize_feed_post(callback: types.CallbackQuery, state: FSMContext, db: DatabaseService):
    data = await state.get_data()
    user = await db.get_user(callback.from_user.id)
    is_anon = callback.data == "p_hidden"
    channel_id = os.getenv("FEED_CHANNEL_ID")
    bot_user = os.getenv("BOT_USERNAME")

    # FORMAT BARU 5 LINE
    symbol = "👨" if user.gender == "pria" else "👩"
    line1 = "👤 **Anonim**" if is_anon else f"{symbol} **{user.full_name}**"
    line2 = ""
    line3 = data['f_caption']
    line4 = ""
    line5 = f"#{user.gender} #{user.city_hashtag.replace('#','')} #PickMeFeed"
    
    full_caption = f"{line1}\n{line2}\n{line3}\n{line4}\n{line5}"

    # Tombol Tunggal agar Komentar Telegram muncul
    kb_list = []
    if not is_anon:
        kb_list.append([
            InlineKeyboardButton(text="👤 Lihat Profil Lengkap", 
                                 url=f"https://t.me/{bot_user}?start=view_{user.id}")
        ])
    
    markup = InlineKeyboardMarkup(inline_keyboard=kb_list)

    try:
        if data['f_type'] == "photo":
            await callback.bot.send_photo(channel_id, photo=data['f_file_id'], 
                                          caption=full_caption, reply_markup=markup)
            await db.increment_quota(user.id, "photo_post")
        else:
            await callback.bot.send_message(channel_id, full_caption, reply_markup=markup)
            await db.increment_quota(user.id, "text_post")
        
        await callback.message.edit_text("✅ **Berhasil!** Cek channel untuk melihat interaksimu.")
    except Exception as e:
        await callback.message.edit_text(f"❌ Gagal memposting: {str(e)}")
    
    await state.clear()
    from handlers.start import show_main_menu
    await show_main_menu(callback.message)
    
