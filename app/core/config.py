from pydantic_settings import BaseSettings 
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # R2_ACCOUNT_ID: str
    # R2_ACCESS_KEY_ID: str
    # R2_SECRET_ACCESS_KEY: str
    # R2_BUCKET_NAME: str
    # R2_PUBLIC_URL: str  # base public URL for constructing file URLs

    CLOUDINARY_CLOUD_NAME: str
    CLOUDINARY_API_KEY: str
    CLOUDINARY_API_SECRET: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra="ignore"


settings = Settings()
