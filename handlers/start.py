from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from services.database import DatabaseService
import os

router = Router()

FEED_CHANNEL_ID = os.getenv("FEED_CHANNEL_ID")
PUBLIC_GROUP_ID = os.getenv("PUBLIC_GROUP_ID")
CH_LINK = os.getenv("CH_LINK")
GR_LINK = os.getenv("GR_LINK")

class ChatState(StatesGroup):
    waiting_for_message = State()

@router.message(Command("start"))
async def cmd_start(message: types.Message, db: DatabaseService, state: FSMContext):
    user_id = message.from_user.id
    args = message.text.split()
    
    # HANDLER VIEW PROFIL DARI CHANNEL
    if len(args) > 1 and args[1].startswith("view_"):
        target_id = int(args[1].replace("view_", ""))
        target = await db.get_user(target_id)
        me = await db.get_user(user_id)
        
        if not me:
            return await message.answer("👋 Daftar dulu yuk untuk melihat profil ini!")
        if not target:
            return await message.answer("Profil tidak ditemukan.")

        # Tampilkan Bio Saja (Foto Terkunci)
        text = (
            f"👤 **PROFIL: {target.full_name}**\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🎂 Usia: {target.age}\n"
            f"🎨 Minat: {target.interest}\n"
            f"📍 Lokasi: {target.location_name}\n\n"
            f"📝 **Bio:**\n{target.bio}\n"
            f"━━━━━━━━━━━━━━━\n"
            "📸 *Foto & Chat terkunci. Gunakan kuotamu:* "
        )
        
        kb = [
            [
                InlineKeyboardButton(text=f"🖼️ Lihat Foto ({3 - me.profiles_viewed_today}/3)", callback_data=f"unl_photo_{target.id}"),
                InlineKeyboardButton(text=f"💌 Chat ({3 - me.messages_sent_today}/3)", callback_data=f"unl_chat_{target.id}")
            ],
            [InlineKeyboardButton(text="🔙 Kembali", callback_data="main_menu")]
        ]
        return await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

    # CEK JOIN (Feature lama tetap dipertahankan)
    try:
        member_feed = await message.bot.get_chat_member(FEED_CHANNEL_ID, user_id)
        if member_feed.status in ["left", "kicked"]:
            kb = [[InlineKeyboardButton(text="📢 Join Channel", url=f"https://t.me/{CH_LINK}")],
                  [InlineKeyboardButton(text="✅ Sudah Join", callback_data="check_join")]]
            return await message.answer("❌ Join channel dulu ya!", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    except: pass

    user = await db.get_user(user_id)
    if not user:
        kb = [[InlineKeyboardButton(text="📝 Daftar Sekarang", callback_data="start_register")]]
        return await message.answer("👋 Selamat Datang! Yuk buat profil dulu.", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    
    await show_main_menu(message)

# SISTEM UNLOCK & NOTIFIKASI PESAN
@router.callback_query(F.data.startswith("unl_"))
async def process_unlock(callback: types.CallbackQuery, state: FSMContext, db: DatabaseService):
    action, target_id = callback.data.split("_")[1], int(callback.data.split("_")[2])
    me = await db.get_user(callback.from_user.id)
    target = await db.get_user(target_id)

    if action == "photo":
        if me.profiles_viewed_today >= 3 and not me.is_premium:
            return await callback.answer("❌ Kuota Lihat Foto habis!", show_alert=True)
        await db.increment_quota(me.id, "view_profile")
        await callback.message.answer_photo(photo=target.photo_id, caption=f"Foto profil {target.full_name}")
        await callback.answer("Kuota terpakai!")
    
    elif action == "chat":
        if me.messages_sent_today >= 3 and not me.is_premium:
            return await callback.answer("❌ Kuota Chat habis!", show_alert=True)
        await state.update_data(chat_target_id=target.id)
        await callback.message.answer(f"💌 **Kirim Pesan ke {target.full_name}**\n\nTulis pesanmu di bawah ini:")
        await state.set_state(ChatState.waiting_for_message)
        await callback.answer()

@router.message(ChatState.waiting_for_message)
async def forward_to_target(message: types.Message, state: FSMContext, db: DatabaseService):
    data = await state.get_data()
    target_id = data.get("chat_target_id")
    sender = await db.get_user(message.from_user.id)
    
    notif_text = (
        f"💌 **PESAN BARU MASUK!**\n"
        f"━━━━━━━━━━━━━━━\n"
        f"“ {message.text} ”\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Dari: **{sender.full_name}**\n\n"
        f"Ingin membalas?"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Lihat Profil", url=f"https://t.me/{os.getenv('BOT_USERNAME')}?start=view_{sender.id}")],
        [InlineKeyboardButton(text="💬 Balas Pesan", callback_data=f"unl_chat_{sender.id}")],
        [InlineKeyboardButton(text="🗑️ Abaikan", callback_data="delete_msg")]
    ])

    try:
        await message.bot.send_message(chat_id=target_id, text=notif_text, reply_markup=kb)
        await db.increment_quota(sender.id, "message")
        await message.answer("✅ Pesan terkirim!")
    except:
        await message.answer("❌ Gagal mengirim pesan.")
    
    await state.clear()
    await show_main_menu(message)

@router.callback_query(F.data == "delete_msg")
async def delete_msg(callback: types.CallbackQuery):
    await callback.message.delete()

@router.callback_query(F.data == "check_join")
async def check_join_callback(callback: types.CallbackQuery, db: DatabaseService, state: FSMContext):
    await callback.message.delete()
    await cmd_start(callback.message, db, state)

async def show_main_menu(message: types.Message):
    kb = [[InlineKeyboardButton(text="🔍 Cari Pasangan", callback_data="menu_swipe"),
           InlineKeyboardButton(text="📱 Update Feed", callback_data="menu_feed")],
          [InlineKeyboardButton(text="❤️ Suka Kamu", callback_data="menu_liked_me"),
           InlineKeyboardButton(text="👤 Profil Saya", callback_data="view_my_profile")],
          [InlineKeyboardButton(text="✏️ Edit Profil", callback_data="menu_edit")]]
    text = "🌟 **MENU UTAMA PICKME**"
    if isinstance(message, types.Message): await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    else: await message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data == "view_my_profile")
async def view_my_profile(callback: types.CallbackQuery, db: DatabaseService):
    user = await db.get_user(callback.from_user.id)
    caption = f"📇 **Profil Kamu**\n\n👤 {user.full_name}, {user.age} thn\n📊 **Kuota Hari Ini:**\n💬 Chat: {user.messages_sent_today}/3\n🖼️ Foto: {user.profiles_viewed_today}/3"
    await callback.message.answer_photo(photo=user.photo_id, caption=caption, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙", callback_data="main_menu")]]))

@router.callback_query(F.data == "main_menu")
async def back_to_menu(callback: types.CallbackQuery):
    await show_main_menu(callback.message)
    
