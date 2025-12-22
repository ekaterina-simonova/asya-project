import asyncio
import json
import logging
import os
import subprocess
import wave
from pathlib import Path
from typing import Optional

import aiohttp
import numpy as np
import torch
from nemo.collections.asr.models import EncDecCTCModelBPE

# ---------- Логирование ----------

logger = logging.getLogger("nemo_ari_app")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# ---------- Пути и константы ----------

BASE_DIR = Path(__file__).resolve().parent
CALL_RECORDS_DIR = BASE_DIR / "call_records"
MODELS_DIR = BASE_DIR / "models"

CALL_RECORDS_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Параметры ARI / Asterisk
ARI_BASE_URL = os.getenv("ARI_BASE_URL", "http://localhost:8088/ari")
ARI_APP = os.getenv("ARI_APP", "fast_api")
ARI_USER = os.getenv("ARI_USER", "avr")
ARI_PASSWORD = os.getenv("ARI_PASSWORD", "avr_password")

AST_RECORDING_DIR = "/var/spool/asterisk/recording"
AST_SOUNDS_DIR = "/var/lib/asterisk/sounds"

# Параметры NeMo ASR
ASR_MODEL_NAME = os.getenv("ASR_MODEL_NAME", "stt_ru_conformer_ctc_large")

# Параметры Silero TTS
SILERO_MODEL_URL = "https://models.silero.ai/models/tts/ru/v3_1_ru.pt"
SILERO_MODEL_LOCAL = MODELS_DIR / "silero_v3_1_ru.pt"
SILERO_SAMPLE_RATE = 8000  # критично: 8000 Гц, как ждёт Asterisk
SILERO_SPEAKER = "xenia"  # женский голос

# Глобальные объекты
asr_model: Optional[EncDecCTCModelBPE] = None
silero_model = None
silero_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# ---------- Инициализация NeMo ASR ----------

def init_nemo_asr() -> EncDecCTCModelBPE:
    global asr_model
    if asr_model is not None:
        return asr_model

    logger.info("Загружаем NeMo ASR модель '%s' ...", ASR_MODEL_NAME)
    # Без именованного аргумента, как в test_nemo_asr.py
    asr_model = EncDecCTCModelBPE.from_pretrained(ASR_MODEL_NAME)
    if torch.cuda.is_available():
        asr_model = asr_model.to("cuda")
        logger.info("NeMo ASR модель переведена на cuda")
    else:
        logger.info("NeMo ASR модель работает на CPU")
    asr_model.eval()
    logger.info("NeMo ASR модель успешно загружена")
    return asr_model


# ---------- Инициализация Silero TTS ----------

def init_silero_tts():
    """
    Загружаем offline-модель Silero TTS в формате torch.package.
    """
    global silero_model
    if silero_model is not None:
        return silero_model

    if not SILERO_MODEL_LOCAL.exists():
        logger.info(
            "Локальный файл модели Silero не найден (%s), скачиваем из %s",
            SILERO_MODEL_LOCAL,
            SILERO_MODEL_URL,
        )
        import urllib.request

        SILERO_MODEL_LOCAL.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(SILERO_MODEL_URL, SILERO_MODEL_LOCAL)
        logger.info("Модель Silero сохранена в %s", SILERO_MODEL_LOCAL)

    from torch.package import PackageImporter

    logger.info(
        "Загружаем Silero TTS (standalone, ru v3_1) из %s на %s ...",
        SILERO_MODEL_LOCAL,
        silero_device,
    )
    importer = PackageImporter(str(SILERO_MODEL_LOCAL))
    silero = importer.load_pickle("tts_models", "model")
    silero.to(silero_device)

    silero_model = silero
    logger.info(
        "Silero TTS инициализирован: %s на устройстве %s (пример текста: 'Привет, я голосовой бот Ася.')",
        type(silero_model),
        silero_device,
    )
    return silero_model


# ---------- ASR: распознавание одной WAV ----------

async def transcribe_wav(wav_path: str) -> str:
    """
    Распознаёт речь в одном wav-файле с помощью NeMo ASR.
    Возвращает распознанный текст или пустую строку.
    """
    model = init_nemo_asr()
    loop = asyncio.get_running_loop()

    def _do_transcribe() -> str:
        try:
            hyps = model.transcribe(
                [wav_path],
                batch_size=1,
                return_hypotheses=True,
            )
        except TypeError:
            # fallback: старая сигнатура без return_hypotheses
            texts = model.transcribe([wav_path])
            if not texts:
                return ""
            return (texts[0] or "").strip()

        if not hyps:
            return ""

        hyp = hyps[0]
        # В NeMo 2.6 это обычно объект Hypothesis с полем .text
        text = getattr(hyp, "text", None)
        if text is None:
            # Если вдруг вернулась строка
            if isinstance(hyp, str):
                text = hyp
            else:
                text = ""
        return text.strip()

    logger.info("[ASR] Начинаем распознавание: %s", wav_path)
    text = await loop.run_in_executor(None, _do_transcribe)
    logger.info("[ASR] Результат распознавания для %s: %r", wav_path, text)
    return text


# ---------- TTS: синтез и копирование в контейнер ----------

async def synthesize_tts(text: str, basename: str) -> str:
    """
    Синтезирует речь с помощью Silero TTS в локальный WAV-файл
    и копирует его в /var/lib/asterisk/sounds внутри контейнера asterisk.
    Возвращает базовое имя файла (без расширения), которое надо
    использовать в ARI play как media='sound:<basename>'.
    """
    model = init_silero_tts()
    loop = asyncio.get_running_loop()
    local_wav = CALL_RECORDS_DIR / f"{basename}.wav"

    def _do_tts():
        logger.info(
            "[TTS] Синтезируем речь для %r в %s (sample_rate=%d, speaker=%s)",
            text,
            local_wav,
            SILERO_SAMPLE_RATE,
            SILERO_SPEAKER,
        )
        with torch.no_grad():
            audio = model.apply_tts(
                text=text,
                speaker=SILERO_SPEAKER,
                sample_rate=SILERO_SAMPLE_RATE,  # <<< 8 kHz для телефонии
            )
        if isinstance(audio, torch.Tensor):
            audio_np = audio.cpu().numpy()
        else:
            audio_np = np.array(audio)

        # моно
        if audio_np.ndim > 1:
            audio_np = audio_np[0, :]

        # нормализуем и конвертируем в int16
        audio_np = np.clip(audio_np, -1.0, 1.0)
        audio_int16 = (audio_np * 32767.0).astype(np.int16)

        # пишем WAV 16-bit PCM, 8 kHz
        with wave.open(str(local_wav), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16 bit
            wf.setframerate(SILERO_SAMPLE_RATE)
            wf.writeframes(audio_int16.tobytes())

        logger.info(
            "[TTS] Локальный WAV создан: %s (size=%d)",
            local_wav,
            local_wav.stat().st_size,
        )

    await loop.run_in_executor(None, _do_tts)

    # Копируем в контейнер asterisk
    container_wav = f"{AST_SOUNDS_DIR}/{basename}.wav"
    cmd = [
        "docker",
        "cp",
        str(local_wav),
        f"asterisk:{container_wav}",
    ]
    logger.info(
        "[TTS] Копируем WAV в контейнер: %s -> %s",
        local_wav,
        container_wav,
    )
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        logger.error(
            "[TTS] Ошибка docker cp (rc=%s): stdout=%s stderr=%s",
            proc.returncode,
            stdout.decode(errors="ignore"),
            stderr.decode(errors="ignore"),
        )
        raise RuntimeError("docker cp для TTS завершился с ошибкой")
    logger.info("[TTS] WAV успешно скопирован в контейнер")

    return basename  # использовать в media='sound:<basename>'


# ---------- ARI: помощники ----------

async def start_recording(session: aiohttp.ClientSession, channel_id: str) -> str:
    """
    Запускает запись канала через ARI. Возвращает имя записи (без расширения).
    """
    record_name = f"call-{channel_id}"
    params = {
        "name": record_name,
        "format": "wav",
        "maxDurationSeconds": "8",
        "maxSilenceSecons": "0.5",
        "ifExists": "overwrite",
        "beep": "false",
        "terminateOn": "none",
    }
    url = f"{ARI_BASE_URL}/channels/{channel_id}/record"
    logger.info(
        "Запускаем запись через ARI: channel=%s, name=%s, params=%s",
        channel_id,
        record_name,
        params,
    )
    async with session.post(url, params=params) as resp:
        body = await resp.text()
        if resp.status not in (200, 201):
            logger.error(
                "Ошибка запуска записи канала %s: %s - %s",
                channel_id,
                resp.status,
                body,
            )
        else:
            logger.info(
                "Запись канала %s успешно запущена (status=%s, response=%s)",
                channel_id,
                resp.status,
                body,
            )
    return record_name


async def play_tts_on_channel(
    session: aiohttp.ClientSession, channel_id: str, basename: str
) -> None:
    """
    Проигрывает ранее сгенерированный TTS-файл (basename) на канале channel_id.
    """
    media_uri = f"sound:{basename}"
    url = f"{ARI_BASE_URL}/channels/{channel_id}/play"
    params = {"media": media_uri}
    logger.info(
        "[TTS] Запускаем воспроизведение %s на канале %s",
        media_uri,
        channel_id,
    )
    async with session.post(url, params=params) as resp:
        body = await resp.text()
        if resp.status not in (200, 201):
            logger.error(
                "[TTS] Ошибка воспроизведения TTS (status=%s): %s",
                resp.status,
                body,
            )
        else:
            logger.info(
                "[TTS] Воспроизведение успешно запущено (status=%s, body=%s)",
                resp.status,
                body,
            )


async def copy_recording_from_container(recording_name: str) -> Path:
    """
    Копирует запись из контейнера asterisk в локальную директорию и возвращает путь.
    """
    container_path = f"{AST_RECORDING_DIR}/{recording_name}.wav"
    local_path = CALL_RECORDS_DIR / f"{recording_name}.wav"

    cmd = [
        "docker",
        "cp",
        f"asterisk:{container_path}",
        str(local_path),
    ]
    logger.info(
        "Копируем запись из контейнера: %s -> %s",
        container_path,
        local_path,
    )
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        logger.error(
            "Ошибка docker cp записи %s (rc=%s): stdout=%s stderr=%s",
            recording_name,
            proc.returncode,
            stdout.decode(errors="ignore"),
            stderr.decode(errors="ignore"),
        )
        raise RuntimeError("docker cp для записи завершился с ошибкой")

    size = local_path.stat().st_size
    logger.info(
        "Запись %s скопирована в %s (size=%d)",
        recording_name,
        local_path,
        size,
    )
    return local_path


# ---------- Обработчики ARI событий ----------

async def handle_stasis_start(
    session: aiohttp.ClientSession, event: dict
) -> None:
    channel = event.get("channel") or {}
    channel_id = channel.get("id")
    caller = (channel.get("caller") or {}).get("number")
    exten = (channel.get("dialplan") or {}).get("exten")
    app = event.get("application")

    logger.info(
        "[StasisStart] channel_id=%s, from=%s, to=%s, app=%s",
        channel_id,
        caller,
        exten,
        app,
    )

    if not channel_id:
        return

    # Запускаем запись этого канала
    await start_recording(session, channel_id)


async def handle_recording_finished(
    session: aiohttp.ClientSession, event: dict
) -> None:
    rec = event.get("recording") or {}
    name = rec.get("name")
    state = rec.get("state")
    target_uri = rec.get("target_uri", "")

    logger.info(
        "[RecordingFinished] name=%s state=%s target_uri=%s",
        name,
        state,
        target_uri,
    )

    if not name or state != "done":
        return

    channel_id = None
    if target_uri.startswith("channel:"):
        channel_id = target_uri.split(":", 1)[1]

    # Копируем wav из контейнера
    try:
        local_rec_path = await copy_recording_from_container(name)
    except Exception as e:
        logger.error(
            "Не удалось скопировать запись %s из контейнера: %s",
            name,
            e,
        )
        return

    # ASR
    user_text = ""
    try:
        user_text = await transcribe_wav(str(local_rec_path))
    except Exception as e:
        logger.exception(
            "Ошибка при распознавании NeMo ASR для %s: %s",
            local_rec_path,
            e,
        )

    logger.info("[ASR] Итоговый текст для %s: %r", name, user_text)

    # Ответ бота (пока простое эхо)
    if not user_text.strip():
        bot_reply = (
            "Я вас услышала, но не смогла ничего разобрать. "
            "Повторите, пожалуйста."
        )
    else:
        bot_reply = (
            "Я вас услышала. Вы сказали: "
            f"{user_text}. Чем могу помочь?"
        )

    logger.info(
        "[BOT] channel=%s name=%s текст пользователя: %r",
        channel_id,
        name,
        user_text,
    )
    logger.info(
        "[BOT] Ответ бота для name=%s: %r",
        name,
        bot_reply,
    )

    if not channel_id:
        logger.warning(
            "Не удалось определить channel_id для записи %s, "
            "TTS воспроизводить не будем",
            name,
        )
        return

    # TTS + воспроизведение
    try:
        tts_basename = f"tts-{name}"
        tts_basename = await synthesize_tts(bot_reply, tts_basename)
        await play_tts_on_channel(session, channel_id, tts_basename)
    except Exception as e:
        logger.exception(
            "Ошибка TTS/воспроизведения для канала %s и записи %s: %s",
            channel_id,
            name,
            e,
        )
        return


async def ari_events_loop() -> None:
    """
    Основной цикл работы с ARI WebSocket.
    """
    ws_url = f"{ARI_BASE_URL}/events"
    params = {"app": ARI_APP, "subscribeAll": "true"}

    auth = aiohttp.BasicAuth(ARI_USER, ARI_PASSWORD)

    logger.info(
        "Подключаемся к ARI WebSocket: %s с params=%s",
        ws_url,
        params,
    )

    async with aiohttp.ClientSession(auth=auth) as session:
        logger.info(
            "Создана aiohttp-сессия для ARI (user=%s)", ARI_USER
        )
        while True:
            try:
                async with session.ws_connect(ws_url, params=params) as ws:
                    logger.info("ARI WebSocket подключен как app='%s'", ARI_APP)
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            try:
                                event = json.loads(msg.data)
                            except json.JSONDecodeError:
                                logger.warning(
                                    "Не удалось распарсить JSON из ARI: %r",
                                    msg.data,
                                )
                                continue

                            event_type = event.get("type")
                            if event_type == "ChannelStateChange":
                                channel = event.get("channel") or {}
                                ch_id = channel.get("id")
                                st = channel.get("state")
                                caller = (channel.get("caller") or {}).get("number")
                                exten = (channel.get("dialplan") or {}).get("exten")
                                logger.info(
                                    "[ChannelStateChange] channel_id=%s: %s, from=%s, to=%s",
                                    ch_id,
                                    st,
                                    caller,
                                    exten,
                                )
                            elif event_type == "StasisStart":
                                await handle_stasis_start(session, event)
                            elif event_type == "RecordingFinished":
                                await handle_recording_finished(session, event)
                            elif event_type == "StasisEnd":
                                ch = event.get("channel") or {}
                                ch_id = ch.get("id")
                                logger.info(
                                    "[StasisEnd] channel_id=%s", ch_id
                                )
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            logger.error(
                                "Ошибка ARI WebSocket: %s", msg
                            )
                            break
            except Exception as e:
                logger.exception(
                    "Ошибка при работе с ARI WebSocket: %s", e
                )

            logger.info("Пробуем переподключиться к ARI через 3 секунды...")
            await asyncio.sleep(3)


async def main_async():
    # Подготовим NeMo ASR, чтобы не грузить модель при первом звонке
    init_nemo_asr()
    await ari_events_loop()


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
