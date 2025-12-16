import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from asya_core.models.llm import LLM
from asya_core.models.stt import STT
from asya_core.models.tts import TTS
from asya_core.models.vad import VAD
from asya_core.knowledge_base import KnowledgeBase
from asya_core.database import DatabaseManager
from asya_core.schemas import DialogState, CallProfile, TranscriptSegment, LLMResponse

logger = logging.getLogger(__name__)


class DialogManager:
    """
    Ядро системы "Ася". Управляет потоком диалога, передавая аудио и историю в LLM,
    который сам определяет, как вести диалог, и возвращает структурированный ответ.
    """

    def __init__(
        self,
        llm: LLM,
        stt: STT,
        tts: TTS,
        vad: VAD,
        kb: KnowledgeBase,
        db: DatabaseManager,
    ):
        self.llm = llm
        self.stt = stt
        self.tts = tts
        self.vad = vad
        self.kb = kb
        self.db = db

        # Состояние диалога
        self.state = DialogState()
        self.profile = CallProfile()
        self.transcript: List[TranscriptSegment] = []
        self.history: List[Dict[str, str]] = []

        # Добавляем системный промпт в историю
        self._init_history()

    def _init_history(self):
        """Инициализирует историю диалога с системным промптом."""
        # Загружаем FULL_PROMPT из файла или константы
        # В реальности — это должен быть большой промпт из файла, который вы уже имеете
        with open("prompts/full_prompt.txt", "r", encoding="utf-8") as f:
            full_prompt = f.read()

        self.history.append({
            "role": "system",
            "content": full_prompt
        })

    def process_audio_chunk(self, audio_chunk: bytes) -> Dict[str, Any]:
        """
        Главный метод: обрабатывает один аудиофрагмент.
        Возвращает JSON-ответ в формате, требуемом промптом:
        {
          "reasoning": "...",
          "answer": "...",
          "system_info": "..."
        }
        """
        try:
            # 1. VAD: определяем, есть ли речь
            is_speech = self.vad.detect_speech(audio_chunk)

            if is_speech:
                # Добавляем аудиофрагмент в буфер STT
                self.stt.add_audio_chunk(audio_chunk)
                return self._build_response("Прослушиваю...", None, None)

            else:
                # Если тишина — запускаем STT на накопленном аудио
                if self.stt.has_audio():
                    full_transcript = self.stt.transcribe()
                    self.transcript.append(TranscriptSegment(
                        speaker="client",
                        text=full_transcript,
                        timestamp=datetime.now()
                    ))
                    self.history.append({"role": "user", "content": full_transcript})

                    # 2. Отправляем полную историю в LLM
                    llm_response_raw = self.llm.generate(self.history)

                    # 3. Парсим ответ LLM
                    response = self._parse_llm_response(llm_response_raw)

                    # 4. Обновляем профиль по system_info
                    if response.get("system_info"):
                        self._update_profile_from_system_info(response["system_info"])

                    # 5. Добавляем ответ LLM в историю
                    self.history.append({"role": "assistant", "content": response["answer"]})

                    # 6. Генерируем TTS
                    audio_output = self.tts.synthesize(response["answer"])

                    # 7. Сохраняем транскрипцию и логи
                    self.transcript.append(TranscriptSegment(
                        speaker="bot",
                        text=response["answer"],
                        timestamp=datetime.now()
                    ))

                    # 8. Логируем
                    logger.info(f"Dialog step: {response['reasoning']}")

                    # 9. Возвращаем ответ в формате промпта
                    return response

                else:
                    # Нет аудио — ждём
                    return self._build_response("Жду речь...", None, None)

        except Exception as e:
            logger.error(f"Ошибка в dialog_manager: {e}", exc_info=True)
            return {
                "reasoning": f"Системная ошибка: {str(e)}",
                "answer": "Извините, произошла внутренняя ошибка. Пожалуйста, попробуйте ещё раз.",
                "system_info": f"ERROR: {str(e)}"
            }

    def handle_interrupt(self, client_text: str) -> Dict[str, Any]:
        """
        Обрабатывает перебивание: клиент говорит, пока Ася говорит.
        """
        logger.info("Перебивание: клиент говорит во время ответа Аси.")

        # 1. Останавливаем TTS
        self.tts.stop()

        # 2. Сбрасываем буфер STT
        self.stt.clear_buffer()

        # 3. Добавляем реплику клиента в историю
        self.history.append({"role": "user", "content": client_text})

        # 4. Получаем ответ от LLM
        llm_response_raw = self.llm.generate(self.history)
        response = self._parse_llm_response(llm_response_raw)

        # 5. Обновляем профиль
        if response.get("system_info"):
            self._update_profile_from_system_info(response["system_info"])

        # 6. Добавляем ответ в историю
        self.history.append({"role": "assistant", "content": response["answer"]})

        # 7. Генерируем TTS
        audio_output = self.tts.synthesize(response["answer"])

        # 8. Логируем
        logger.info(f"Interrupted dialog step: {response['reasoning']}")

        return response

    def _parse_llm_response(self, raw_response: str) -> LLMResponse:
        """
        Парсит сырой ответ LLM в строгий JSON-формат.
        """
        try:
            # Убираем лишние символы (если LLM добавил Markdown или пояснения)
            if raw_response.startswith("```json"):
                raw_response = raw_response[7:-3].strip()

            parsed = json.loads(raw_response)

            # Проверяем обязательные поля
            required_fields = {"reasoning", "answer", "system_info"}
            if not required_fields.issubset(parsed.keys()):
                raise ValueError(f"Ответ LLM не содержит всех обязательных полей: {required_fields}")

            return LLMResponse(**parsed)

        except json.JSONDecodeError as e:
            logger.error(f"Неверный JSON от LLM: {raw_response[:200]}... | Ошибка: {e}")
            return LLMResponse(
                reasoning="Ошибка парсинга ответа. Повторите запрос.",
                answer="Извините, я не смог обработать ваш запрос. Пожалуйста, повторите.",
                system_info=""
            )
        except Exception as e:
            logger.error(f"Ошибка при парсинге ответа LLM: {e}")
            return LLMResponse(
                reasoning=f"Ошибка обработки: {str(e)}",
                answer="Произошла ошибка. Пожалуйста, повторите запрос.",
                system_info=""
            )

    def _update_profile_from_system_info(self, system_info: str):
        """
        Обновляет профиль клиента на основе строки system_info.
        Пример: "Поле 'Имя клиента' обновлено: Иван Васильевич"
        """
        if "Поле '" in system_info and "' обновлено:" in system_info:
            try:
                prefix, value = system_info.split("Поле '", 1)[1].split("' обновлено:", 1)
                field = prefix.strip()
                value = value.strip().strip('"')

                if field == "Имя клиента":
                    self.profile.name = value
                elif field == "Телефон":
                    self.profile.phone = value
                elif field == "Город":
                    self.profile.city = value
                elif field == "ИНН":
                    self.profile.inn = value
                elif field == "Организация":
                    self.profile.company = value
                elif field == "Отдел":
                    self.profile.department = value
                elif field == "Потребность клиента":
                    self.profile.request = value

                logger.info(f"Профиль обновлён: {field} = {value}")

            except Exception as e:
                logger.warning(f"Не удалось обновить поле из system_info: {system_info} | {e}")

    def _build_response(self, answer: str, reasoning: Optional[str], system_info: Optional[str]) -> Dict[str, Any]:
        """Формирует ответ в строгом формате JSON, как требует промпт."""
        return {
            "reasoning": reasoning or "Ожидание речи клиента...",
            "answer": answer,
            "system_info": system_info or ""
        }

    def save_call_data(self):
        """Сохраняет полный диалог и профиль в БД."""
        self.db.save_call(
            profile=self.profile,
            transcript=self.transcript,
            history=self.history
        )