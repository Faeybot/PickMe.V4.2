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
    photo = State()
    location = State()

@router.callback_query(F.data == "start_register")
async def start_reg(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Siapa nama panggilanmu? (Maksimal 15 karakter)")
    await state.set_state(RegState.name)

@router.message(RegState.name)
async def reg_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text[:15])
    await message.answer("Berapa usiamu? (Ketik angka saja, contoh: 20)")
    await state.set_state(RegState.age)

@router.message(RegState.age)
async def reg_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("Tolong masukkan angka saja ya!")
    
    await state.update_data(age=int(message.text))
    
    kb = [
        [types.InlineKeyboardButton(text="Pria 👨", callback_data="g_Pria"),
         types.InlineKeyboardButton(text="Wanita 👩", callback_data="g_Wanita")]
    ]
    await message.answer("Apa jenis kelaminmu?", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))
    await state.set_state(RegState.gender)

@router.callback_query(RegState.gender, F.data.startswith("g_"))
async def reg_gender(callback: types.CallbackQuery, state: FSMContext):
    gender = callback.data.split("_")[1]
    await state.update_data(gender=gender)
    
    kb = [
        [types.InlineKeyboardButton(text="Cari Pria", callback_data="i_Pria"),
         types.InlineKeyboardButton(text="Cari Wanita", callback_data="i_Wanita")],
        [types.InlineKeyboardButton(text="Cari Keduanya", callback_data="i_Keduanya")]
    ]
    await callback.message.edit_text("Siapa yang ingin kamu cari?", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))
    await state.set_state(RegState.interest)

@router.callback_query(RegState.interest, F.data.startswith("i_"))
async def reg_interest(callback: types.CallbackQuery, state: FSMContext):
    interest = callback.data.split("_")[1]
    await state.update_data(interest=interest)
    await callback.message.answer("Sekarang kirimkan foto profil terbaikmu! (Pastikan wajah terlihat)")
    await state.set_state(RegState.photo)

@router.message(RegState.photo, F.photo)
async def reg_photo(message: types.Message, state: FSMContext):
    await state.update_data(photo_id=message.photo[-1].file_id)
    
    kb = [[types.KeyboardButton(text="📍 Kirim Lokasi", request_location=True)]]
    markup = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, one_time_keyboard=True)
    
    await message.answer("Terakhir, bagikan lokasimu agar kami bisa mencarikan orang terdekat!", reply_markup=markup)
    await state.set_state(RegState.location)

@router.message(RegState.location, F.location)
async def reg_final(message: types.Message, state: FSMContext, db: DatabaseService):
    data = await state.get_data()
    
    # Proses Geocoding Lokasi
    city = get_city_name(message.location.latitude, message.location.longitude)
    hashtag = create_hashtag(city)
    
    # SIMPAN KE DATABASE
    await db.register_full_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=data['name'],
        age=data['age'],
        gender=data['gender'],
        interest=data['interest'],
        photo_id=data['photo_id'],
        location_name=city,
        city_hashtag=hashtag
    )
    
    await state.clear()
    
    # Notifikasi Berhasil ke User (Tanpa tombol keyboard reply)
    await message.answer("✅ Pendaftaran Selesai!", reply_markup=types.ReplyKeyboardRemove())
    
    preview_text = (
        f"✨ **Profil Kamu Telah Aktif!**\n\n"
        f"👤 Nama: {data['name']}, {data['age']}\n"
        f"🚻 Gender: {data['gender']}\n"
        f"📍 Lokasi: {city}\n"
        f"{hashtag}"
    )
    await message.answer_photo(photo=data['photo_id'], caption=preview_text)
    
    # KIRIM KE CHANNEL ADMIN (DATABASE ADMIN)
    LOG_CHANNEL_ID = os.getenv("LOG_CHANNEL_ID")
    admin_log = (
        f"🗂 **USER BARU TERDAFTAR**\n\n"
        f"ID: `{message.from_user.id}`\n"
        f"Nama: {data['name']}\n"
        f"Username: @{message.from_user.username or 'Tidak ada'}\n"
        f"Link: [Klik Chat](tg://user?id={message.from_user.id})"
    )
    await message.bot.send_message(LOG_CHANNEL_ID, admin_log)
                  
