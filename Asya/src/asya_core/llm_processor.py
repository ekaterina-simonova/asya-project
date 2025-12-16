import logging
import json
import os
from typing import List, Dict, Any, Optional

# Настройка логгера
logger = logging.getLogger(__name__)

class LLMProcessor:
    """
    Класс для взаимодействия с LLM (Mistral-NeMo-Minitron-8B-Instruct-Q6_K_L.gguf).
    Отвечает за отправку промпта и парсинг ответа в строгом формате JSON.
    Не содержит бизнес-логики — только инфраструктура для вызова модели.
    """

    def __init__(self, model_path: str):
        """
        Инициализация LLMProcessor.
        
        Args:
            model_path (str): Путь к GGUF-файлу модели (например, "models/Mistral-NeMo-Minitron-8B-Instruct-Q6_K_L.gguf")
        """
        self.model_path = model_path
        self._load_model()  # Инициализируем модель при старте

    def _load_model(self):
        """
        Загружает модель через llama.cpp (или другую библиотеку).
        В реальности — это может быть vLLM, llama.cpp, или другой движок.
        Здесь — заглушка для демонстрации.
        """
        # В реальности здесь будет код инициализации движка (например, llama.cpp)
        # Пример для llama.cpp:
        # from llama_cpp import Llama
        # self.llm = Llama(model_path=self.model_path, n_gpu_layers=35, n_ctx=8192, verbose=False)
        #
        # Для целей этого файла — мы просто подтверждаем, что модель доступна.
        logger.info(f"LLMProcessor: Модель загружена из {self.model_path}")
        # В реальности проверяем существование файла
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Модель не найдена по пути: {self.model_path}")

    def generate(self, history: List[Dict[str, str]]) -> str:
        """
        Отправляет полную историю диалога в LLM и возвращает сырые ответы.

        Args:
            history (List[Dict[str, str]]): Список сообщений в формате:
                [
                    {"role": "system", "content": "FULL_PROMPT..."},
                    {"role": "user", "content": "Привет, меня зовут Иван"},
                    {"role": "assistant", "content": "Здравствуйте, Иван! Я Ася..."},
                    {"role": "user", "content": "Какой диаметр у ШБТ-50?"}
                ]

        Returns:
            str: Сырой ответ LLM в виде строки — **должен быть в формате JSON**:
                {
                  "reasoning": "Обоснование...",
                  "answer": "Ответ клиенту...",
                  "system_info": "Обновление профиля: Имя клиента = Иван"
                }

        Raises:
            RuntimeError: Если ответ не в формате JSON или произошла ошибка.
        """
        try:
            # --- В РЕАЛЬНОСТИ: Здесь будет вызов движка ---
            # Пример для llama.cpp:
            # response = self.llm.create_chat_completion(
            #     messages=history,
            #     temperature=0.1,
            #     max_tokens=512,
            #     stop=["</s>"]
            # )
            # raw_response = response['choices'][0]['message']['content']

            # --- ЗАГЛУШКА ДЛЯ ДЕМОНСТРАЦИИ (в реальности — вызов модели) ---
            # В реальном коде — здесь будет реальный вызов к вашему движку (llama.cpp, vLLM и т.д.)
            # Для примера — возвращаем "заглушку", как будто модель ответила
            # В реальности — уберите этот блок и замените на реальный вызов!

            # Пример реального вызова (закомментирован, чтобы не запускался без движка):
            # raw_response = self._call_llm_engine(history)

            # --- ВРЕМЕННАЯ ЗАГЛУШКА (для тестирования без модели) ---
            # Удалите этот блок после подключения реального движка!
            raw_response = '''
{
  "reasoning": "Клиент спросил про ШБТ-50 — это запрос о продукте. Ищу в базе знаний. Продукт найден: Шнур базальтовый теплоизоляционный ШБТ-50. Диаметр — 50 мм. Отвечаю.",
  "answer": "Шнур ШБТ-50 имеет диаметр 50 мм. Он предназначен для теплоизоляции трубопроводов и систем с температурой до 900°C.",
  "system_info": "Поле 'Потребность клиента' обновлено: интерес к ШБТ-50"
}
            '''.strip()

            # --- ВАЖНО: В реальности здесь будет вызов вашей модели! ---
            # Например:
            # raw_response = self._call_llm_engine(history)

            logger.debug(f"Отправленный промпт: {history}")
            logger.debug(f"Ответ LLM (сырой): {raw_response}")

            # --- ПАРСИНГ И ВАЛИДАЦИЯ ---
            # Убираем лишние символы, если LLM добавил Markdown-блоки
            if raw_response.startswith("```json"):
                raw_response = raw_response[7:-3].strip()

            # Парсим JSON
            parsed = json.loads(raw_response)

            # Проверяем обязательные поля
            required_fields = {"reasoning", "answer", "system_info"}
            if not required_fields.issubset(parsed.keys()):
                raise ValueError(f"Ответ LLM не содержит всех обязательных полей: {required_fields}")

            # Возвращаем сырую строку — **не парсим в объект**, чтобы не терять формат!
            # Это делается в DialogManager — там будет полный парсинг и обработка.
            return raw_response

        except json.JSONDecodeError as e:
            logger.error(f"LLM вернул некорректный JSON: {raw_response[:500]}... | Ошибка: {e}")
            raise RuntimeError(f"LLM вернул некорректный JSON: {str(e)}")
        except Exception as e:
            logger.error(f"Ошибка при вызове LLM: {str(e)}")
            raise RuntimeError(f"Ошибка при вызове LLM: {str(e)}")

    def _call_llm_engine(self, history: List[Dict[str, str]]) -> str:
        """
        Внутренний метод для реального вызова движка LLM (llama.cpp, vLLM и т.д.).
        Этот метод должен быть реализован в зависимости от выбранного движка.
        """
        # --- ПРИМЕР ДЛЯ llama.cpp ---
        try:
            from llama_cpp import Llama
            if not hasattr(self, 'llm'):
                self.llm = Llama(
                    model_path=self.model_path,
                    n_gpu_layers=35,      # Используем GPU
                    n_ctx=8192,           # Длина контекста
                    n_threads=8,          # Потоки CPU для обработки
                    verbose=False
                )
            response = self.llm.create_chat_completion(
                messages=history,
                temperature=0.1,
                max_tokens=512,
                stop=["</s>"],
                response_format={"type": "json_object"}  # Запрашиваем JSON
            )
            return response['choices'][0]['message']['content']
        except ImportError:
            raise RuntimeError("Для работы с llama.cpp требуется установить библиотеку: pip install llama-cpp-python")
        except Exception as e:
            raise RuntimeError(f"Ошибка при вызове llama.cpp: {str(e)}")