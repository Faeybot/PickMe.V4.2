import os
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from services.database import DatabaseService
from utils.geocoder import get_city_name, create_hashtag

router = Router()

class RegState(StatesGroup):
    name = State()
    age = State()
    gender = State()
    interest = State()
    looking_for = State()
    bio = State()
    photo = State()
    location = State()

@router.callback_query(F.data == "start_register")
async def start_reg_tos(callback: types.CallbackQuery, state: FSMContext):
    text = (
        "⚠️ **Aturan Komunitas**\n\n"
        "1. Minimal usia 18 tahun.\n"
        "2. Dilarang spam/scam/judi online.\n"
        "3. Hormati sesama pengguna.\n\n"
        "Apakah kamu setuju dengan aturan ini?"
    )
    kb = [[types.InlineKeyboardButton(text="✅ Setuju & Lanjut", callback_data="tos_agree")]]
    await callback.message.edit_text(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data == "tos_agree")
async def tos_agreed(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Bagus! Siapa nama panggilanmu?")
    await state.set_state(RegState.name)

@router.message(RegState.name)
async def reg_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text[:15])
    await message.answer("Berapa usiamu? (Angka saja, contoh: 20)")
    await state.set_state(RegState.age)

@router.message(RegState.age)
async def reg_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("Tolong masukkan angka saja!")
    await state.update_data(age=int(message.text))
    
    kb = [[types.InlineKeyboardButton(text="Pria 👨", callback_data="g_Pria"),
           types.InlineKeyboardButton(text="Wanita 👩", callback_data="g_Wanita")]]
    await message.answer("Pilih Gendermu:", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))
    await state.set_state(RegState.gender)

@router.callback_query(RegState.gender, F.data.startswith("g_"))
async def reg_gender(callback: types.CallbackQuery, state: FSMContext):
    gender = callback.data.split("_")[1]
    await state.update_data(gender=gender)
    
    # 7 Pilihan Minat (Adult)
    minat_options = ["Kenalan", "Kencan", "Love", "Ngopi", "Flirting", "DirtyTalk", "FWB"]
    kb = [[types.InlineKeyboardButton(text=m, callback_data=f"i_{m}")] for m in minat_options]
    
    await callback.message.edit_text("Apa minatmu saat ini?", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))
    await state.set_state(RegState.interest)

@router.callback_query(RegState.interest, F.data.startswith("i_"))
async def reg_interest(callback: types.CallbackQuery, state: FSMContext):
    interest = callback.data.split("_")[1]
    await state.update_data(interest=interest)
    await callback.message.answer("Kamu sedang tertarik mencari siapa/kriteria seperti apa?")
    await state.set_state(RegState.looking_for)

@router.message(RegState.looking_for)
async def reg_looking(message: types.Message, state: FSMContext):
    await state.update_data(looking_for=message.text)
    await message.answer("Tuliskan sedikit tentang dirimu (About Me):")
    await state.set_state(RegState.bio)

@router.message(RegState.bio)
async def reg_bio(message: types.Message, state: FSMContext):
    await state.update_data(bio=message.text)
    await message.answer("Sekarang, kirimkan satu foto profil terbaikmu:")
    await state.set_state(RegState.photo)

@router.message(RegState.photo, F.photo)
async def reg_photo(message: types.Message, state: FSMContext):
    await state.update_data(photo_id=message.photo[-1].file_id)
    kb = [[types.KeyboardButton(text="📍 Kirim Lokasi", request_location=True)]]
    await message.answer("Terakhir, kirimkan lokasimu agar kami bisa mencocokkan profil terdekat:", 
                         reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    await state.set_state(RegState.location)

@router.message(RegState.location, F.location)
async def reg_final(message: types.Message, state: FSMContext, db: DatabaseService):
    data = await state.get_data()
    city = get_city_name(message.location.latitude, message.location.longitude)
    hashtag = create_hashtag(city)
    
    # Simpan ke Postgres
    await db.register_full_user(
        id=message.from_user.id,
        username=message.from_user.username,
        full_name=data['name'],
        age=data['age'],
        gender=data['gender'],
        interest=data['interest'],
        looking_for=data['looking_for'],
        bio=data['bio'],
        photo_id=data['photo_id'],
        location_name=city,
        city_hashtag=hashtag
    )
    
    await state.clear()
    await message.answer("✅ Registrasi Sukses!", reply_markup=types.ReplyKeyboardRemove())

    # --- LOG ADMIN KE CHANNEL ---
    LOG_CHANNEL_ID = os.getenv("LOG_CHANNEL_ID")
    admin_kb = [[
        types.InlineKeyboardButton(text="💬 Chat User", url=f"tg://user?id={message.from_user.id}"),
        types.InlineKeyboardButton(text="🚫 Ban", callback_data=f"ban_{message.from_user.id}")
    ]]
    
    log_text = (
        f"🔔 **USER BARU**\n"
        f"👤 {data['name']}, {data['age']} ({data['gender']})\n"
        f"🔥 Minat: {data['interest']}\n"
        f"🎯 Mencari: {data['looking_for']}\n"
        f"📍 Lokasi: {city}\n"
        f"📝 Bio: {data['bio']}"
    )
    await message.bot.send_photo(LOG_CHANNEL_ID, photo=data['photo_id'], caption=log_text, 
                                 reply_markup=types.InlineKeyboardMarkup(inline_keyboard=admin_kb))

    # Tampilkan Menu Utama (Nanti akan kita buat di start.py)
    from handlers.start import show_main_menu
    await show_main_menu(message)
    
