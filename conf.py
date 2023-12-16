import pathlib
from pydantic import SecretStr
from pydantic_settings import SettingsConfigDict, BaseSettings


class BotSettings(BaseSettings):
    bot_token: SecretStr
    payment_provider_token: SecretStr
    server_token: SecretStr
    support_username: SecretStr
    smtp_host: SecretStr
    smtp_port: SecretStr
    email_username: SecretStr
    email_password: SecretStr

    model_config = SettingsConfigDict(
        env_file=pathlib.Path.cwd() / 'balance_bot' / '.env',
        env_file_encoding='utf-8',
    )


bot_settings = BotSettings()
