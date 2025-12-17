"""
Endpoints для управления звонками через Asterisk ARI.
"""

from fastapi import APIRouter, HTTPException, Depends

from src.utils.ari_client import AriClient
from src.utils.logger import get_logger
from src.database.shemas.call_schemas import (
    CallRequest,
    CallResponse,
    HangupRequest,
)

router = APIRouter(prefix="/calls", tags=["calls"])
logger = get_logger(__name__)


def get_ari_client() -> AriClient:
    """Зависимость FastAPI: создаёт экземпляр AriClient."""
    return AriClient()


@router.post("/initiate", response_model=CallResponse)
async def initiate_call(
    call_request: CallRequest,
    ari_client: AriClient = Depends(get_ari_client),
):
    """
    Инициировать исходящий звонок.
    """
    try:
        logger.info(f"Initiating call to {call_request.destination}")

        call_id = await ari_client.originate_call(
            endpoint=call_request.destination,
            caller_id=call_request.caller_id or "Asya",
            context=call_request.context or "default",
            extension=call_request.extension or "s",
            variables=call_request.variables or {},
        )

        return CallResponse(
            success=True,
            call_id=call_id,
            message=f"Call initiated to {call_request.destination}",
        )

    except Exception as e:
        logger.error(f"Failed to initiate call: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hangup")
async def hangup_call(
    hangup_request: HangupRequest,
    ari_client: AriClient = Depends(get_ari_client),
):
    """
    Завершить активный звонок.
    """
    try:
        logger.info(f"Hanging up call: {hangup_request.call_id}")

        success = await ari_client.hangup_call(hangup_request.call_id)

        if success:
            return {"success": True, "message": "Call terminated successfully"}
        else:
            raise HTTPException(status_code=404, detail="Call not found")

    except Exception as e:
        logger.error(f"Failed to hangup call: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active")
async def get_active_calls(
    ari_client: AriClient = Depends(get_ari_client),
):
    """
    Получить список активных звонков.
    """
    try:
        active_calls = await ari_client.get_active_calls()
        return {"active_calls": active_calls}
    except Exception as e:
        logger.error(f"Failed to get active calls: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transfer")
async def transfer_call(
    call_id: str,
    target_extension: str,
    ari_client: AriClient = Depends(get_ari_client),
):
    """
    Перевести звонок на другой endpoint/extension.
    """
    try:
        success = await ari_client.transfer_call(call_id, target_extension)
        if success:
            return {"success": True, "message": "Call transferred successfully"}
        else:
            raise HTTPException(
                status_code=404,
                detail="Call not found or transfer failed",
            )
    except Exception as e:
        logger.error(f"Failed to transfer call: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/play_audio")
async def play_audio_to_call(
    call_id: str,
    audio_file: str,
    ari_client: AriClient = Depends(get_ari_client),
):
    """
    Воспроизвести аудиофайл в активном звонке.
    audio_file должен быть в формате 'sound:custom/...'.
    """
    try:
        success = await ari_client.play_audio(call_id, audio_file)
        if success:
            return {"success": True, "message": "Audio playback started"}
        else:
            raise HTTPException(
                status_code=404,
                detail="Call not found or playback failed",
            )
    except Exception as e:
        logger.error(f"Failed to play audio: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))