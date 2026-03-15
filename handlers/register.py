import os
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from services.database import DatabaseService
from utils.geocoder import get_city_name, create_hashtag

router = Router()

# Daftar Minat untuk Multi-Select
INTEREST_OPTIONS = ["Musik", "Olahraga", "Travel", "Kuliner", "Game", "Film", "Adult"]

class RegState(StatesGroup):
    name = State()
    age = State()
    gender = State()
    interest = State()    # Multi-pilih minat
    looking_for = State() # Mencari Pria/Wanita/Keduanya
    bio = State()
    location = State()
    photo = State()

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
async def start_name(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Bagus! Siapa nama panggilanmu?")
    await state.set_state(RegState.name)

@router.message(RegState.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer(f"Salam kenal, {message.text}! Berapa usiamu? (Hanya angka)")
    await state.set_state(RegState.age)

@router.message(RegState.age)
async def process_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("Tolong masukkan angka saja ya.")
    
    age = int(message.text)
    if age < 18:
        return await message.answer("Maaf, kamu harus berusia minimal 18 tahun.")
    
    await state.update_data(age=age)
    kb = [
        [types.InlineKeyboardButton(text="👨 Pria", callback_data="gender_pria")],
        [types.InlineKeyboardButton(text="👩 Wanita", callback_data="gender_wanita")]
    ]
    await message.answer("Apa jenis kelaminmu?", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))
    await state.set_state(RegState.gender)

@router.callback_query(RegState.gender)
async def process_gender(callback: types.CallbackQuery, state: FSMContext):
    gender = "pria" if "pria" in callback.data else "wanita"
    await state.update_data(gender=gender)
    await state.update_data(selected_interests=[]) # Inisialisasi list minat
    
    # Tampilkan Menu Minat (Multi-Select)
    await show_interest_keyboard(callback.message, [])
    await state.set_state(RegState.interest)

async def show_interest_keyboard(message: types.Message, selected_list: list):
    buttons = []
    for opt in INTEREST_OPTIONS:
        text = f"✅ {opt}" if opt in selected_list else opt
        buttons.append([types.InlineKeyboardButton(text=text, callback_data=f"opt_{opt}")])
    
    buttons.append([types.InlineKeyboardButton(text="➡️ SELESAI", callback_data="done_interest")])
    text = "Pilih satu atau beberapa minatmu, lalu tekan Selesai:"
    
    await message.edit_text(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(RegState.interest)
async def process_interest_selection(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("selected_interests", [])
    
    if callback.data.startswith("opt_"):
        choice = callback.data.replace("opt_", "")
        if choice in selected:
            selected.remove(choice)
        else:
            selected.append(choice)
        
        await state.update_data(selected_interests=selected)
        await show_interest_keyboard(callback.message, selected)
        
    elif callback.data == "done_interest":
        if not selected:
            return await callback.answer("Pilih minimal satu minat!", show_alert=True)
        
        await state.update_data(interest=", ".join(selected))
        
        # Pindah ke Kriteria Pencarian (UPDATE: Pria/Wanita/Keduanya)
        kb = [
            [types.InlineKeyboardButton(text="👨 Pria", callback_data="look_pria")],
            [types.InlineKeyboardButton(text="👩 Wanita", callback_data="look_wanita")],
            [types.InlineKeyboardButton(text="🌈 Keduanya", callback_data="look_keduanya")]
        ]
        await callback.message.edit_text("Kamu sedang mencari siapa?", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))
        await state.set_state(RegState.looking_for)

@router.callback_query(RegState.looking_for)
async def process_looking_for(callback: types.CallbackQuery, state: FSMContext):
    choice = callback.data.replace("look_", "")
    await state.update_data(looking_for=choice)
    await callback.message.edit_text("Tuliskan bio singkat tentang dirimu (hobi, kriteria, atau sapaan):")
    await state.set_state(RegState.bio)

@router.message(RegState.bio)
async def process_bio(message: types.Message, state: FSMContext):
    await state.update_data(bio=message.text)
    kb = [[types.KeyboardButton(text="📍 Kirim Lokasi", request_location=True)]]
    await message.answer("Terakhir, bagikan lokasimu agar bisa menemukan orang terdekat:", 
                         reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, one_time_keyboard=True))
    await state.set_state(RegState.location)

@router.message(RegState.location, F.location)
async def process_location(message: types.Message, state: FSMContext):
    lat = message.location.latitude
    lon = message.location.longitude
    
    # Geocoding
    city_name = get_city_name(lat, lon)
    city_tag = create_hashtag(city_name)
    
    await state.update_data(lat=lat, lon=lon, loc_name=city_name, city_tag=city_tag)
    await message.answer("Terima kasih! Sekarang kirimkan foto profil terbaikmu:", 
                         reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(RegState.photo)

@router.message(RegState.photo, F.photo)
async def process_photo_final(message: types.Message, state: FSMContext, db: DatabaseService):
    photo_id = message.photo[-1].file_id
    data = await state.get_data()
    
    # Simpan ke Database (Pastikan db.register_full_user sudah mendukung parameter baru)
    await db.register_full_user(
        user_id=message.from_user.id,
        full_name=data['name'],
        gender=data['gender'],
        age=data['age'],
        interest=data['interest'],
        looking_for=data['looking_for'],
        bio=data['bio'],
        photo_id=photo_id,
        lat=data['lat'],
        lon=data['lon'],
        loc_name=data['loc_name'],
        city_tag=data['city_tag']
    )
    
    await state.clear()
    
    # --- PREVIEW PROFIL PRIBADI (Fitur yang dikembalikan) ---
    preview_text = (
        "✅ **PENDAFTARAN BERHASIL!**\n\n"
        "Berikut adalah tampilan profilmu:\n"
        "━━━━━━━━━━━━━━━\n"
        f"👤 **{data['name']}, {data['age']}**\n"
        f"📍 {data['loc_name']}\n"
        f"🔍 Mencari: {data['looking_for'].capitalize()}\n"
        f"🎨 Minat: {data['interest']}\n\n"
        f"📝 **Bio:**\n{data['bio']}\n"
        "━━━━━━━━━━━━━━━\n"
    )
    
    await message.answer_photo(photo=photo_id, caption=preview_text)
    
    # Munculkan Menu Utama
    from handlers.start import show_main_menu
    await show_main_menu(message)
