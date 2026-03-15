import os
import logging
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from services.database import DatabaseService
from utils.geocoder import get_city_name, create_hashtag

router = Router()
logger = logging.getLogger(__name__)

# Daftar Minat untuk Multi-Select
INTEREST_OPTIONS = ["Musik", "Olahraga", "Travel", "Kuliner", "Game", "Film", "Adult"]

class RegState(StatesGroup):
    name = State()
    age = State()
    gender = State()
    interest = State()    
    looking_for = State() 
    bio = State()
    location = State()
    photo = State()

# --- 1. START & TOS ---
@router.callback_query(F.data == "start_register")
async def start_reg_tos(callback: types.CallbackQuery, state: FSMContext):
    await state.clear() # Reset state lama jika ada
    text = (
        "⚠️ **ATURAN KOMUNITAS PICKME**\n\n"
        "1. Minimal usia 18 tahun.\n"
        "2. Dilarang spam, scam, atau promosi judi/obat terlarang.\n"
        "3. Gunakan foto asli dan sopan.\n"
        "4. Hormati privasi sesama pengguna.\n\n"
        "Penyalahgunaan akun akan berakibat BANNED permanen.\n"
        "Apakah kamu setuju dan ingin lanjut?"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Setuju & Daftar", callback_data="tos_agree")],
        [InlineKeyboardButton(text="❌ Batalkan", callback_data="main_menu")]
    ])
    await callback.message.edit_text(text, reply_markup=kb)

@router.callback_query(F.data == "tos_agree")
async def start_name(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Senang mendengarnya! 😊\n\nSiapa **nama panggilan** kamu?")
    await state.set_state(RegState.name)

# --- 2. NAME & AGE ---
@router.message(RegState.name)
async def process_name(message: types.Message, state: FSMContext):
    if len(message.text) < 2 or len(message.text) > 20:
        return await message.answer("Nama terlalu pendek/panjang. Gunakan 2-20 karakter ya.")
    
    await state.update_data(name=message.text)
    await message.answer(f"Halo {message.text}! Berapa **usia** kamu sekarang?\n\n(Kirim dalam bentuk angka, misal: 22)")
    await state.set_state(RegState.age)

@router.message(RegState.age)
async def process_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("Tolong kirimkan angka saja ya, Kak.")
    
    age = int(message.text)
    if age < 18:
        return await message.answer("Maaf, PickMe hanya untuk pengguna berusia 18 tahun ke atas.")
    if age > 70:
        return await message.answer("Wah, serius? Tolong masukkan usia yang valid ya.")

    await state.update_data(age=age)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👨 Pria", callback_data="gender_pria"),
         InlineKeyboardButton(text="👩 Wanita", callback_data="gender_wanita")]
    ])
    await message.answer("Apa jenis kelamin kamu?", reply_markup=kb)
    await state.set_state(RegState.gender)

# --- 3. GENDER & INTEREST (MULTI-SELECT) ---
@router.callback_query(RegState.gender)
async def process_gender(callback: types.CallbackQuery, state: FSMContext):
    gender = "pria" if "pria" in callback.data else "wanita"
    await state.update_data(gender=gender, selected_interests=[])
    
    await show_interest_kb(callback.message, [])
    await state.set_state(RegState.interest)

async def show_interest_kb(message: types.Message, selected_list: list):
    buttons = []
    for opt in INTEREST_OPTIONS:
        status = "✅ " if opt in selected_list else ""
        buttons.append([InlineKeyboardButton(text=f"{status}{opt}", callback_data=f"opt_{opt}")])
    
    buttons.append([InlineKeyboardButton(text="➡️ SELESAI", callback_data="done_interest")])
    
    text = (
        "🎨 **Pilih Minat & Hobi**\n\n"
        "Kamu bisa memilih lebih dari satu. Klik lagi untuk membatalkan.\n"
        "Tekan **SELESAI** jika sudah cukup."
    )
    # Gunakan edit_text agar tombol terupdate di tempat
    try:
        await message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except:
        await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

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
        await show_interest_kb(callback.message, selected)
        
    elif callback.data == "done_interest":
        if not selected:
            return await callback.answer("Pilih minimal satu minat kamu!", show_alert=True)
        
        await state.update_data(interest=", ".join(selected))
        
        # --- 4. CRITERIA (LOOKING FOR) ---
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👨 Pria", callback_data="look_pria")],
            [InlineKeyboardButton(text="👩 Wanita", callback_data="look_wanita")],
            [InlineKeyboardButton(text="🌈 Keduanya", callback_data="look_keduanya")]
        ])
        await callback.message.edit_text("Kamu sedang mencari siapa di aplikasi ini?", reply_markup=kb)
        await state.set_state(RegState.looking_for)

@router.callback_query(RegState.looking_for)
async def process_looking_for(callback: types.CallbackQuery, state: FSMContext):
    choice = callback.data.replace("look_", "")
    await state.update_data(looking_for=choice)
    await callback.message.edit_text("Tulis **Bio** singkat tentang dirimu (misal: hobi, pekerjaan, atau tipe pasangan ideal):")
    await state.set_state(RegState.bio)

# --- 5. BIO & LOCATION ---
@router.message(RegState.bio)
async def process_bio(message: types.Message, state: FSMContext):
    if len(message.text) < 10:
        return await message.answer("Bio terlalu singkat, Kak. Tambahkan sedikit lagi ya (min. 10 karakter).")
    
    await state.update_data(bio=message.text)
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📍 Bagikan Lokasi", request_location=True)]
    ], resize_keyboard=True, one_time_keyboard=True)
    
    await message.answer("Terakhir, PickMe butuh lokasi kamu untuk mencari orang terdekat:", reply_markup=kb)
    await state.set_state(RegState.location)

@router.message(RegState.location, F.location)
async def process_location(message: types.Message, state: FSMContext):
    lat = message.location.latitude
    lon = message.location.longitude
    
    # Geocoding Logic
    city_name = get_city_name(lat, lon)
    city_tag = create_hashtag(city_name)
    
    await state.update_data(lat=lat, lon=lon, loc_name=city_name, city_tag=city_tag)
    await message.answer(
        f"Lokasi terdeteksi: **{city_name}**\n\nSekarang, kirimkan **Foto Profil** terbaikmu:", 
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(RegState.photo)

# --- 6. PHOTO & DATABASE SAVING ---
@router.message(RegState.photo, F.photo)
async def process_photo_final(message: types.Message, state: FSMContext, db: DatabaseService):
    photo_id = message.photo[-1].file_id
    data = await state.get_data()
    
    try:
        # Simpan ke Postgres
        await db.register_full_user(
            user_id=message.from_user.id,
            full_name=data['name'],
            gender=data['gender'],
            age=int(data['age']),
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

        # PREVIEW PROFIL (FITUR YANG KAMU MINTA)
        preview_text = (
            "✅ **PENDAFTARAN BERHASIL!**\n\n"
            "Profil kamu sekarang aktif dan dapat dilihat orang lain:\n"
            "━━━━━━━━━━━━━━━\n"
            f"👤 **{data['name']}, {data['age']}**\n"
            f"📍 {data['loc_name']}\n"
            f"🔍 Mencari: {data['looking_for'].capitalize()}\n"
            f"🎨 Minat: {data['interest']}\n\n"
            f"📝 **Bio:**\n{data['bio']}\n"
            "━━━━━━━━━━━━━━━\n"
        )
        
        await message.answer_photo(photo=photo_id, caption=preview_text)
        
        # Panggil Menu Utama
        from handlers.start import show_main_menu
        await show_main_menu(message)
        
    except Exception as e:
        logger.error(f"Error saat registrasi: {e}")
        await message.answer("❌ Terjadi kesalahan saat menyimpan data. Silakan coba /start lagi.")

# Fallback jika user mengirim teks saat bot minta lokasi/foto
@router.message(RegState.location)
async def location_fallback(message: types.Message):
    await message.answer("Tolong klik tombol **📍 Bagikan Lokasi** di bawah ya.")

@router.message(RegState.photo)
async def photo_fallback(message: types.Message):
    await message.answer("Tolong kirimkan **Foto**, bukan teks ya Kak.")
    
