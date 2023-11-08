from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from .engine import postgres_engine

AsyncSessionLocal = sessionmaker(
    postgres_engine.engine, class_=AsyncSession, expire_on_commit=False
)
