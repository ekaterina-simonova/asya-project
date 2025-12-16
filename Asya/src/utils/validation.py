import re
from typing import Optional

def validate_phone(phone: str) -> bool:
    """Проверяет, является ли строка корректным номером."""
    if not phone:
        return False
    digits = ''.join(filter(str.isdigit, str(phone)))
    if len(digits) == 11 and digits[0] in ('7', '8'):
        return True
    elif len(digits) == 10 and digits[0] == '9':
        return True
    return False

def normalize_phone(phone: str) -> Optional[str]:
    """Приводит номер к формату +7XXXXXXXXXX"""
    if not phone:
        return None
    digits = ''.join(filter(str.isdigit, str(phone)))
    if len(digits) == 11:
        if digits[0] == '8':
            digits = '7' + digits[1:]
        elif digits[0] == '7':
            pass
        else:
            return None
    elif len(digits) == 10 and digits[0] == '9':
        digits = '7' + digits
    else:
        return None
    return f"+{digits}"

def extract_city(text: str) -> Optional[str]:
    """Извлекает название города из фразы"""
    if not text or not isinstance(text, str):
        return None

    patterns = [
        r'из\s+([а-яА-ЯёЁ\-]+)',
        r'в\s+([а-яА-ЯёЁ\-]+)',
        r'город\s+[,:]*\s*([а-яА-ЯёЁ\-]+)'
    ]

    text_lower = text.lower().strip()
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            city = match.group(1).capitalize()
            if len(city) > 2:
                return city
    return None

def is_valid_department(department: str) -> bool:
    """Проверяет, относится ли отдел к одному из допустимых"""
    valid = ["коммерческий", "бухгалтерский", "логистика", "закупки", "маркетинг"]
    return department.lower().strip() in valid

def validate_call_id(call_id: str) -> bool:
    """
    Проверяет формат call_id: либо UUID, либо timestamp-based.
    """
    if not call_id:
        return False

    # Проверяем UUID-формат (примерно 8-4-4-4-12)
    uuid_pattern = r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$'
    if re.match(uuid_pattern, str(call_id), re.IGNORECASE):
        return True

    # Проверяем кастомный формат: call_YYYYMMDD_HHMMSS_UUID или short
    timestamp_pattern = r'^call_\d{8}_\d{6}_[a-z0-9]+$'
    if re.match(timestamp_pattern, str(call_id)):
        return True

    return False