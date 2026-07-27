#Настройки приложения. Читаются из .env через Pydantic Settings

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "LaneGateway"
    debug: bool = False

    #Авторизация (Этап 1 — простой API-key)
    api_key: str = ""

    #БД
    database_url: str = "sqlite:///./lanegateway.db"

    #Провайдеры (ключи; на будущих этапах провайдеров станет больше)
    openrouter_api_key: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
