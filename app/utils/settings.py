from pydantic_settings import BaseSettings, SettingsConfigDict
from decouple import config
from pathlib import Path


# Use this to build paths inside the project
BASE_DIR = Path(__file__).resolve().parent
print('BASE_DIR')
print(BASE_DIR)

class Settings(BaseSettings):
    """ Class to hold application's config values."""

    SECRET_KEY: str = str(config("SECRET_KEY"))
    ALGORITHM: str = "HS256"  # default value, can be overridden by env var
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_EXPIRY: int = 5

    # Database configurations
    DB_HOST: str = str(config("SECRET_KEY"))
    DB_PORT: int = 5432
    DB_USER: str = str(config("DB_USER"))
    DB_PASSWORD: str = str(config("DB_PASSWORD"))
    DB_NAME: str = str(config("DB_NAME"))
    DB_TYPE: str = str(config("DB_TYPE"))
    # Update all string configurations to use correct environment variables
    SECRET_KEY: str = str(config("SECRET_KEY"))
    ALGORITHM: str = str(config("ALGORITHM", default="HS256"))

    # Database configurations
    DB_HOST: str = str(config("DB_HOST"))
    DB_USER: str = str(config("DB_USER"))
    DB_PASSWORD: str = str(config("DB_PASSWORD"))
    DB_NAME: str = str(config("DB_NAME"))
    DB_TYPE: str = str(config("DB_TYPE"))

    # Mail configurations
    MAIL_USERNAME: str = str(config("MAIL_USERNAME"))
    MAIL_PASSWORD: str = str(config("MAIL_PASSWORD"))
    MAIL_FROM: str = str(config("MAIL_FROM"))
    MAIL_SERVER: str = str(config("MAIL_SERVER"))

    # Twilio configurations
    TWILIO_ACCOUNT_SID: str = str(config("TWILIO_ACCOUNT_SID"))
    TWILIO_AUTH_TOKEN: str = str(config("TWILIO_AUTH_TOKEN"))
    TWILIO_PHONE_NUMBER: str = str(config("TWILIO_PHONE_NUMBER"))
    MAIL_USERNAME: str = str(config("MAIL_USERNAME"))
    MAIL_PASSWORD: str = str(config("MAIL_PASSWORD"))
    MAIL_FROM: str = str(config("MAIL_FROM"))
    MAIL_PORT: int = int(config("MAIL_PORT", default=465))
    MAIL_SERVER: str = str(config("MAIL_SERVER"))

    TWILIO_ACCOUNT_SID: str = str(config("TWILIO_ACCOUNT_SID"))
    TWILIO_AUTH_TOKEN: str = str(config("TWILIO_AUTH_TOKEN"))
    TWILIO_PHONE_NUMBER: str = str(config("TWILIO_PHONE_NUMBER"))
    TWILIO_AUTH_TOKEN: str = str(config("TWILIO_AUTH_TOKEN"))
    TWILIO_PHONE_NUMBER: str = str(config("TWILIO_PHONE_NUMBER"))


settings = Settings()
