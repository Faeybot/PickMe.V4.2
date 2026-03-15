import datetime
from sqlalchemy import Column, Integer, String, BigInteger, Float, Text, Boolean, select, update, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

# --- MODEL TABEL ---

class User(Base):
    __tablename__ = 'users'
    id = Column(BigInteger, primary_key=True)
    full_name = Column(String)
    gender = Column(String)
    age = Column(Integer)
    interest = Column(String)
    looking_for = Column(String)
    bio = Column(Text)
    photo_id = Column(String)
    location_name = Column(String)
    city_hashtag = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    is_premium = Column(Boolean, default=False)
    
    # Counter Kuota Harian
    text_posts_today = Column(Integer, default=0)
    photo_posts_today = Column(Integer, default=0)
    messages_sent_today = Column(Integer, default=0)
    profiles_viewed_today = Column(Integer, default=0)
    
    status = Column(String, default='active') # active / banned
    last_reset = Column(String) # Format: YYYY-MM-DD

class Like(Base):
    __tablename__ = 'likes'
    id = Column(Integer, primary_key=True)
    from_user = Column(BigInteger)
    to_user = Column(BigInteger)
    created_at = Column(String, default=lambda: datetime.datetime.now().strftime("%Y-%m-%d"))

# --- LAYANAN DATABASE ---

class DatabaseService:
    def __init__(self, db_url: str):
        # Konversi URL untuk dukungan Asyncpg
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        
        self.engine = create_async_engine(db_url, echo=False)
        self.async_session = sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )

    async def init_db(self):
        async with self.engine.begin() as conn:
            # Membuat semua tabel yang didefinisikan di atas
            await conn.run_sync(Base.metadata.create_all)

    async def get_user(self, user_id: int):
        async with self.async_session() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            
            # Logika Auto-Reset Kuota Harian
            if user:
                today = datetime.datetime.now().strftime("%Y-%m-%d")
                if user.last_reset != today:
                    user.text_posts_today = 0
                    user.photo_posts_today = 0
                    user.messages_sent_today = 0
                    user.profiles_viewed_today = 0
                    user.last_reset = today
                    await session.commit()
            return user

    async def register_full_user(self, user_id, full_name, gender, age, interest, looking_for, bio, photo_id, lat, lon, loc_name, city_tag):
        async with self.async_session() as session:
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            user = User(
                id=user_id,
                full_name=full_name,
                gender=gender,
                age=age,
                interest=interest,
                looking_for=looking_for,
                bio=bio,
                photo_id=photo_id,
                latitude=lat,
                longitude=lon,
                location_name=loc_name,
                city_hashtag=city_tag,
                last_reset=today,
                status='active'
            )
            await session.merge(user)
            await session.commit()

    async def increment_quota(self, user_id: int, action_type: str):
        async with self.async_session() as session:
            user = await session.get(User, user_id)
            if not user: return

            if action_type == "text_post":
                user.text_posts_today += 1
            elif action_type == "photo_post":
                user.photo_posts_today += 1
            elif action_type == "message":
                user.messages_sent_today += 1
            elif action_type == "view_profile":
                user.profiles_viewed_today += 1
                
            await session.commit()

    async def add_like(self, from_id, to_id):
        async with self.async_session() as session:
            # Cek apakah sudah pernah me-like sebelumnya
            existing = await session.execute(
                select(Like).where(Like.from_user == from_id, Like.to_user == to_id)
            )
            if not existing.scalar_one_or_none():
                new_like = Like(from_user=from_id, to_user=to_id)
                session.add(new_like)
                await session.commit()
                return True
            return False

    async def get_discovery_users(self, user_id: int, gender_target: str, limit=10):
        async with self.async_session() as session:
            # Mengambil daftar user yang bukan dirinya sendiri dan statusnya aktif
            query = select(User).where(
                User.id != user_id,
                User.status == 'active'
            )
            
            # Filter Gender (Pria/Wanita). Jika 'keduanya', maka tidak difilter.
            if gender_target != 'keduanya':
                query = query.where(User.gender == gender_target)
            
            # Mengacak urutan agar discovery terasa dinamis
            query = query.order_by(func.random())
                
            result = await session.execute(query.limit(limit))
            return result.scalars().all()

    async def get_likes_count(self, user_id: int):
        async with self.async_session() as session:
            result = await session.execute(
                select(func.count(Like.id)).where(Like.to_user == user_id)
            )
            return result.scalar() or 0

    async def get_who_liked_me(self, user_id: int):
        async with self.async_session() as session:
            # Mengambil data user yang memberikan LIKE kepada user_id
            query = select(User).join(Like, User.id == Like.from_user).where(Like.to_user == user_id)
            result = await session.execute(query)
            return result.scalars().all()
    
