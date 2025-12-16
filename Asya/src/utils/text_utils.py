import yaml
import logging

logger = logging.getLogger(__name__)

def load_pronunciation_dict(file_path):
    """
    Загружает словарь произношения из YAML.
    Ожидается формат: dictionary: { term: pronunciation }
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            if not isinstance(config, dict) or 'dictionary' not in config:
                logger.error(f"Неверный формат YAML: ожидается ключ 'dictionary' в {file_path}")
                return {}
            logger.info(f"Словарь произношения загружен: {len(config['dictionary'])} записей")
            return config['dictionary']
    except Exception as e:
        logger.error(f"Ошибка загрузки словаря произношения: {e}")
        return {}

def replace_terms(text: str, dictionary: dict) -> str:
    """
    Заменяет все вхождения терминов на их произносимые формы.
    Сортировка по длине — чтобы длинные термины заменялись первыми.
    """
    if not text or not dictionary:
        return text

    # Сортируем по длине — важно для терминов типа "ШБТ-50" vs "ШБТ"
    sorted_terms = sorted(dictionary.keys(), key=len, reverse=True)

    for term in sorted_terms:
        if term in text:
            text = text.replace(term, dictionary[term])

    return text