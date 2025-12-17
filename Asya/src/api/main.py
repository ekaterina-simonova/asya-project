# src/api/main.py
import os
from dotenv import load_dotenv

from fastapi import FastAPI, Request

from .middleware.logging_middleware import logging_middleware
from .routes.call_endpoints import router as call_router
from .routes.health_check import router as health_router

load_dotenv()

app = FastAPI(title="Ася Voice Assistant API")

# Логирование всех HTTP-запросов
@app.middleware("http")
async def add_logging_middleware(request: Request, call_next):
    return await logging_middleware(request, call_next)

# Подключаем роуты
app.include_router(call_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")
# Важно: websocket_router пока НЕ подключаем, чтобы не тянуть незавершённый код

@app.get("/")
async def root():
    return {"message": "ASYA Voice Assistant API is running"}