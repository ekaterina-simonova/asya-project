# src/api/routes/health_check.py
"""
Endpoints для проверки здоровья сервиса и его компонентов.
"""

from fastapi import APIRouter, Depends
from typing import Dict, Any
from datetime import datetime

from src.utils.ari_client import AriClient
from src.database.db_manager import DatabaseManager
from src.utils.logger import get_logger

router = APIRouter(tags=["health"])
logger = get_logger(__name__)


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Базовая проверка здоровья API.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "asya-voice-assistant",
        "version": "1.0.0",
    }


@router.get("/health/full")
async def full_health_check(
    ari_client: AriClient = Depends(AriClient),
    db_manager: DatabaseManager = Depends(DatabaseManager),
) -> Dict[str, Any]:
    """
    Полная проверка здоровья всех компонентов системы.
    """
    health_status: Dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "api": "healthy",
        "database": "unknown",
        "asterisk_ari": "unknown",
        "details": {},
    }

    # База данных
    try:
        db_connected = await db_manager.check_connection()
        health_status["database"] = "healthy" if db_connected else "unhealthy"
        health_status["details"]["database"] = {
            "connected": db_connected,
            "checked_at": datetime.now().isoformat(),
        }
    except Exception as e:
        health_status["database"] = "unhealthy"
        health_status["details"]["database"] = {
            "error": str(e),
            "connected": False,
        }

    # ARI
    try:
        ari_connected = await ari_client.check_connection()
        health_status["asterisk_ari"] = "healthy" if ari_connected else "unhealthy"
        health_status["details"]["asterisk_ari"] = {
            "connected": ari_connected,
            "checked_at": datetime.now().isoformat(),
        }
    except Exception as e:
        health_status["asterisk_ari"] = "unhealthy"
        health_status["details"]["asterisk_ari"] = {
            "error": str(e),
            "connected": False,
        }

    all_healthy = (
        health_status["database"] == "healthy"
        and health_status["asterisk_ari"] == "healthy"
    )
    health_status["status"] = "healthy" if all_healthy else "degraded"

    return health_status
