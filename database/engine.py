from sqlalchemy.ext.asyncio import create_async_engine
from .conf import postgres_settings


engine = create_async_engine(
    url=postgres_settings._load_env_vars().get('POSTGRES_URL'),
)
