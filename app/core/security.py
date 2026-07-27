#Авторизация — Этап 1: простая проверка API-ключа в заголовке

from fastapi import Header, HTTPException, status

from app.core.config import settings


async def verify_api_key(x_api_key: str = Header(default="")) -> None:
    if not settings.api_key:
        #Ключ не настроен — авторизация отключена (для локальной разработки)
        return
    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный или отсутствующий API-ключ",
        )
