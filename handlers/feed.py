import os
import html
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
    sisa_t = max(0, 3 - user.text_posts_today)
    sisa_f = max(0, 1 - user.photo_posts_today)
    
    text = (
        "📱 <b>UPDATE FEED CHANNEL</b>\n\n"
        f"📝 Sisa kuota teks: <b>{sisa_t}/3</b>\n"
        f"📸 Sisa kuota foto: <b>{sisa_f}/1</b>\n\n"
        "Silakan kirim teks atau foto + caption sekarang:"
    )
    kb = [[InlineKeyboardButton(text="🔙 Batal", callback_data="main_menu")]]
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")
    await state.set_state(FeedState.waiting_content)

@router.message(FeedState.waiting_content, F.text | F.photo)
async def process_feed_input(message: types.Message, state: FSMContext, db: DatabaseService):
    user = await db.get_user(message.from_user.id)
    is_photo = bool(message.photo)
    
    # Validasi Kuota
    if is_photo and not user.is_premium and user.photo_posts_today >= 1:
        return await message.answer("⚠️ Kuota foto harianmu sudah habis!")
    if not is_photo and not user.is_premium and user.text_posts_today >= 3:
        return await message.answer("⚠️ Kuota teks harianmu sudah habis!")

    f_id = message.photo[-1].file_id if is_photo else None
    f_cap = message.caption or message.text
    await state.update_data(f_file_id=f_id, f_caption=f_cap, f_type="photo" if is_photo else "text")
    
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
    bot_user = os.getenv("BOT_USERNAME")
    channel_id = os.getenv("FEED_CHANNEL_ID")
    
    # --- LOGIKA VISUAL BARIS 1 (NAMA & LINK) ---
    symbol = "👨" if user.gender == "pria" else "👩"
    link_text = "[👤 View Profile]"
    
    if is_anon:
        display_name = "ANONYMOUS USER"
        header = f"<b>👤 {display_name}</b>"
        # Hitung panjang garis untuk anonim (Symbol + Space + Name)
        line_len = len(display_name) + 3
    else:
        full_name_up = user.full_name.upper()
        profile_url = f"https://t.me/{bot_user}?start=view_{user.id}"
        header = f"{symbol} <b>{full_name_up}</b> <a href='{profile_url}'>{link_text}</a>"
        # Hitung panjang garis: Emoji(2) + Spasi(1) + Nama + Spasi(1) + LinkText
        line_len = len(full_name_up) + len(link_text) + 4

    # --- LOGIKA BARIS 2 (GARIS DINAMIS) ---
    # Menggunakan tanda "-" yang dibungkus <code> agar presisi
    separator = f"<code>{'-' * line_len}</code>"
    
    # --- LOGIKA BARIS 3 (ISI FEED) ---
    caption_clean = html.escape(data['f_caption'])
    isi_feed = f"<code><i>{caption_clean}</i></code>"
    
    # --- PENGGABUNGAN STRUKTUR (Format 5 Baris) ---
    full_text = (
        f"{header}\n"         # Baris 1
        f"{separator}\n\n"    # Baris 2 & Spasi Kosong
        f"{isi_feed}\n\n"      # Baris 3 & Spasi Kosong
        f"#{user.gender} #{user.city_hashtag.replace('#','')} #PickMeFeed" # Baris 5
    )

    try:
        # Tanpa reply_markup agar kolom komentar otomatis muncul
        if data['f_type'] == "photo":
            await callback.bot.send_photo(
                channel_id, 
                photo=data['f_file_id'], 
                caption=full_text, 
                parse_mode="HTML"
            )
            await db.increment_quota(user.id, "photo_post")
        else:
            await callback.bot.send_message(
                channel_id, 
                full_text, 
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            await db.increment_quota(user.id, "text_post")
            
        await callback.message.edit_text("✅ <b>Berhasil Terbit!</b>\nVisual garis sudah simetris dengan namamu.", parse_mode="HTML")
    except Exception as e:
        await callback.message.edit_text(f"❌ Gagal memposting: {e}")
    
    await state.clear()
    from handlers.start import show_main_menu
    await show_main_menu(callback.message)
    
