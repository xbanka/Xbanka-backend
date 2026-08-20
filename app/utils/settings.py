import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Use this to build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = os.getenv("ENV_FILE", ".env")

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

    # Mail configurations. The SMTP settings the old fastapi-mail path needed
    # (MAIL_USERNAME/PASSWORD/FROM/PORT/SERVER) are gone with it; any left over
    # in a .env file are ignored via extra="ignore" below.
    RESEND_API_KEY: str
    # Sender for every Resend-delivered email. Defaults to the address the
    # invite flow already sends from, since that domain is verified in Resend.
    RESEND_FROM: str = "Xbanka <notifications@xbankang.com>"

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
    INTERNAL_BASE_URL: str = "https://backend.xbankang.com"

    # Add this configuration
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ENV_FILE),  # Absolute path to .env
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings.model_validate({})
