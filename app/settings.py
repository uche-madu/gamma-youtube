# app/config.py

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    
    GROQ_API_KEY: SecretStr = Field(..., alias='GROQ_API_KEY')
    SERPAPI_API_KEY: SecretStr = Field(..., alias='SERPAPI_API_KEY')
    TOGETHER_API_KEY: SecretStr = Field(..., alias='TOGETHER_API_KEY')
    GOOGLE_API_KEY: SecretStr
    
    WEBSHARE_PROXY_USERNAME: SecretStr = Field(..., alias='WEBSHARE_PROXY_USERNAME')
    WEBSHARE_PROXY_PASSWORD: SecretStr = Field(..., alias='WEBSHARE_PROXY_PASSWORD')

    MODEL_NAME: str = Field(..., alias='MODEL_NAME')


    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow",
        env_file_encoding="utf-8",
    )

settings = Settings() # type: ignore
