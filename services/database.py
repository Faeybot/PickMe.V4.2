from sqlalchemy import BigInteger, Column, String, Integer, Boolean, DateTime, func
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
    gender = Column(String, nullable=True)
    interest = Column(String, nullable=True)
    location_name = Column(String, nullable=True) 
    city_hashtag = Column(String, nullable=True)
    photo_id = Column(String, nullable=True)
    report_count = Column(Integer, default=0)
    status = Column(String, default='active')
    is_premium = Column(Boolean, default=False)
    text_posts_today = Column(Integer, default=0)
    photo_posts_today = Column(Integer, default=0)
    last_reset = Column(DateTime, default=datetime.utcnow)

class DatabaseService:
    def __init__(self, db_url):
        # Perbaikan URL untuk Asyncpg
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        
        # Penanganan SSL otomatis untuk Railway
        if "sslmode" not in db_url:
            db_url += "?sslmode=prefer"

        # Engine versi stabil (Tanpa parameter yang bikin TypeError)
        self.engine = create_async_engine(db_url)
        self.async_session = sessionmaker(
            self.engine, 
            expire_on_commit=False, 
            class_=AsyncSession
        )

    async def init_db(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def get_user(self, user_id: int):
        async with self.async_session() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            return result.scalar_one_or_none()

    async def register_full_user(self, user_id, **kwargs):
        async with self.async_session() as session:
            # Menggunakan merge agar tidak bentrok saat re-register
            user = User(id=user_id, **kwargs)
            await session.merge(user)
            await session.commit()
            return user

    async def increment_quota(self, user_id: int, post_type: str):
        async with self.async_session() as session:
            user = await session.get(User, user_id)
            if user:
                if post_type == "text":
                    user.text_posts_today += 1
                else:
                    user.photo_posts_today += 1
                await session.commit()

    async def add_report(self, user_id: int):
        async with self.async_session() as session:
            user = await session.get(User, user_id)
            if user:
                user.report_count += 1
                if user.report_count >= 15: user.status = 'total_ban'
                elif user.report_count >= 10: user.status = 'swipe_ban'
                elif user.report_count >= 3: user.status = 'warn'
                await session.commit()
                return user.status
            return None

    async def get_potential_match(self, user_id: int, interest: str):
        async with self.async_session() as session:
            query = select(User).where(User.id != user_id, User.status == 'active')
            if interest != "Keduanya":
                query = query.where(User.gender == interest)
            result = await session.execute(query.order_by(func.random()).limit(1))
            return result.scalar_one_or_none()
            
