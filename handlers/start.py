from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from services.database import DatabaseService
import os

router = Router()
class ChatState(StatesGroup): waiting_for_message = State()

@router.message(Command("start"))
async def cmd_start(message: types.Message, db: DatabaseService, state: FSMContext):
    user_id = message.from_user.id
    args = message.text.split()
    
    if len(args) > 1 and args[1].startswith("view_"):
        target = await db.get_user(int(args[1].replace("view_", "")))
        me = await db.get_user(user_id)
        if not me: return await message.answer("👋 Daftar dulu yuk!")
        text = f"👤 **PROFIL: {target.full_name}**\n━━━━━━━━━━━━━━━\n🎂 Usia: {target.age}\n📍 Lokasi: {target.location_name}\n\n📝 **Bio:**\n{target.bio}\n━━━━━━━━━━━━━━━\n📸 *Foto & Chat terkunci:*"
        kb = [[InlineKeyboardButton(text=f"🖼️ Foto ({3-me.profiles_viewed_today}/3)", callback_data=f"unl_photo_{target.id}"),
               InlineKeyboardButton(text=f"💌 Chat ({3-me.messages_sent_today}/3)", callback_data=f"unl_chat_{target.id}")],
              [InlineKeyboardButton(text="🔙 Kembali", callback_data="main_menu")]]
        return await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

    user = await db.get_user(user_id)
    if not user: return await message.answer("👋 Selamat Datang! Yuk buat profil.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📝 Daftar", callback_data="start_register")]]))
    await show_main_menu(message)

@router.callback_query(F.data.startswith("unl_"))
async def process_unlock(callback: types.CallbackQuery, state: FSMContext, db: DatabaseService):
    action, target_id = callback.data.split("_")[1], int(callback.data.split("_")[2])
    me, target = await db.get_user(callback.from_user.id), await db.get_user(target_id)

    if action == "photo":
        if me.profiles_viewed_today >= 3 and not me.is_premium: return await callback.answer("❌ Kuota habis!", show_alert=True)
        await db.increment_quota(me.id, "view_profile")
        await callback.message.answer_photo(target.photo_id, caption=f"Foto {target.full_name}")
    elif action == "chat":
        if me.messages_sent_today >= 3 and not me.is_premium: return await callback.answer("❌ Kuota habis!", show_alert=True)
        await state.update_data(chat_target_id=target.id)
        await callback.message.answer(f"💌 Kirim pesan ke {target.full_name}:")
        await state.set_state(ChatState.waiting_for_message)
    await callback.answer()

@router.message(ChatState.waiting_for_message)
async def forward_to_target(message: types.Message, state: FSMContext, db: DatabaseService):
    data = await state.get_data()
    sender = await db.get_user(message.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👤 Profil", url=f"https://t.me/{os.getenv('BOT_USERNAME')}?start=view_{sender.id}")],
                                               [InlineKeyboardButton(text="💬 Balas", callback_data=f"unl_chat_{sender.id}")],
                                               [InlineKeyboardButton(text="🗑️ Abaikan", callback_data="delete_msg")]])
    try:
        await message.bot.send_message(data['chat_target_id'], f"💌 **PESAN BARU!**\n\n“ {message.text} ”\n\nDari: **{sender.full_name}**", reply_markup=kb)
        await db.increment_quota(sender.id, "message")
        await message.answer("✅ Terkirim!")
    except: await message.answer("❌ Gagal!")
    await state.clear()
    await show_main_menu(message)

async def show_main_menu(message: types.Message):
    kb = [[InlineKeyboardButton(text="🔍 Cari", callback_data="menu_swipe"), InlineKeyboardButton(text="📱 Feed", callback_data="menu_feed")],
          [InlineKeyboardButton(text="❤️ Suka", callback_data="menu_liked_me"), InlineKeyboardButton(text="👤 Profil", callback_data="view_my_profile")],
          [InlineKeyboardButton(text="✏️ Edit", callback_data="menu_edit")]]
    if isinstance(message, types.Message): await message.answer("🌟 **MENU UTAMA**", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    else: await message.edit_text("🌟 **MENU UTAMA**", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data == "main_menu")
async def back_to_menu(callback: types.CallbackQuery): await show_main_menu(callback.message)

@router.callback_query(F.data == "delete_msg")
async def delete_msg(callback: types.CallbackQuery): await callback.message.delete()
    
