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
    
    # Hitung sisa kuota
    sisa_teks = 3 - user.text_posts_today
    sisa_foto = 1 - user.photo_posts_today
    
    text = (
        "📱 **UPDATE FEED CHANNEL**\n\n"
        "Bagikan aktivitas atau sapaanmu ke channel komunitas!\n"
        "Postingan kamu akan memiliki kolom komentar otomatis.\n\n"
        f"📝 Sisa kuota teks: **{max(0, sisa_teks)}/3**\n"
        f"📸 Sisa kuota foto: **{max(0, sisa_foto)}/1**\n\n"
        "Silakan kirim **Teks** saja atau **Foto + Caption** sekarang:"
    )
    
    kb = [[types.InlineKeyboardButton(text="🔙 Batal", callback_data="main_menu")]]
    await callback.message.edit_text(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))
    await state.set_state(FeedState.waiting_content) # WAJIB: Set state agar tidak bentrok
    await callback.answer()

@router.message(FeedState.waiting_content, F.text | F.photo)
async def process_feed_input(message: types.Message, state: FSMContext, db: DatabaseService):
    user = await db.get_user(message.from_user.id)
    
    # Validasi Kuota
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

    if not caption and not file_id:
        return await message.answer("Silakan masukkan teks atau foto dengan caption.")

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

    # Susun Header & Hashtag
    header = "👤 **Anonim**" if is_anon else f"👤 **{user.full_name}**, {user.age}"
    location_info = f"📍 {user.location_name}"
    
    full_caption = (
        f"📣 **FEED BARU**\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{header}\n"
        f"{location_info}\n\n"
        f"“ {data['f_caption']} ”\n\n"
        f"#{user.city_hashtag.replace('#','')} #{user.gender} #PickMeFeed"
    )

    # Tombol Interaksi (Dua tombol berdampingan sesuai permintaan)
    kb_list = []
    if not is_anon:
        kb_list.append([
            types.InlineKeyboardButton(text="👤 Lihat Profil", url=f"https://t.me/{bot_user}?start=view_{user.id}"),
            types.InlineKeyboardButton(text="💌 Chat / Kenalan", url=f"https://t.me/{bot_user}?start=chat_{user.id}")
        ])
    
    markup = types.InlineKeyboardMarkup(inline_keyboard=kb_list)

    # Kirim ke Channel (Pesan Baru agar Komentar Muncul)
    try:
        if data['f_type'] == "photo":
            await callback.bot.send_photo(channel_id, photo=data['f_file_id'], 
                                          caption=full_caption, reply_markup=markup)
            await db.increment_quota(user.id, "photo_post")
        else:
            await callback.bot.send_message(channel_id, full_caption, reply_markup=markup)
            await db.increment_quota(user.id, "text_post")
        
        await callback.message.edit_text("✅ **Berhasil!** Postingan kamu sudah terbit di channel dan kolom komentar sudah aktif.")
    except Exception as e:
        await callback.message.edit_text(f"❌ Gagal memposting: {str(e)}")
    
    await state.clear()
    from handlers.start import show_main_menu
    await show_main_menu(callback.message)
    
