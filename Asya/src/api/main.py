# src/api/main.py
import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from .middleware.logging_middleware import logging_middleware
from .routes.call_endpoints import router as call_router
from .routes.health_check import router as health_router
from .routes.websocket_handler import router as websocket_router

# Создаём приложение
app = FastAPI(title="Ася")

# Регистрируем middleware
@app.middleware("http")
async def add_logging_middleware(request: Request, call_next):
    return await logging_middleware(request, call_next)

# Подключаем роуты
app.include_router(call_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")
app.include_router(websocket_router, prefix="/ari")  # ARI использует /ari/events

@app.get("/")
async def root():
    return {"message": "ASYA Voice Assistant API is running"}

