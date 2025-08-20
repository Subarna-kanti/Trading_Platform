# app/core/config.py
from typing import ClassVar
from pydantic_settings import BaseSettings
from fastapi.security import OAuth2PasswordBearer


class Settings(BaseSettings):
    SECRET_KEY: ClassVar[str] = (
        "8fc693866aaeb82412dd02ed9a99dd9abe676acc77edbac0288d492326059883e76f22b1c7bcfeac4da55dddeae03fa28965ead7fcdd06f3ede0974688309d17"
    )
    ALGORITHM: ClassVar[str] = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: ClassVar[int] = 60
    REFRESH_TOKEN_EXPIRE_DAYS: ClassVar[int] = 7
    oauth2_scheme: ClassVar[OAuth2PasswordBearer] = OAuth2PasswordBearer(
        tokenUrl="/auth/login"
    )

    class Config:
        env_file = ".env"


settings = Settings()
