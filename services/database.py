import datetime
from sqlalchemy import Column, Integer, String, BigInteger, Float, Text, Boolean, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

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
    text_posts_today = Column(Integer, default=0)
    photo_posts_today = Column(Integer, default=0)
    messages_sent_today = Column(Integer, default=0)
    profiles_viewed_today = Column(Integer, default=0)
    status = Column(String, default='active')
    last_reset = Column(String)

class DatabaseService:
    def __init__(self, db_url: str):
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
            user = result.scalar_one_or_none()
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
            user = User(
                id=user_id, full_name=full_name, gender=gender, age=age,
                interest=interest, looking_for=looking_for, bio=bio,
                photo_id=photo_id, latitude=lat, longitude=lon,
                location_name=loc_name, city_hashtag=city_tag,
                last_reset=datetime.datetime.now().strftime("%Y-%m-%d")
            )
            await session.merge(user)
            await session.commit()
    
