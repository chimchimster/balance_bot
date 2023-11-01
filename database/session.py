from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import create_session

from engine import engine


PostgresAsyncSession = create_session(
    engine, class_=AsyncSession, expire_on_commit=False
)
