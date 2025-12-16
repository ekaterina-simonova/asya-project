import time
import logging
from fastapi import Request, Response
from typing import Callable

from src.utils.logger import get_logger

# Получаем логгер для middleware
logger = get_logger(__name__)


async def logging_middleware(request: Request, call_next: Callable) -> Response:
    """
    Middleware для логирования всех входящих HTTP-запросов и ответов.
    Используется в FastAPI как асинхронный middleware.
    """
    start_time = time.time()

    # Логируем входящий запрос
    client_host = request.client.host if request.client else "unknown"
    logger.info(
        f"Request: {request.method} {request.url.path} | "
        f"Client: {client_host} | "
        f"Headers: {dict(request.headers)}"
    )

    try:
        # Пропускаем запрос дальше по цепочке
        response = await call_next(request)

        # Вычисляем время обработки
        process_time = time.time() - start_time

        # Логируем успешный ответ
        logger.info(
            f"Response: {response.status_code} | "
            f"Time: {process_time:.3f}s | "
            f"Path: {request.url.path} | "
            f"Method: {request.method}"
        )

        return response

    except Exception as e:
        # Логируем ошибку
        process_time = time.time() - start_time
        logger.error(
            f"Error: {str(e)} | "
            f"Time: {process_time:.3f}s | "
            f"Path: {request.url.path} | "
            f"Method: {request.method}",
            exc_info=True  # Выводит стек вызовов
        )
        raise