import pathlib
from pydantic import SecretStr
from pydantic_settings import SettingsConfigDict, BaseSettings


class BotSettings(BaseSettings):
    bot_token: SecretStr
    payment_provider_token: SecretStr
    server_token: SecretStr
    support_username: SecretStr

    model_config = SettingsConfigDict(
        env_file=pathlib.Path('/home/newuser/balance_tg/balance_bot/.env'),
        env_file_encoding='utf-8',
    )


bot_settings = BotSettings()
