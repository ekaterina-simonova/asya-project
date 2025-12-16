#это файл с endpoints для проверки здоровья сервиса и его компонентов
from fastapi import APIRouter, Depends
from typing import Dict, Any
import logging
from datetime import datetime

from utils.ari_client import AriClient
from database.db_manager import DatabaseManager
from utils.logger import get_logger

# Инициализация роутера и логгера
router = APIRouter(tags=["health"])
logger = get_logger(__name__)

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Базовая проверка здоровья API
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "asya-voice-assistant",
        "version": "1.0.0"
    }

@router.get("/health/full")
async def full_health_check(
    ari_client: AriClient = Depends(AriClient),
    db_manager: DatabaseManager = Depends(DatabaseManager)
) -> Dict[str, Any]:
    """
    Полная проверка здоровья всех компонентов системы
    """
    health_status = {
        "timestamp": datetime.now().isoformat(),
        "api": "healthy",
        "database": "unknown",
        "asterisk_ari": "unknown",
        "details": {}
    }

    try:
        # Проверка подключения к базе данных
        db_connected = await db_manager.check_connection()
        health_status["database"] = "healthy" if db_connected else "unhealthy"
        health_status["details"]["database"] = {
            "connected": db_connected,
            "connection_time": datetime.now().isoformat()
        }
    except Exception as e:
        health_status["database"] = "unhealthy"
        health_status["details"]["database"] = {
            "error": str(e),
            "connected": False
        }

    try:
        # Проверка подключения к Asterisk ARI
        ari_connected = await ari_client.check_connection()
        health_status["asterisk_ari"] = "healthy" if ari_connected else "unhealthy"
        health_status["details"]["asterisk_ari"] = {
            "connected": ari_connected,
            "connection_time": datetime.now().isoformat()
        }
    except Exception as e:
        health_status["asterisk_ari"] = "unhealthy"
        health_status["details"]["asterisk_ari"] = {
            "error": str(e),
            "connected": False
        }

    # Общий статус системы
    all_healthy = all([
        health_status["database"] == "healthy",
        health_status["asterisk_ari"] == "healthy"
    ])
    
    health_status["status"] = "healthy" if all_healthy else "degraded"
    
    return health_status

@router.get("/health/ready")
async def readiness_probe() -> Dict[str, Any]:
    """
    Проверка готовности сервиса к работе
    """
    return {
        "status": "ready",
        "timestamp": datetime.now().isoformat()
    }

@router.get("/health/live")
async def liveness_probe() -> Dict[str, Any]:
    """
    Проверка живости сервиса (для Kubernetes liveness probe)
    """
    return {
        "status": "alive",
        "timestamp": datetime.now().isoformat()
    }

@router.get("/health/version")
async def version_info() -> Dict[str, Any]:
    """
    Информация о версиях компонентов
    """
    return {
        "api_version": "1.0.0",
        "python_version": "3.9+",
        "fastapi_version": "0.68.0+",
        "asterisk_ari_version": "8.0+",
        "timestamp": datetime.now().isoformat()
    }