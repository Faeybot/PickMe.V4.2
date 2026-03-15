from aiogram import Router, F, types
from aiogram.filters import Command
from services.database import DatabaseService
import os

router = Router()

# Ambil ID Channel dari Environment Variable
FEED_CHANNEL_ID = os.getenv("FEED_CHANNEL_ID")
PUBLIC_GROUP_ID = os.getenv("PUBLIC_GROUP_ID")

@router.message(Command("start"))
async def cmd_start(message: types.Message, db: DatabaseService):
    user_id = message.from_user.id
    
    # LOGIKA CEK JOIN (Gunakan try-except agar tidak crash jika bot belum di-add)
    try:
        member_feed = await message.bot.get_chat_member(FEED_CHANNEL_ID, user_id)
        member_group = await message.bot.get_chat_member(PUBLIC_GROUP_ID, user_id)
        
        if member_feed.status == "left" or member_group.status == "left":
            kb = [
                [types.InlineKeyboardButton(text="📢 Join Channel Feed", url=f"https://t.me/{FEED_CHANNEL_ID.replace('-100','')}")],
                [types.InlineKeyboardButton(text="💬 Join Grup Publik", url=f"https://t.me/{PUBLIC_GROUP_ID.replace('-100','')}")],
                [types.InlineKeyboardButton(text="✅ Saya Sudah Join", callback_data="check_join")]
            ]
            markup = types.InlineKeyboardMarkup(inline_keyboard=kb)
            return await message.answer("Halo! Untuk menggunakan bot ini, kamu wajib join channel dan grup kami dulu ya.", reply_markup=markup)
    except:
        pass # Jika error cek member, abaikan sementara agar user tidak stuck

    # CEK USER DI DATABASE
    user = await db.get_user(user_id)
    if not user:
        # Jika belum ada di DB, arahkan ke pendaftaran
        await message.answer("Selamat datang di PickMe! Sepertinya kamu belum terdaftar. Yuk, isi profil dulu!")
        # Di sini nanti kita panggil fungsi mulai daftar dari register.py
    else:
        # Jika sudah ada, tampilkan menu utama
        await show_main_menu(message)

async def show_main_menu(message: types.Message):
    kb = [
        [types.InlineKeyboardButton(text="📸 Post Feed", callback_data="menu_feed"),
         types.InlineKeyboardButton(text="💘 Swipe Dating", callback_data="menu_swipe")],
        [types.InlineKeyboardButton(text="⚙️ Edit Profil", callback_data="menu_edit"),
         types.InlineKeyboardButton(text="🔍 Filter", callback_data="menu_filter")]
    ]
    markup = types.InlineKeyboardMarkup(inline_keyboard=kb)
    await message.answer("Pilih menu di bawah ini:", reply_markup=markup)
