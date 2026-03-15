from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from services.database import DatabaseService
from handlers.register import RegState # Menggunakan state yang sudah ada atau buat baru

router = Router()

# --- FITUR DISCOVERY (SWIPE) ---

@router.callback_query(F.data == "menu_swipe")
@router.callback_query(F.data == "swipe_next")
async def start_swipe(callback: types.CallbackQuery, db: DatabaseService):
    user = await db.get_user(callback.from_user.id)
    
    # Ambil 1 calon pasangan secara acak (Lawan Jenis)
    target = await db.get_potential_match(user.id, user.gender)
    
    if not target:
        return await callback.message.answer("🥺 Belum ada profil baru yang sesuai kriteria kamu. Coba lagi nanti ya!")

    caption = (
        f"💘 **{target.full_name}, {target.age}**\n"
        f"🔥 Minat: {target.interest}\n"
        f"🎯 Mencari: {target.looking_for}\n"
        f"📍 Lokasi: {target.location_name}\n"
        f"📝 Bio: {target.bio}\n\n"
        f"Hashtag: {target.city_hashtag}"
    )
    
    kb = [
        [
            types.InlineKeyboardButton(text="❌ Pass", callback_data="swipe_next"),
            types.InlineKeyboardButton(text="❤️ Like", callback_data=f"like_{target.id}")
        ],
        [types.InlineKeyboardButton(text="💌 Kirim Pesan Instan", callback_data=f"chat_{target.id}")]
    ]
    
    # Hapus pesan swipe sebelumnya agar tidak menumpuk
    try: await callback.message.delete()
    except: pass

    await callback.message.answer_photo(
        photo=target.photo_id,
        caption=caption,
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb)
    )

@router.callback_query(F.data.startswith("like_"))
async def handle_like(callback: types.CallbackQuery, db: DatabaseService):
    target_id = int(callback.data.split("_")[1])
    await db.add_like(callback.from_user.id, target_id)
    
    await callback.answer("💖 Kamu menyukai profil ini!")
    # Notifikasi ringan ke target (Tanpa buka identitas dulu)
    try:
        await callback.bot.send_message(target_id, "🔥 Seseorang baru saja menyukai profilmu! Cek di menu 'Suka Kamu'.")
    except: pass
    
    await start_swipe(callback, db)

# --- FITUR PESAN INSTAN (POPUP SYSTEM) ---

@router.callback_query(F.data.startswith("chat_"))
async def start_instant_chat(callback: types.CallbackQuery, db: DatabaseService, state: FSMContext):
    user = await db.get_user(callback.from_user.id)
    target_id = int(callback.data.split("_")[1])

    if not user.is_premium and user.messages_sent_today >= 1:
        return await callback.answer("⚠️ Kuota pesan gratis kamu (1/hari) sudah habis!", show_alert=True)

    await state.update_data(target_id=target_id)
    await callback.message.answer("✍️ Ketik pesan instan yang ingin kamu kirimkan:")
    await state.set_state("waiting_instant_message")

@router.message(F.text, F.state == "waiting_instant_message")
async def send_instant_message(message: types.Message, state: FSMContext, db: DatabaseService):
    data = await state.get_data()
    target_id = data['target_id']
    sender_id = message.from_user.id
    
    # Popup Notification untuk Penerima
    kb = [
        [types.InlineKeyboardButton(text="👤 Lihat Profil Pengirim", callback_data=f"view_sender_{sender_id}"),
         types.InlineKeyboardButton(text="📩 Buka Pesan", callback_data=f"open_msg_{sender_id}")]
    ]
    
    await message.bot.send_message(
        target_id, 
        "🔔 **Kamu mendapat pesan instan baru!**", 
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb)
    )
    
    # Simpan konten pesan di FSM/Temp (atau database jika perlu permanen)
    # Untuk simplifikasi kita gunakan prefix callback untuk isi pesan singkat atau state
    await db.increment_quota(sender_id, "message")
    await message.answer("✅ Pesanmu telah terkirim!")
    await state.clear()

# --- FITUR SIAPA YANG MENYUKAI SAYA ---

@router.callback_query(F.data == "menu_liked_me")
async def list_who_liked_me(callback: types.CallbackQuery, db: DatabaseService):
    likes = await db.get_my_likes(callback.from_user.id)
    
    if not likes:
        return await callback.answer("Belum ada yang menyukai profilmu.", show_alert=True)
    
    await callback.message.answer("❤️ **Orang yang menyukaimu:**")
    for like in likes[:5]: # Tampilkan 5 terbaru
        sender = await db.get_user(like.sender_id)
        text = f"👤 {sender.full_name}, {sender.age} thn\n📍 {sender.location_name}"
        kb = [[types.InlineKeyboardButton(text="👁️ Buka Profil (Jatah 1/hari)", callback_data=f"unlock_{sender.id}")]]
        await callback.message.answer(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("unlock_"))
async def unlock_profile(callback: types.CallbackQuery, db: DatabaseService):
    user = await db.get_user(callback.from_user.id)
    target_id = int(callback.data.split("_")[1])
    
    if not user.is_premium and user.profiles_opened_today >= 1:
        return await callback.answer("⚠️ Kamu sudah menggunakan jatah buka profil gratis hari ini!", show_alert=True)
    
    target = await db.get_user(target_id)
    await db.increment_quota(user.id, "view_profile")
    
    caption = f"🔓 **Profil Terbuka**\n\n👤 {target.full_name}\n📝 Bio: {target.bio}\n🔥 Minat: {target.interest}"
    await callback.message.answer_photo(photo=target.photo_id, caption=caption)
        
