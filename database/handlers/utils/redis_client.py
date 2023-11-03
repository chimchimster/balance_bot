import redis

from database.conf import environments_settings

redis_client = redis.Redis(
    host=environments_settings._load_env_vars().get('REDIS_HOST'),
    port=environments_settings._load_env_vars().get('REDIS_PORT'),
    decode_responses=True,
)
