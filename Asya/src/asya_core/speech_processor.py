import yaml
import re
from typing import Dict, Any

class SpeechProcessor:
    """
    Класс для нормализации текста перед синтезом речи (TTS).
    Заменяет технические термины, артикулы и сленг на произносимые формы.
    Работает на основе словаря произношения из config/pronunciation_dictionary.yaml.
    """

    def __init__(self, dict_path: str = "config/pronunciation_dictionary.yaml"):
        """
        Инициализирует SpeechProcessor и загружает словарь произношения.
        
        Args:
            dict_path (str): Путь к YAML-файлу со словарём произношения.
        """
        self.pronunciation_dict = self._load_pronunciation_dict(dict_path)

    def _load_pronunciation_dict(self, dict_path: str) -> Dict[str, str]:
        """
        Загружает словарь произношения из YAML-файла.
        Формат YAML:
          term_replacements:
            "ШБТ": "Шнур базальтовый теплоизоляционный"
            "ШБТ-50": "Шнур базальтовый теплоизоляционный пятьдесят"
            "ОБМ": "Огнезащитный базальтовый материал"
            "EXPERT FIRE-M": "Эксперт Файер-М"
            ...
        """
        try:
            with open(dict_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                if not config or "term_replacements" not in config:
                    raise ValueError(f"Файл {dict_path} не содержит ключа 'term_replacements'")
                return config["term_replacements"]
        except FileNotFoundError:
            raise FileNotFoundError(f"Файл словаря произношения не найден: {dict_path}")
        except Exception as e:
            raise RuntimeError(f"Ошибка при загрузке словаря произношения: {e}")

    def prepare_text_for_tts(self, text: str) -> str:
        """
        Нормализует текст для TTS:
        - Заменяет термины и артикулы по словарю (с приоритетом по длине)
        - Убирает лишние пробелы и символы
        - Не изменяет грамматику, только произношение
        
        Args:
            text (str): Исходный текст от LLM
            
        Returns:
            str: Нормализованный текст для синтеза речи
        """
        if not text:
            return ""

        # Сортируем ключи по длине — сначала самые длинные (например, "ШБТ-50" до "ШБТ")
        sorted_terms = sorted(self.pronunciation_dict.keys(), key=len, reverse=True)
        
        result = text
        for term in sorted_terms:
            if term in result:
                result = result.replace(term, self.pronunciation_dict[term])

        # Убираем множественные пробелы
        result = re.sub(r'\s+', ' ', result).strip()

        return result