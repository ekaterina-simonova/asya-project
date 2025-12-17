import os
import yaml
import aiohttp
import logging
from typing import Optional, List, Any

logger = logging.getLogger(__name__)


class AriClient:
    """
    Асинхронный клиент для Asterisk ARI (REST API).

    Читает настройки из config/asterisk_ari_config.yaml (секция `asterisk`)
    и переменных окружения ARI_USERNAME / ARI_PASSWORD.
    """

    def __init__(self):
        # Путь к конфигу относительно корня проекта Asya
        config_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..",
            "config",
            "asterisk_ari_config.yaml",
        )

        with open(config_path, "r", encoding="utf-8") as f:
            raw_cfg = yaml.safe_load(f) or {}

        cfg = raw_cfg.get("asterisk", {})

        # Базовый URL ARI, без /ari в конце
        self.base_url = cfg.get("base_url", "http://localhost:8088").rstrip("/")

        # Логин/пароль: сначала из .env, затем из конфига
        self.username = os.getenv("ARI_USERNAME", cfg.get("username", "asya_app"))
        self.password = os.getenv("ARI_PASSWORD", cfg.get("password", ""))

        self.app_name = cfg.get("app_name", "asya_app")

        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def connect(self):
        """Создаёт aiohttp-сессию, если её ещё нет."""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(
                auth=aiohttp.BasicAuth(self.username, self.password),
                timeout=timeout,
            )
            logger.info("✅ ARI: сессия инициализирована")

    async def close(self):
        """Закрывает сессию."""
        if self.session is not None:
            await self.session.close()
            self.session = None
            logger.info("🔌 ARI: сессия закрыта")

    async def check_connection(self) -> bool:
        """
        Простейшая проверка доступности ARI.
        Пробуем получить список приложений.
        """
        try:
            if self.session is None:
                await self.connect()

            url = f"{self.base_url}/ari/applications"
            async with self.session.get(url) as resp:
                if resp.status == 200:
                    logger.info("✅ ARI: соединение успешно (applications)")
                    return True
                text = await resp.text()
                logger.warning(f"⚠️ ARI: неожиданный статус {resp.status}: {text}")
                return False
        except Exception as e:
            logger.error(f"❌ ARI: ошибка при проверке соединения: {e}")
            return False

    async def get_active_calls(self) -> List[Any]:
        """Возвращает список активных каналов."""
        if self.session is None:
            await self.connect()

        url = f"{self.base_url}/ari/channels"
        try:
            async with self.session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.info(f"📊 ARI: активных каналов: {len(data)}")
                    return data
                text = await resp.text()
                logger.error(f"❌ ARI: get_active_calls {resp.status}: {text}")
                return []
        except Exception as e:
            logger.error(f"❌ ARI: исключение в get_active_calls: {e}")
            return []

    async def originate_call(
        self,
        endpoint: str,
        caller_id: str,
        context: str,
        extension: str,
        variables: Optional[dict] = None,
    ) -> str:
        """
        Инициирует исходящий звонок через ARI.
        Возвращает ID канала (call_id) при успехе.
        """
        if self.session is None:
            await self.connect()

        url = f"{self.base_url}/ari/channels"
        params = {
            "endpoint": endpoint,
            "app": self.app_name,
            "callerId": caller_id,
            "context": context,
            "extension": extension,
        }

        if variables:
            for k, v in variables.items():
                params[f"variables[{k}]"] = v

        try:
            async with self.session.post(url, params=params) as resp:
                if resp.status in (200, 202):
                    result = await resp.json()
                    call_id = result.get("id")
                    logger.info(f"📞 ARI: исходящий звонок инициирован {call_id} → {endpoint}")
                    return call_id
                text = await resp.text()
                logger.error(f"❌ ARI: originate_call {resp.status}: {text}")
                raise RuntimeError(f"ARI originate error {resp.status}: {text}")
        except Exception as e:
            logger.error(f"❌ ARI: исключение в originate_call: {e}")
            raise

    async def hangup_call(self, call_id: str) -> bool:
        """Завершает звонок по ID канала."""
        if self.session is None:
            await self.connect()

        url = f"{self.base_url}/ari/channels/{call_id}"
        try:
            async with self.session.delete(url) as resp:
                if resp.status == 204:
                    logger.info(f"📞 ARI: вызов завершён {call_id}")
                    return True
                text = await resp.text()
                logger.error(f"❌ ARI: hangup_call {resp.status}: {text}")
                return False
        except Exception as e:
            logger.error(f"❌ ARI: исключение в hangup_call: {e}")
            return False

    async def transfer_call(self, call_id: str, target_endpoint: str) -> bool:
        """
        Простейшая реализация "перевода" через redirect.
        """
        if self.session is None:
            await self.connect()

        url = f"{self.base_url}/ari/channels/{call_id}/redirect"
        params = {"endpoint": target_endpoint}

        try:
            async with self.session.post(url, params=params) as resp:
                if resp.status in (200, 204):
                    logger.info(f"🔀 ARI: вызов {call_id} переведён на {target_endpoint}")
                    return True
                text = await resp.text()
                logger.error(f"❌ ARI: transfer_call {resp.status}: {text}")
                return False
        except Exception as e:
            logger.error(f"❌ ARI: исключение в transfer_call: {e}")
            return False

    async def play_audio(self, call_id: str, audio_file: str) -> bool:
        """
        Воспроизводит аудио в канале.
        audio_file обычно в формате 'sound:custom/...' или similar.
        """
        if self.session is None:
            await self.connect()

        url = f"{self.base_url}/ari/channels/{call_id}/play"
        params = {"media": audio_file}

        try:
            async with self.session.post(url, params=params) as resp:
                if resp.status in (200, 204):
                    logger.info(f"🎵 ARI: проигрываю {audio_file} в канале {call_id}")
                    return True
                text = await resp.text()
                logger.error(f"❌ ARI: play_audio {resp.status}: {text}")
                return False
        except Exception as e:
            logger.error(f"❌ ARI: исключение в play_audio: {e}")
            return False