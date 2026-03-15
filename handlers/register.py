from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from services.database import DatabaseService
from utils.geocoder import get_city_name, create_hashtag

router = Router()
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

@router.callback_query(F.data == "start_register")
async def start_reg_tos(callback: types.CallbackQuery, state: FSMContext):
    text = "⚠️ **Aturan Komunitas**\n\n1. Minimal 18 tahun.\n2. Dilarang spam/scam.\n3. Sopan.\n\nSetuju?"
    kb = [[types.InlineKeyboardButton(text="✅ Setuju", callback_data="tos_agree")]]
    await callback.message.edit_text(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data == "tos_agree")
async def start_name(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Siapa nama panggilanmu?")
    await state.set_state(RegState.name)

@router.message(RegState.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer(f"Halo {message.text}! Berapa usiamu? (Angka)")
    await state.set_state(RegState.age)

@router.message(RegState.age)
async def process_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit(): return await message.answer("Masukkan angka!")
    await state.update_data(age=int(message.text))
    kb = [[types.InlineKeyboardButton(text="👨 Pria", callback_data="g_pria"),
           types.InlineKeyboardButton(text="👩 Wanita", callback_data="g_wanita")]]
    await message.answer("Jenis kelaminmu?", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))
    await state.set_state(RegState.gender)

@router.callback_query(RegState.gender)
async def process_gender(callback: types.CallbackQuery, state: FSMContext):
    gender = "pria" if "pria" in callback.data else "wanita"
    await state.update_data(gender=gender, selected_interests=[])
    await show_interest_kb(callback.message, [])
    await state.set_state(RegState.interest)

async def show_interest_kb(message: types.Message, selected: list):
    btns = [[types.InlineKeyboardButton(text=f"{'✅ ' if i in selected else ''}{i}", callback_data=f"opt_{i}")] for i in INTEREST_OPTIONS]
    btns.append([types.InlineKeyboardButton(text="➡️ SELESAI", callback_data="done_int")])
    await message.edit_text("Pilih minatmu (bisa lebih dari satu):", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=btns))

@router.callback_query(RegState.interest)
async def process_int(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("selected_interests", [])
    if callback.data.startswith("opt_"):
        choice = callback.data.replace("opt_", "")
        selected.remove(choice) if choice in selected else selected.append(choice)
        await state.update_data(selected_interests=selected)
        await show_interest_kb(callback.message, selected)
    elif callback.data == "done_int":
        if not selected: return await callback.answer("Pilih minimal satu!")
        await state.update_data(interest=", ".join(selected))
        kb = [[types.InlineKeyboardButton(text="👨 Pria", callback_data="l_pria"),
               types.InlineKeyboardButton(text="👩 Wanita", callback_data="l_wanita"),
               types.InlineKeyboardButton(text="🌈 Keduanya", callback_data="l_keduanya")]]
        await callback.message.edit_text("Kamu mencari siapa?", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))
        await state.set_state(RegState.looking_for)

@router.callback_query(RegState.looking_for)
async def process_look(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(looking_for=callback.data.replace("l_", ""))
    await callback.message.edit_text("Tulis bio singkatmu:")
    await state.set_state(RegState.bio)

@router.message(RegState.bio)
async def process_bio(message: types.Message, state: FSMContext):
    await state.update_data(bio=message.text)
    kb = [[types.KeyboardButton(text="📍 Kirim Lokasi", request_location=True)]]
    await message.answer("Kirim lokasimu:", reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    await state.set_state(RegState.location)

@router.message(RegState.location, F.location)
async def process_loc(message: types.Message, state: FSMContext):
    lat, lon = message.location.latitude, message.location.longitude
    city = get_city_name(lat, lon)
    await state.update_data(lat=lat, lon=lon, loc_name=city, city_tag=create_hashtag(city))
    await message.answer("Kirim foto profilmu:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(RegState.photo)

@router.message(RegState.photo, F.photo)
async def process_photo_final(message: types.Message, state: FSMContext, db: DatabaseService):
    photo_id = message.photo[-1].file_id
    data = await state.get_data()
    await db.register_full_user(message.from_user.id, data['name'], data['gender'], data['age'], 
                                data['interest'], data['looking_for'], data['bio'], photo_id, 
                                data['lat'], data['lon'], data['loc_name'], data['city_tag'])
    await state.clear()
    
    # PREVIEW PROFIL
    caption = (f"✅ **PENDAFTARAN BERHASIL!**\n\n👤 **{data['name']}, {data['age']}**\n📍 {data['loc_name']}\n"
               f"🔍 Mencari: {data['looking_for'].capitalize()}\n🎨 Minat: {data['interest']}\n\n📝 **Bio:**\n{data['bio']}")
    await message.answer_photo(photo=photo_id, caption=caption)
    
    from handlers.start import show_main_menu
    await show_main_menu(message)
