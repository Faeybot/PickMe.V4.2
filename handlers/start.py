from aiogram import Router, F, types
from aiogram.filters import Command
from services.database import DatabaseService
import os

router = Router()

# Pastikan variabel ini ada di Environment Railway kamu
FEED_CHANNEL_ID = os.getenv("FEED_CHANNEL_ID")
PUBLIC_GROUP_ID = os.getenv("PUBLIC_GROUP_ID")
CH_LINK = os.getenv("CH_LINK") # Username channel tanpa @
GR_LINK = os.getenv("GR_LINK") # Username grup tanpa @

# Tambahkan di dalam cmd_start (start.py)
@router.message(Command("start"))
async def cmd_start(message: types.Message, db: DatabaseService):
    user_id = message.from_user.id
    args = message.text.split()
    
    # Fitur Deep Linking: /start view_12345
    if len(args) > 1 and args[1].startswith("view_"):
        target_id = int(args[1].replace("view_", ""))
        target = await db.get_user(target_id)
        if target:
            # Cek apakah user sudah daftar sendiri
            me = await db.get_user(user_id)
            if not me:
                return await message.answer("👋 Halo! Daftar dulu yuk untuk bisa berinteraksi dengan profil ini.")
            
            # Tampilkan profil target
            caption = f"👤 **Profil: {target.full_name}**\n📍 {target.location_name}\n\n{target.bio}"
            return await message.answer_photo(photo=target.photo_id, caption=caption)

    # 1. CEK MANDATORY JOIN (Agar bot tidak spammer)
    try:
        member_feed = await message.bot.get_chat_member(FEED_CHANNEL_ID, user_id)
        member_group = await message.bot.get_chat_member(PUBLIC_GROUP_ID, user_id)
        
        if member_feed.status in ["left", "kicked"] or member_group.status in ["left", "kicked"]:
            kb = [
                [types.InlineKeyboardButton(text="📢 Join Channel Feed", url=f"https://t.me/{CH_LINK}")],
                [types.InlineKeyboardButton(text="💬 Join Grup Publik", url=f"https://t.me/{GR_LINK}")],
                [types.InlineKeyboardButton(text="✅ Saya Sudah Join", callback_data="check_join")]
            ]
            return await message.answer(
                "❌ **Akses Ditolak!**\n\nKamu harus bergabung di Channel dan Grup kami terlebih dahulu untuk menggunakan bot ini.",
                reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb)
            )
    except Exception as e:
        print(f"Error check member: {e}")

    # 2. CEK REGISTRASI
    user = await db.get_user(user_id)
    if not user:
        kb = [[types.InlineKeyboardButton(text="📝 Daftar Sekarang", callback_data="start_register")]]
        return await message.answer(
            "👋 **Selamat Datang di PickMe Bot!**\n\nTempat cari teman, kencan, atau sekadar ngopi. Profil kamu belum terdaftar nih. Yuk, buat dulu!",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb)
        )
    
    # 3. TAMPILKAN MENU UTAMA JIKA SUDAH DAFTAR
    await show_main_menu(message)

@router.callback_query(F.data == "check_join")
async def check_join_callback(callback: types.CallbackQuery, db: DatabaseService):
    await callback.message.delete()
    await cmd_start(callback.message, db)

async def show_main_menu(message: types.Message):
    # Struktur Menu sesuai konsep Antarmuka yang kita bahas
    kb = [
        [types.InlineKeyboardButton(text="🔍 Cari Pasangan", callback_data="menu_swipe"),
         types.InlineKeyboardButton(text="📱 Update Feed", callback_data="menu_feed")],
        [types.InlineKeyboardButton(text="❤️ Suka Kamu", callback_data="menu_liked_me"),
         types.InlineKeyboardButton(text="👤 Profil Saya", callback_data="view_my_profile")],
        [types.InlineKeyboardButton(text="✏️ Edit Profil", callback_data="menu_edit"),
         types.InlineKeyboardButton(text="⚙️ Pengaturan", callback_data="menu_settings")]
    ]
    markup = types.InlineKeyboardMarkup(inline_keyboard=kb)
    
    text = "🌟 **MENU UTAMA PICKME**\n\nSilakan pilih menu di bawah untuk berinteraksi:"
    
    if isinstance(message, types.Message):
        await message.answer(text, reply_markup=markup)
    else:
        # Jika dipanggil dari callback_query (misal klik 'back')
        await message.edit_text(text, reply_markup=markup)

@router.callback_query(F.data == "view_my_profile")
async def view_my_profile(callback: types.CallbackQuery, db: DatabaseService):
    user = await db.get_user(callback.from_user.id)
    caption = (
        f"📇 **Profil Kamu**\n\n"
        f"👤 {user.full_name}, {user.age} thn\n"
        f"🚻 Gender: {user.gender}\n"
        f"🔥 Minat: {user.interest}\n"
        f"🎯 Mencari: {user.looking_for}\n"
        f"📍 Lokasi: {user.location_name}\n"
        f"📝 Bio: {user.bio}\n\n"
        f"📊 **Statistik Hari Ini:**\n"
        f"💬 Pesan: {user.messages_sent_today}/1\n"
        f"📱 Feed: {user.text_posts_today + user.photo_posts_today}/4"
    )
    kb = [[types.InlineKeyboardButton(text="🔙 Kembali", callback_data="main_menu")]]
    await callback.message.answer_photo(
        photo=user.photo_id, 
        caption=caption, 
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb)
    )

@router.callback_query(F.data == "main_menu")
async def back_to_menu(callback: types.CallbackQuery):
    await show_main_menu(callback.message)
