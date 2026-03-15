from aiogram import Router, F, types
from aiogram.filters import Command
from services.database import DatabaseService
import os

router = Router()

# Ambil data dari Environment Variable
FEED_CHANNEL_ID = os.getenv("FEED_CHANNEL_ID")
PUBLIC_GROUP_ID = os.getenv("PUBLIC_GROUP_ID")
# Tambahkan dua variabel ini di Railway agar tombol link aktif!
CH_LINK = os.getenv("CH_LINK") # Contoh isi: PickMeFeed
GR_LINK = os.getenv("GR_LINK") # Contoh isi: PickMeGroup

@router.message(Command("start"))
async def cmd_start(message: types.Message, db: DatabaseService):
    user_id = message.from_user.id
    
    try:
        # Cek status member (menggunakan ID angka)
        member_feed = await message.bot.get_chat_member(FEED_CHANNEL_ID, user_id)
        member_group = await message.bot.get_chat_member(PUBLIC_GROUP_ID, user_id)
        
        # Jika belum join (status: left, kicked, atau restricted jika perlu)
        if member_feed.status == "left" or member_group.status == "left":
            kb = [
                [types.InlineKeyboardButton(text="📢 Join Channel Feed", url=f"https://t.me/{CH_LINK}")],
                [types.InlineKeyboardButton(text="💬 Join Grup Publik", url=f"https://t.me/{GR_LINK}")],
                [types.InlineKeyboardButton(text="✅ Saya Sudah Join", callback_data="check_join")]
            ]
            markup = types.InlineKeyboardMarkup(inline_keyboard=kb)
            return await message.answer("Halo! Untuk menggunakan bot ini, kamu wajib join channel dan grup kami dulu ya.", reply_markup=markup)
    except Exception as e:
        print(f"Error check member: {e}")
        # Jika bot belum jadi admin, dia akan error di sini. Kita izinkan lewat dulu agar tidak stuck.

    # CEK USER DI DATABASE
    user = await db.get_user(user_id)
    if not user:
        kb = [[types.InlineKeyboardButton(text="📝 Daftar Sekarang", callback_data="start_register")]]
        await message.answer(
            "Selamat datang di **PickMe Bot**! 💘\n\nSepertinya kamu belum terdaftar. Yuk, buat profil singkatmu agar bisa mulai mencari teman atau pasangan!",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb)
        )
    else:
        await show_main_menu(message)

@router.callback_query(F.data == "check_join")
async def check_join_callback(callback: types.CallbackQuery, db: DatabaseService):
    # Fungsi ini dijalankan saat user klik "Saya Sudah Join"
    await callback.message.delete() # Hapus pesan lama
    await cmd_start(callback.message, db)

async def show_main_menu(message: types.Message):
    kb = [
        [types.InlineKeyboardButton(text="📸 Post Feed", callback_data="menu_feed"),
         types.InlineKeyboardButton(text="💘 Swipe Dating", callback_data="menu_swipe")],
        [types.InlineKeyboardButton(text="⚙️ Edit Profil", callback_data="menu_edit"),
         types.InlineKeyboardButton(text="🔍 Filter", callback_data="menu_filter")]
    ]
    markup = types.InlineKeyboardMarkup(inline_keyboard=kb)
    # Gunakan edit_text jika dipanggil dari callback, atau answer jika dari message
    if isinstance(message, types.Message):
        await message.answer("🌟 **Menu Utama PickMe**\nSilakan pilih layanan di bawah ini:", reply_markup=markup)
    else:
        await message.edit_text("🌟 **Menu Utama PickMe**\nSilakan pilih layanan di bawah ini:", reply_markup=markup)
        
