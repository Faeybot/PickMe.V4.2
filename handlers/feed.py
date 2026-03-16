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
    
    # Menghitung sisa kuota (Gratis vs VIP akan ditangani di level DB/Service)
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
    
    # Proteksi kuota harian
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
    await message.answer(
        "<b>PILIH MODE TAMPILAN</b>\n\n"
        "Jika memilih anonim, Sultan butuh akses khusus untuk membongkar profilmu!", 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
        parse_mode="HTML"
    )
    await state.set_state(FeedState.confirm_post)

@router.callback_query(F.data.startswith("p_"), FeedState.confirm_post)
async def finalize_feed_post(callback: types.CallbackQuery, state: FSMContext, db: DatabaseService):
    data = await state.get_data()
    user = await db.get_user(callback.from_user.id)
    is_anon = callback.data == "p_hidden"
    bot_user = os.getenv("BOT_USERNAME")
    channel_id = os.getenv("FEED_CHANNEL_ID")
    
    # --- 1. HEADER & LINK (Dibuat tetap muncul meski Anonim) ---
    symbol = "👨" if user.gender == "pria" else "👩"
    profile_url = f"https://t.me/{bot_user}?start=view_{user.id}"
    link_text = "🔗 View Profile"
    
    if is_anon:
        display_name = "ANONYMOUS"
        header = f"<b>👤 {display_name}</b> | <a href='{profile_url}'>{link_text}</a>"
    else:
        display_name = user.full_name.upper()
        header = f"{symbol} <b>{display_name}</b> | <a href='{profile_url}'>{link_text}</a>"

    # --- 2. GARIS PEMISAH DINAMIS (Menggunakan Em-Dash) ---
    line_len = (len(display_name) + 18) // 2
    separator = f"<code>{'—' * line_len}</code>"
    
    # --- 3. ISI FEED (Blockquote + Italic) ---
    caption_clean = html.escape(data['f_caption'])
    isi_feed = f"<blockquote><i>{caption_clean}</i></blockquote>"
    
    # --- 4. PENYUSUNAN TEXT FINAL ---
    full_text = (
        f"{header}\n"
        f"{separator}\n"
        f"{isi_feed}\n"
        f"#{user.gender} #{user.city_hashtag.replace('#','')} #PickMeFeed"
    )

    try:
        # Kirim ke Channel Utama
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
            
        # --- 5. REDIRECT KE MENU BOOST (Upselling) ---
        kb_boost = [
            [InlineKeyboardButton(text="🚀 Boost Postingan Ini!", callback_data="menu_boost")],
            [InlineKeyboardButton(text="🏠 Menu Utama", callback_data="main_menu")]
        ]
        
        await callback.message.edit_text(
            "✅ <b>BERHASIL TERBIT!</b>\n\n"
            "Postinganmu sudah tayang di channel. Mau dapat lebih banyak poin? "
            "Gunakan <b>Boost</b> agar fotomu auto-repost ke puncak feed!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_boost),
            parse_mode="HTML"
        )
        
    except Exception as e:
        await callback.message.edit_text(f"❌ Gagal: {e}")
    
    await state.clear()

# --- LOGIKA PENANGANAN MENU BOOST ---
@router.callback_query(F.data == "menu_boost")
async def show_boost_options(callback: types.CallbackQuery, db: DatabaseService):
    user = await db.get_user(callback.from_user.id)
    
    # Cek limit harian boost (1x per 24 jam)
    if not await db.can_user_boost_today(user.id):
        return await callback.answer("🚫 Kamu sudah menggunakan jatah Boost hari ini!", show_alert=True)

    text = (
        "🚀 <b>BOOST FEED MENU</b>\n\n"
        "Pilih paket boost untuk menaikkan pesonamu ke puncak feed secara otomatis:\n\n"
        "1️⃣ <b>1 Boost</b> (2x Tampil / 6 Jam) - Rp 5rb\n"
        "2️⃣ <b>5 Boost</b> (6x Tampil / 12 Jam) - Rp 25rb\n"
        "3️⃣ <b>30 Boost</b> (24x Tampil / 24 Jam) - Rp 150rb\n\n"
        f"Saldo Boost saat ini: <b>{user.paid_boost_balance}</b>\n"
        f"Kuota Gratis VIP+: <b>{user.weekly_free_boost}</b>"
    )
    
    kb = [
        [InlineKeyboardButton(text="Gunakan Kuota Gratis", callback_data="apply_boost_free")],
        [InlineKeyboardButton(text="Beli Paket Boost", callback_data="buy_boost_package")],
        [InlineKeyboardButton(text="🔙 Batal", callback_data="main_menu")]
    ]
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")
                             
