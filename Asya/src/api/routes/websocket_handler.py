# src/api/routes/websocket_handler.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from typing import Dict
import logging
from src.asya_core.dialog_manager import DialogManager
from src.utils.ari_client import AriClient
from src.config.asterisk_ari_config import ARI_CONFIG  # ← ваш конфиг из config/

logger = logging.getLogger(__name__)

router = APIRouter()

# Храним активные диалоги по channel_id
active_dialogs: Dict[str, DialogManager] = {}

# Инициализируем ARI-клиент один раз при старте
ari_client = AriClient(
    base_url=ARI_CONFIG["base_url"],
    username=ARI_CONFIG["username"],
    password=ARI_CONFIG["password"]
)


@router.websocket("/events")
async def ari_websocket_endpoint(websocket: WebSocket):
    """
    WebSocket-эндпоинт для получения событий от Asterisk ARI.
    Все звонки обрабатываются через этот эндпоинт.
    """
    await websocket.accept()
    logger.info("🔌 WebSocket подключён к ARI")

    try:
        while websocket.client_state == WebSocketState.CONNECTED:
            data = await websocket.receive_json()  # Получаем JSON-событие от Asterisk
            event_type = data.get("type")

            if not event_type:
                logger.warning("⚠️ Получено событие без типа: %s", data)
                continue

            # --- Логируем событие ---
            logger.info("📨 Получено событие ARI: %s", event_type)

            # --- Обработка ключевых событий ---
            if event_type == "StasisStart":
                await handle_stasis_start(data)

            elif event_type == "ChannelTalkingStarted":
                await handle_talking_started(data)

            elif event_type == "ChannelTalkingFinished":
                await handle_talking_finished(data)

            elif event_type == "ChannelHangupComplete":
                await handle_hangup_complete(data)

            else:
                # Другие события (опционально) — можно логировать или игнорировать
                logger.debug("ℹ️ Необработанное событие ARI: %s", event_type)

    except WebSocketDisconnect:
        logger.info("🛑 WebSocket отключён")
    except Exception as e:
        logger.error("❌ Ошибка в WebSocket-обработчике: %s", str(e), exc_info=True)
    finally:
        # Очистка всех диалогов, связанных с этим соединением
        for dialog in active_dialogs.values():
            await dialog.cleanup()
        active_dialogs.clear()


async def handle_stasis_start(data: dict):
    """Обработка начала звонка"""
    channel_id = data["channel"]["id"]
    caller_id = data["channel"].get("caller", {}).get("number", "unknown")
    called_id = data["channel"].get("connected", {}).get("number", "unknown")

    logger.info(f"📞 Новый звонок: {caller_id} → {called_id} (ID: {channel_id})")

    # Создаём новый диалог
    dialog = DialogManager(
        channel_id=channel_id,
        caller_number=caller_id,
        ari_client=ari_client
    )

    # Сохраняем диалог
    active_dialogs[channel_id] = dialog

    # Запускаем основной цикл диалога
    asyncio.create_task(dialog.start())


async def handle_talking_started(data: dict):
    """Клиент начал говорить — останавливаем паузу, если была"""
    channel_id = data["channel"]["id"]
    if channel_id in active_dialogs:
        dialog = active_dialogs[channel_id]
        dialog.on_talking_started()


async def handle_talking_finished(data: dict):
    """Клиент закончил говорить — начинаем обработку речи"""
    channel_id = data["channel"]["id"]
    if channel_id in active_dialogs:
        dialog = active_dialogs[channel_id]
        dialog.on_talking_finished()


async def handle_hangup_complete(data: dict):
    """Звонок завершён — очищаем ресурсы"""
    channel_id = data["channel"]["id"]
    if channel_id in active_dialogs:
        dialog = active_dialogs.pop(channel_id)
        await dialog.cleanup()
        logger.info(f"🗑️ Диалог завершён: {channel_id}")