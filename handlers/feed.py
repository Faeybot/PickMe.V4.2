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
    text = (f"📱 **UPDATE FEED**\n\n📝 Sisa kuota teks: {max(0, 3 - user.text_posts_today)}/3\n"
            f"📸 Sisa kuota foto: {max(0, 1 - user.photo_posts_today)}/1\n\nKirim Teks atau Foto + Caption:")
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Batal", callback_data="main_menu")]]))
    await state.set_state(FeedState.waiting_content)

@router.message(FeedState.waiting_content, F.text | F.photo)
async def process_feed_input(message: types.Message, state: FSMContext, db: DatabaseService):
    user = await db.get_user(message.from_user.id)
    is_photo = bool(message.photo)
    if (is_photo and not user.is_premium and user.photo_posts_today >= 1) or (not is_photo and not user.is_premium and user.text_posts_today >= 3):
        return await message.answer("⚠️ Kuota harianmu habis!")

    await state.update_data(f_file_id=message.photo[-1].file_id if is_photo else None, f_caption=message.caption or message.text, f_type="photo" if is_photo else "text")
    kb = [[InlineKeyboardButton(text="👤 Tampilkan Profil", callback_data="p_visible")], [InlineKeyboardButton(text="🎭 Anonim", callback_data="p_hidden")]]
    await message.answer("Tampilkan profil di channel?", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await state.set_state(FeedState.confirm_post)

@router.callback_query(F.data.startswith("p_"), FeedState.confirm_post)
async def finalize_feed_post(callback: types.CallbackQuery, state: FSMContext, db: DatabaseService):
    data, user = await state.get_data(), await db.get_user(callback.from_user.id)
    is_anon = callback.data == "p_hidden"
    
    # FORMAT 5 LINE & BOLD FIX
    symbol = "👨" if user.gender == "pria" else "👩"
    header = "👤 **Anonim**" if is_anon else f"{symbol} **{user.full_name}**"
    full_text = f"{header}\n\n{data['f_caption']}\n\n#{user.gender} #{user.city_hashtag.replace('#','')} #PickMeFeed"
    
    kb = [[InlineKeyboardButton(text="👤 Lihat Profil Lengkap", url=f"https://t.me/{os.getenv('BOT_USERNAME')}?start=view_{user.id}")]] if not is_anon else []

    try:
        if data['f_type'] == "photo":
            await callback.bot.send_photo(os.getenv("FEED_CHANNEL_ID"), photo=data['f_file_id'], caption=full_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
            await db.increment_quota(user.id, "photo_post")
        else:
            await callback.bot.send_message(os.getenv("FEED_CHANNEL_ID"), full_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
            await db.increment_quota(user.id, "text_post")
        await callback.message.edit_text("✅ Berhasil!")
    except Exception as e: await callback.message.edit_text(f"❌ Gagal: {e}")
    
    await state.clear()
    from handlers.start import show_main_menu
    await show_main_menu(callback.message)
    
