from sqlalchemy.ext.asyncio import create_async_engine
from database.conf import environments_settings


engine = create_async_engine(
    url=environments_settings._load_env_vars().get('POSTGRES_URL'),
)
