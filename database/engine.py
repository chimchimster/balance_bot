from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import create_async_engine
from .conf import environments_settings


class PostgresEngine:
    db_url = environments_settings._load_env_vars().get('POSTGRES_URL')
    engine = create_async_engine(db_url, poolclass=NullPool)


postgres_engine = PostgresEngine()
