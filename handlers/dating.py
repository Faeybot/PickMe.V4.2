import os
from aiogram import Router, F, types
from services.database import DatabaseService

router = Router()

@router.callback_query(F.data == "menu_swipe")
async def start_swipe(callback: types.CallbackQuery, db: DatabaseService):
    user = await db.get_user(callback.from_user.id)
    
    # Ambil 1 calon pasangan secara acak dari database
    target = await db.get_potential_match(user.id, user.interest)
    
    if not target:
        return await callback.message.answer("🥺 Belum ada profil baru yang sesuai kriteria kamu. Coba lagi nanti ya!")

    # Tampilkan Profil Calon Pasangan
    caption = (
        f"💘 **{target.full_name}, {target.age}**\n"
        f"📍 {target.location_name}\n\n"
        f"Tentang: {target.gender}\n"
        f"Hashtag: {target.city_hashtag}"
    )
    
    kb = [
        [
            types.InlineKeyboardButton(text="❌ Pass", callback_data=f"swipe_next"),
            types.InlineKeyboardButton(text="💘 Like", callback_data=f"like_{target.id}")
        ],
        [types.InlineKeyboardButton(text="💌 Kirim Pesan Privat", callback_data=f"chat_{target.id}")]
    ]
    
    await callback.message.answer_photo(
        photo=target.photo_id,
        caption=caption,
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb)
    )

@router.callback_query(F.data == "swipe_next")
async def swipe_next(callback: types.CallbackQuery, db: DatabaseService):
    # Hapus pesan lama dan cari yang baru (efek swipe)
    await callback.message.delete()
    await start_swipe(callback, db)

@router.callback_query(F.data.startswith("like_"))
async def handle_like(callback: types.CallbackQuery, db: DatabaseService):
    target_id = int(callback.data.split("_")[1])
    sender = await db.get_user(callback.from_user.id)
    
    # Notifikasi ke Target (Bahwa ada yang menyukai dia)
    try:
        await callback.bot.send_message(
            target_id, 
            f"🔥 **Seseorang menyukai profilmu!**\n\n"
            f"Buka menu Swipe untuk mencari tahu siapa dia. Siapa tahu dia jodohmu! 😉"
        )
    except:
        pass # Jika target memblokir bot

    await callback.answer("💘 Like terkirim! Semoga dia menyukaimu juga.")
    await swipe_next(callback, db)

@router.callback_query(F.data.startswith("chat_"))
async def handle_chat_paywall(callback: types.CallbackQuery, db: DatabaseService):
    user = await db.get_user(callback.from_user.id)
    target_id = callback.data.split("_")[1]
    
    # CEK STATUS PREMIUM
    if not user.is_premium:
        text_premium = (
            "🔒 **Fitur Premium Detected!**\n\n"
            "Kamu ingin langsung mengobrol dengan dia? Fitur kirim pesan privat hanya tersedia untuk member **Premium**.\n\n"
            "✨ **Keuntungan Premium:**\n"
            "• Chat siapa saja tanpa batas\n"
            "• Swipe tanpa iklan/limit\n"
            "• Profil diprioritaskan\n\n"
            "Hubungi @Admin_PickMe untuk upgrade sekarang!"
        )
        await callback.message.answer(text_premium)
    else:
        # Jika Premium, berikan instruksi cara chat
        await callback.message.answer("✅ Kamu adalah member Premium! Silakan ketik pesan yang ingin kamu sampaikan, kami akan meneruskannya.")
        # Di sini bisa ditambahkan State untuk handling pesan privat
        
