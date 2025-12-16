import sqlite3
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime

from asya_core.schemas import CallProfile, TranscriptSegment, CallLog

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Класс для управления базой данных SQLite (clients.db).
    Отвечает ТОЛЬКО за сохранение и чтение данных.
    НЕ содержит бизнес-логики — всё логика в dialog_manager.py.
    """

    def __init__(self, db_path: str = "data/clients.db"):
        """
        Инициализация менеджера базы данных.
        
        Args:
            db_path (str): Путь к файлу SQLite базы данных.
        """
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """
        Создаёт таблицы базы данных, если их нет.
        Использует структуру из вашего R&D-отчёта.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # --- clients_info ---
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clients_info (
                client_id TEXT PRIMARY KEY,
                phone TEXT UNIQUE,
                name TEXT,
                city_name TEXT,
                region_code TEXT,
                region_name TEXT,
                inn TEXT,
                organization TEXT,
                comment TEXT,
                last_call_summary TEXT,
                is_duplicate_city BOOLEAN DEFAULT FALSE,
                is_repeat_call BOOLEAN DEFAULT FALSE,
                assigned_manager_id TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # --- calls ---
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS calls (
                call_id TEXT PRIMARY KEY,
                client_id TEXT,
                timestamp DATETIME,
                department TEXT,
                product_service TEXT,
                request_text TEXT,
                next_step TEXT,
                target_department TEXT,
                manager_id TEXT,
                is_repeat_call BOOLEAN DEFAULT FALSE,
                is_work_time BOOLEAN DEFAULT TRUE,
                llm_retry_count INTEGER DEFAULT 0,
                sip_status TEXT,
                fallback_triggered BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (client_id) REFERENCES clients_info(client_id)
            )
        ''')

        # --- call_transcripts ---
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS call_transcripts (
                transcript_id INTEGER PRIMARY KEY AUTOINCREMENT,
                call_id TEXT,
                client_id TEXT,
                speaker TEXT,
                text TEXT,
                segment_id TEXT,
                segment_time DATETIME,
                llm_response BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (call_id) REFERENCES calls(call_id),
                FOREIGN KEY (client_id) REFERENCES clients_info(client_id)
            )
        ''')

        # --- jsons ---
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jsons (
                call_id TEXT PRIMARY KEY,
                client_id TEXT,
                timestamp DATETIME,
                json_data TEXT,
                FOREIGN KEY (call_id) REFERENCES calls(call_id),
                FOREIGN KEY (client_id) REFERENCES clients_info(client_id)
            )
        ''')

        # --- products ---
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                product_id TEXT PRIMARY KEY,
                official_name TEXT,
                slang_name TEXT,
                description TEXT,
                technical_specs TEXT,
                price TEXT,
                is_archived BOOLEAN DEFAULT FALSE,
                weight_priority INTEGER DEFAULT 0
            )
        ''')

        # --- regions_map ---
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS regions_map (
                region_code TEXT PRIMARY KEY,
                region_name TEXT,
                city_name TEXT,
                aliases TEXT,
                phone_route_code TEXT
            )
        ''')

        conn.commit()
        conn.close()
        logger.info("База данных инициализирована/проверена.")

    def save_call_data(self, profile: CallProfile, transcript: List[TranscriptSegment], history: List[Dict[str, str]]):
        """
        Сохраняет полный звонок в базу данных.
        Вызывается из dialog_manager.py после завершения диалога.

        Args:
            profile (CallProfile): Полный профиль клиента.
            transcript (List[TranscriptSegment]): Список реплик диалога.
            history (List[Dict[str, str]]): Полная история диалога (для JSON-дампа).
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # --- 1. Сохраняем/обновляем клиента ---
            client_id = str(profile.client_id) if profile.client_id else str(uuid.uuid4())
            profile.client_id = client_id  # Убеждаемся, что client_id есть

            cursor.execute('''
                INSERT OR REPLACE INTO clients_info 
                (client_id, phone, name, city_name, region_code, region_name, inn, organization, comment, 
                 is_duplicate_city, is_repeat_call, assigned_manager_id, last_call_summary)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                client_id,
                profile.get("Телефон"),
                profile.get("Имя клиента"),
                profile.get("Город"),
                profile.get("client_region", {}).get("code"),
                profile.get("client_region", {}).get("name"),
                profile.get("ИНН"),
                profile.get("Организация"),
                profile.get("Комментарии"),
                profile.get("is_duplicate_city", False),
                profile.is_repeat_call,
                profile.get("assigned_manager_id"),
                profile.last_call_summary if hasattr(profile, 'last_call_summary') else None
            ))

            # --- 2. Сохраняем запись звонка ---
            call_id = str(uuid.uuid4())
            last_call_summary = transcript[-1].text if transcript else ""

            cursor.execute('''
                INSERT INTO calls 
                (call_id, client_id, timestamp, department, product_service, request_text, 
                 next_step, target_department, manager_id, is_repeat_call, is_work_time, 
                 llm_retry_count, sip_status, fallback_triggered)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                call_id,
                client_id,
                datetime.now().isoformat(),
                profile.get("Отдел"),
                None,  # Будет заполнено из JSON
                profile.get("Комментарии"),
                "transfer",  # По умолчанию
                profile.get("Отдел"),
                profile.get("assigned_manager_id"),
                profile.is_repeat_call,
                True,  # По умолчанию
                0,  # Будет заполнено из JSON
                "answered",  # Будет заполнено из JSON
                False  # Будет заполнено из JSON
            ))

            # --- 3. Сохраняем транскрипцию ---
            for segment in transcript:
                cursor.execute('''
                    INSERT INTO call_transcripts 
                    (call_id, client_id, speaker, text, segment_id, segment_time, llm_response)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    call_id,
                    client_id,
                    segment.speaker,
                    segment.text,
                    f"seg_{segment.timestamp.strftime('%H%M%S')}",
                    segment.timestamp.isoformat(),
                    segment.speaker == "bot"
                ))

            # --- 4. Сохраняем полный JSON-дамп ---
            json_data = self._build_call_json(profile, transcript, history, call_id, client_id)
            json_str = json.dumps(json_data, ensure_ascii=False, indent=2)

            cursor.execute('''
                INSERT INTO jsons (call_id, client_id, timestamp, json_data)
                VALUES (?, ?, ?, ?)
            ''', (
                call_id,
                client_id,
                datetime.now().isoformat(),
                json_str
            ))

            conn.commit()
            logger.info(f"Звонок {call_id} успешно сохранён в базу.")

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Ошибка при сохранении звонка в базу: {e}", exc_info=True)
            raise RuntimeError(f"Ошибка сохранения звонка в базу: {str(e)}")

        finally:
            if conn:
                conn.close()

    def _build_call_json(self, profile: CallProfile, transcript: List[TranscriptSegment], history: List[Dict[str, str]], call_id: str, client_id: str) -> Dict[str, Any]:
        """
        Формирует полную структуру JSON для сохранения в таблицу jsons.
        Структура соответствует вашему шаблону из Google Docs.
        """
        # Извлекаем данные из профиля
        client_data = {
            "phone_number": profile.get("Телефон"),
            "name": profile.get("Имя клиента"),
            "object": profile.get("Объект", ""),
            "city": profile.get("Город") if profile.get("Город") and profile.get("Город") != "Нет данных" else None,
            "region": profile.get("client_region") if profile.get("client_region") else None,
            "inn": profile.get("ИНН") if profile.get("ИНН") else None,
            "company": profile.get("Организация") if profile.get("Организация") else None,
            "is_duplicate_city": profile.get("is_duplicate_city", False),
            "assigned_manager_id": profile.get("assigned_manager_id"),
            "last_call_summary": profile.last_call_summary if hasattr(profile, 'last_call_summary') else None,
            "comment": profile.get("Комментарии")
        }

        # Извлекаем запрос
        request_details = {
            "department": profile.get("Отдел"),
            "product_service": None,  # Будет заполнено из LLM или вручную
            "request_text": profile.get("Комментарии")
        }

        # Транскрипция
        transcription = []
        for i, segment in enumerate(transcript):
            transcription.append({
                "speaker": segment.speaker,
                "text": segment.text,
                "timestamp": segment.timestamp.strftime("%H:%M:%S")
            })

        # Действия
        action = {
            "next_step": "transfer",
            "target_department": profile.get("Отдел"),
            "manager_id": profile.get("assigned_manager_id")
        }

        # Метаданные
        metadata = {
            "is_repeat_call": profile.is_repeat_call,
            "call_history_id": [],
            "is_work_time": True,
            "sip_status": "answered",
            "llm_retry_count": 0,
            "fallback_triggered": False
        }

        return {
            "call_id": call_id,
            "client_id": client_id,
            "timestamp": datetime.now().isoformat(),
            "client_data": client_data,
            "request_details": request_details,
            "transcription": transcription,
            "action": action,
            "metadata": metadata
        }

    def find_client_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """
        Ищет клиента в базе по номеру телефона.
        Возвращает словарь с данными или None.

        Используется в dialog_manager.py для определения повторного звонка.
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            clean_phone = ''.join(filter(str.isdigit, str(phone)))
            if len(clean_phone) == 11 and clean_phone[0] == '8':
                clean_phone = '7' + clean_phone[1:]

            cursor.execute('SELECT * FROM clients_info WHERE phone = ?', (clean_phone,))
            row = cursor.fetchone()  # ← ✅ ЭТО ПРАВИЛЬНО! БЕЗ "row = "!

            if row:
                return dict(row)
            return None

        except Exception as e:
            logger.error(f"Ошибка при поиске клиента по телефону {phone}: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def update_client_profile(self, client_id: str, field: str, value: Any) -> bool:
        """
        Обновляет одно поле профиля клиента.
        Вызывается из dialog_manager.py через system_info.

        Пример: update_client_profile("uuid-123", "Имя клиента", "Александр")
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Карта полей
            field_map = {
                "Имя клиента": "name",
                "Телефон": "phone",
                "Город": "city_name",
                "ИНН": "inn",
                "Организация": "organization",
                "Комментарии": "comment",
                "Отдел": "department",
                "Объект": "object",
            }

            db_field = field_map.get(field)
            if not db_field:
                logger.warning(f"Поле '{field}' не найдено в карте обновлений.")
                return False

            cursor.execute(f"UPDATE clients_info SET {db_field} = ? WHERE client_id = ?", (value, client_id))
            conn.commit()

            if cursor.rowcount > 0:
                logger.info(f"Поле '{field}' для клиента {client_id} обновлено на '{value}'.")
                return True
            else:
                logger.warning(f"Клиент {client_id} не найден для обновления поля '{field}'.")
                return False

        except Exception as e:
            logger.error(f"Ошибка при обновлении поля '{field}' для клиента {client_id}: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def get_product_by_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает информацию о продукте по product_id.
        Используется для консультаций (в будущем, если LLM не найдёт в тексте).
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM products WHERE product_id = ?', (product_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

        except Exception as e:
            logger.error(f"Ошибка при получении продукта {product_id}: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def get_region_by_city(self, city: str) -> Optional[Dict[str, Any]]:
        """
        Находит регион по названию города (с учётом синонимов).
        Используется при заполнении профиля.
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            city_lower = city.lower().strip()

            # Поиск по city_name
            cursor.execute('SELECT * FROM regions_map WHERE LOWER(city_name) = ?', (city_lower,))
            row = cursor.fetchone()
            if row:
                return dict(row)

            # Поиск по aliases
            cursor.execute('SELECT * FROM regions_map WHERE aliases LIKE ?', (f'%{city_lower}%',))
            row = cursor.fetchone()
            if row:
                return dict(row)

            return None

        except Exception as e:
            logger.error(f"Ошибка при поиске региона по городу {city}: {e}")
            return None
        finally:
            if conn:
                conn.close()