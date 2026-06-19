from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# Use this to build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Class to hold application's config values."""

    AFFILIATE_FRONTEND_URL: str
    ERP_FRONTEND_URL: str

    ENVIRONMENT: str

    TEST_EMAIL: str

    ALLOW_SUPER_ADMIN_BOOTSTRAP: bool = False

    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_EXPIRY: int = 5

    PAYSTACK_SECRET_KEY: str
    NUBAN_SECRET_KEY: str

    # Database configurations
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    DB_TYPE: str

    ALEMBIC_DATABASE_URL: str

    # Mail configurations
    MAIL_USERNAME: str
    MAIL_PASSWORD: SecretStr
    MAIL_FROM: str
    MAIL_PORT: int
    MAIL_SERVER: str

    RESEND_API_KEY: str

    S3_BUCKET_TRANSACTIONS: str
    S3_BUCKET_PAYOUTS: str

    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str

    VERIFY_TOKEN: str

    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str

    INTERNAL_KEY: str
    CORE_BACKEND_URL: str = "https://backend.xbankang.com"

    # Add this configuration
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),  # Absolute path to .env
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings.model_validate({})
