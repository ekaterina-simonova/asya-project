import os
import yaml
import aiohttp
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class AriClient:
    def __init__(self):
        config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "asterisk_ari_config.yaml")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        self.base_url = config["asterisk"]["base_url"].rstrip('/')
        self.username = config["asterisk"]["username"]
        self.password = config["asterisk"]["password"]
        self.app_name = config["asterisk"].get("app_name", "asya_app")  # по умолчанию "asya_app"

        # Асинхронный HTTP-клиент
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Поддержка async with"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def connect(self):
        """Инициализация сессии aiohttp"""
        if self.session is None:
            self.session = aiohttp.ClientSession(
                auth=aiohttp.BasicAuth(self.username, self.password),
                timeout=aiohttp.ClientTimeout(total=30)
            )
            logger.info("✅ Асинхронное соединение с ARI инициализировано")

    async def close(self):
        """Закрытие сессии"""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("🔌 Соединение с ARI закрыто")

    async def play_audio(self, channel_id: str, sound_path: str):
        """
        Проиграть аудиофайл через ARI REST API.
        sound_path — это путь к файлу на сервере Asterisk (например, "sound:custom/my_audio")
        """
        if not self.session:
            await self.connect()

        url = f"{self.base_url}/ari/channels/{channel_id}/play"
        data = {
            "media": sound_path,
            "skipMS": 0,
            "loops": 1
        }

        try:
            async with self.session.post(url, json=data) as resp:
                if resp.status == 204:
                    logger.info(f"🎵 Проигрывание: {sound_path} для канала {channel_id}")
                else:
                    text = await resp.text()
                    logger.error(f"❌ Ошибка воспроизведения: {resp.status} - {text}")
                    raise RuntimeError(f"ARI error {resp.status}: {text}")
        except Exception as e:
            logger.error(f"❌ Исключение при воспроизведении аудио: {e}")
            raise

    async def hangup(self, channel_id: str):
        """Завершить звонок через ARI"""
        if not self.session:
            await self.connect()

        url = f"{self.base_url}/ari/channels/{channel_id}"

        try:
            async with self.session.delete(url) as resp:
                if resp.status == 204:
                    logger.info(f"📞 Завершён звонок: {channel_id}")
                else:
                    text = await resp.text()
                    logger.error(f"❌ Ошибка завершения звонка: {resp.status} - {text}")
                    raise RuntimeError(f"ARI error {resp.status}: {text}")
        except Exception as e:
            logger.error(f"❌ Исключение при завершении звонка: {e}")
            raise

    async def get_active_calls(self):
        """Получить список активных звонков (каналов)"""
        if not self.session:
            await self.connect()

        url = f"{self.base_url}/ari/channels"

        try:
            async with self.session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.info(f"📊 Получено {len(data)} активных каналов")
                    return data
                else:
                    text = await resp.text()
                    logger.error(f"❌ Ошибка получения списка звонков: {resp.status} - {text}")
                    return []
        except Exception as e:
            logger.error(f"❌ Исключение при получении звонков: {e}")
            return []

    async def originate_call(self, endpoint: str, caller_id: str, context: str, extension: str, variables: dict = None):
        """
        Инициировать исходящий звонок через ARI
        """
        if not self.session:
            await self.connect()

        url = f"{self.base_url}/ari/channels"

        data = {
            "endpoint": endpoint,
            "app": self.app_name,
            "callerId": caller_id,
            "context": context,
            "extension": extension,
            "variables": variables or {}
        }

        try:
            async with self.session.post(url, json=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    call_id = result.get("id")
                    logger.info(f"📞 Исходящий звонок инициирован: {call_id} → {endpoint}")
                    return call_id
                else:
                    text = await resp.text()
                    logger.error(f"❌ Ошибка инициации звонка: {resp.status} - {text}")
                    raise RuntimeError(f"ARI originate error {resp.status}: {text}")
        except Exception as e:
            logger.error(f"❌ Исключение при инициации звонка: {e}")
            raise