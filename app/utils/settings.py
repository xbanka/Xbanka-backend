from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

# Use this to build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    """ Class to hold application's config values."""

    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_EXPIRY: int = 5

    # Database configurations
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    DB_TYPE: str

    # Mail configurations
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_PORT: int
    MAIL_SERVER: str

    # Twilio configurations
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    TWILIO_PHONE_NUMBER: str

    # Add this configuration
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),  # Absolute path to .env
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings.model_validate({})
