from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from database.handlers.utils.engine import engine


PostgresAsyncSession = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)
