from pathlib import Path
from pydantic_settings import BaseSettings, DotEnvSettingsSource


DEBUG = True


class PostgresSettings(DotEnvSettingsSource):
    pass


if DEBUG:
    env_file_path = Path().cwd().parent / '.env'
else:
    env_file_path = Path.cwd() / 'database' / '.env'

postgres_settings = PostgresSettings(
    settings_cls=BaseSettings,
    env_file=env_file_path,
    env_file_encoding='utf-8',
    case_sensitive=True
)
