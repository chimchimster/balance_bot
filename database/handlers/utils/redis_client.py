import aioredis

from database.conf import environments_settings


async def connect_redis_url():

    url = environments_settings._load_env_vars().get('REDIS_URL')
    return await aioredis.from_url(url)
