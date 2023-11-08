from pathlib import Path
from pydantic_settings import BaseSettings, DotEnvSettingsSource


DEBUG = False


class EnvironmentsSettings(DotEnvSettingsSource):
    pass


if not DEBUG:
    env_file_path = Path('/home/newuser/balance_tg/balance_bot/database/.env') # ABS
else:
    env_file_path = Path.cwd() / '.env'

environments_settings = EnvironmentsSettings(
    settings_cls=BaseSettings,
    env_file=env_file_path,
    env_file_encoding='utf-8',
    case_sensitive=True
)
