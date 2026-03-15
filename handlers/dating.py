@router.callback_query(F.data == "menu_swipe")
async def start_swipe(callback: types.CallbackQuery, db: DatabaseService):
    user = await db.get_user(callback.from_user.id)
    
    # AMBIL CALON MATCH (Logika Database)
    potential_match = await db.get_potential_match(user.id, user.interest)
    
    if not potential_match:
        return await callback.answer("Ups, belum ada orang baru di sekitarmu. Coba lagi nanti!", show_alert=True)
    
    caption = f"💘 {potential_match.full_name}, {potential_match.age}\n📍 {potential_match.location_name}"
    
    kb = [
        [types.InlineKeyboardButton(text="❌ Pass", callback_data=f"swipe_next"),
         types.InlineKeyboardButton(text="💘 Like", callback_data=f"like_{potential_match.id}")],
        [types.InlineKeyboardButton(text="💌 Kirim Pesan Privat", callback_data=f"chat_{potential_match.id}")]
    ]
    await callback.message.answer_photo(potential_match.photo_id, caption=caption, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("chat_"))
async def handle_paywall(callback: types.CallbackQuery, db: DatabaseService):
    user = await db.get_user(callback.from_user.id)
    
    if not user.is_premium:
        await callback.message.answer(
            "🔒 **Fitur Premium Detected!**\n\n"
            "Kamu harus menjadi member Premium untuk mengirim pesan privat langsung ke dia.\n\n"
            "✨ Keuntungan: Unlimited Chat & Swipe!"
        )
    else:
        await callback.message.answer("Silakan ketik pesanmu untuk dia...")
        # Lanjut ke state kirim pesan
                         
