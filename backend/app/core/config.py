# settings.py
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import ClassVar
from fastapi.security import OAuth2PasswordBearer


class Settings(BaseSettings):
    # Secrets & tokens
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ALGORITHM: ClassVar[str] = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(60, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(7, env="REFRESH_TOKEN_EXPIRE_DAYS")

    # OAuth2 scheme (this can stay hardcoded)
    oauth2_scheme: ClassVar[OAuth2PasswordBearer] = OAuth2PasswordBearer(
        tokenUrl="/auth/login"
    )

    class Config:
        env_file = ".env"  # loads environment variables from .env
        env_file_encoding = "utf-8"


settings = Settings()
