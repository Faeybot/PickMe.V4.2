from sqlalchemy import BigInteger, Column, String, Integer, Boolean, DateTime, Float, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.future import select
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(BigInteger, primary_key=True)
    username = Column(String, nullable=True)
    full_name = Column(String)
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)    # Pria / Wanita
    interest = Column(String, nullable=True)  # Pria / Wanita / Keduanya
    location_name = Column(String, nullable=True) 
    city_hashtag = Column(String, nullable=True)
    photo_id = Column(String, nullable=True)
    
    # Moderasi & Status
    report_count = Column(Integer, default=0)
    status = Column(String, default='active') # active, warn, swipe_ban, total_ban
    is_premium = Column(Boolean, default=False)
    
    # Kuota Harian
    text_posts_today = Column(Integer, default=0)
    photo_posts_today = Column(Integer, default=0)
    last_reset = Column(DateTime, default=datetime.utcnow)

class DatabaseService:
    def __init__(self, db_url):
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        self.engine = create_async_engine(db_url, echo=False)
        self.async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    async def init_db(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def get_user(self, user_id: int):
        async with self.async_session() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            return result.scalar_one_or_none()

    async def register_full_user(self, user_id, **kwargs):
        async with self.async_session() as session:
            user = await self.get_user(user_id)
            if not user:
                user = User(id=user_id, **kwargs)
                session.add(user)
            else:
                for key, value in kwargs.items():
                    setattr(user, key, value)
            await session.commit()
            return user

    # LOGIKA KUOTA
    async def increment_quota(self, user_id: int, post_type: str):
        async with self.async_session() as session:
            user = await self.get_user(user_id)
            if user:
                if post_type == "text":
                    user.text_posts_today += 1
                else:
                    user.photo_posts_today += 1
                await session.commit()

    # LOGIKA MODERASI (3, 10, 15 Laporan)
    async def add_report(self, user_id: int):
        async with self.async_session() as session:
            user = await self.get_user(user_id)
            if user:
                user.report_count += 1
                if user.report_count >= 15:
                    user.status = 'total_ban'
                elif user.report_count >= 10:
                    user.status = 'swipe_ban'
                elif user.report_count >= 3:
                    user.status = 'warn'
                await session.commit()
                return user.status
            return None

    # LOGIKA SWIPE DATING
    async def get_potential_match(self, user_id: int, interest: str):
        async with self.async_session() as session:
            # Cari user yang gendernya sesuai interest kita, dan bukan diri sendiri
            query = select(User).where(
                User.id != user_id,
                User.status == 'active'
            )
            
            if interest != "Keduanya":
                query = query.where(User.gender == interest)
            
            # Ambil satu secara acak (Random)
            result = await session.execute(query.order_by(func.random()).limit(1))
            return result.scalar_one_or_none()
  
