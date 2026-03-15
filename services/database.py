from sqlalchemy import BigInteger, Column, String, Integer, Boolean, DateTime, func, ForeignKey
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.future import select
from datetime import datetime
import ssl

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(BigInteger, primary_key=True)
    username = Column(String, nullable=True)
    full_name = Column(String)
    age = Column(Integer)
    gender = Column(String)
    interest = Column(String)    # Kenalan, Kencan, Love, Ngopi, Flirting, DirtyTalk, FWB
    looking_for = Column(String) # Kriteria yang dicari
    bio = Column(String)
    location_name = Column(String) 
    city_hashtag = Column(String)
    photo_id = Column(String)
    
    # Status & Moderasi
    status = Column(String, default='active') # active, banned
    is_premium = Column(Boolean, default=False)
    
    # Kuota Harian (Reset setiap hari)
    text_posts_today = Column(Integer, default=0)
    photo_posts_today = Column(Integer, default=0)
    messages_sent_today = Column(Integer, default=0)
    profiles_opened_today = Column(Integer, default=0) # Untuk fitur "Siapa menyukai saya"
    last_reset = Column(DateTime, default=datetime.utcnow)

class Like(Base):
    __tablename__ = 'likes'
    id = Column(Integer, primary_key=True)
    sender_id = Column(BigInteger, ForeignKey('users.id'))
    receiver_id = Column(BigInteger, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.utcnow)

class DatabaseService:
    def __init__(self, db_url):
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        
        self.engine = create_async_engine(
            db_url,
            pool_pre_ping=True,
            connect_args={"ssl": "require"} if "localhost" not in db_url else {}
        )
        self.async_session = sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )

    async def init_db(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def get_user(self, user_id: int):
        async with self.async_session() as session:
            user = await session.get(User, user_id)
            if user:
                # Logika Reset Kuota Harian jika sudah ganti hari
                now = datetime.utcnow()
                if user.last_reset.date() < now.date():
                    user.text_posts_today = 0
                    user.photo_posts_today = 0
                    user.messages_sent_today = 0
                    user.profiles_opened_today = 0
                    user.last_reset = now
                    await session.commit()
            return user

    async def register_full_user(self, **kwargs):
        async with self.async_session() as session:
            user = User(**kwargs)
            await session.merge(user)
            await session.commit()
            return user

    async def add_like(self, sender_id: int, receiver_id: int):
        async with self.async_session() as session:
            new_like = Like(sender_id=sender_id, receiver_id=receiver_id)
            session.add(new_like)
            await session.commit()

    async def get_my_likes(self, user_id: int):
        async with self.async_session() as session:
            result = await session.execute(select(Like).where(Like.receiver_id == user_id))
            return result.scalars().all()

    async def increment_quota(self, user_id: int, quota_type: str):
        async with self.async_session() as session:
            user = await session.get(User, user_id)
            if user:
                if quota_type == "text_post": user.text_posts_today += 1
                elif quota_type == "photo_post": user.photo_posts_today += 1
                elif quota_type == "message": user.messages_sent_today += 1
                elif quota_type == "view_profile": user.profiles_opened_today += 1
                await session.commit()

    async def get_potential_match(self, user_id: int, my_gender: str):
        # Cari lawan jenis yang aktif dan bukan diri sendiri
        target_gender = "Wanita" if my_gender == "Pria" else "Pria"
        async with self.async_session() as session:
            query = select(User).where(
                User.id != user_id, 
                User.gender == target_gender,
                User.status == 'active'
            ).order_by(func.random()).limit(1)
            result = await session.execute(query)
            return result.scalar_one_or_none()
        
