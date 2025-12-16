# create_database.py
import sqlite3
import uuid
from datetime import datetime

def create_tables():
    """Создает таблицы в базе данных SQLite."""
    try:
        # Подключение к базе данных (если файл не существует, он будет создан)
        conn = sqlite3.connect('clients.db')
        cursor = conn.cursor()

        # --- Таблица clients_info ---
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clients_info (
                client_id TEXT PRIMARY KEY, -- UUID stored as TEXT
                phone TEXT UNIQUE,
                name TEXT,
                city_name TEXT,
                region_code TEXT,
                region_name TEXT,
                inn TEXT,
                last_call_summary TEXT,
                call_summary_history TEXT,
                call_history TEXT, -- JSON stored as TEXT
                assigned_manager_id TEXT, -- UUID stored as TEXT
                assigned_manager_id1 TEXT, -- UUID stored as TEXT
                assigned_manager_id2 TEXT, -- UUID stored as TEXT
                object TEXT,
                organization TEXT,
                comment TEXT
            )
        ''')
        print("Таблица 'clients_info' создана или уже существует.")

        # --- Таблица cities_map ---
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cities_map (
                city_id INTEGER PRIMARY KEY AUTOINCREMENT,
                city_name TEXT,
                region_code TEXT,
                region_name TEXT,
                is_duplicate BOOLEAN,
                aliases TEXT, -- Можно хранить как CSV или JSON строку
                phone_route_code TEXT
            )
        ''')
        print("Таблица 'cities_map' создана или уже существует.")

        # --- Таблица calls ---
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS calls (
                call_id TEXT PRIMARY KEY, -- UUID stored as TEXT
                client_id TEXT, -- UUID stored as TEXT
                timestamp TEXT, -- TIMESTAMPTZ stored as TEXT (ISO format)
                department TEXT,
                product_service TEXT,
                request_text TEXT,
                next_step TEXT,
                target_department TEXT,
                manager_id TEXT, -- UUID stored as TEXT
                is_repeat_call BOOLEAN,
                is_work_time BOOLEAN,
                llm_retry_count INTEGER,
                sip_status TEXT,
                fallback_triggered BOOLEAN,
                FOREIGN KEY (client_id) REFERENCES clients_info(client_id)
                -- FOREIGN KEY (manager_id) REFERENCES managers(manager_id) -- Если таблица managers будет
            )
        ''')
        print("Таблица 'calls' создана или уже существует.")

        # --- Таблица call_transcripts ---
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS call_transcripts (
                call_id TEXT, -- UUID stored as TEXT
                client_id TEXT, -- UUID stored as TEXT
                speaker TEXT,
                text TEXT,
                segment_time TEXT, -- TIMESTAMPTZ stored as TEXT (ISO format)
                llm_response BOOLEAN,
                segment_id TEXT, -- TEXT, так как не указан конкретный тип
                FOREIGN KEY (call_id) REFERENCES calls(call_id),
                FOREIGN KEY (client_id) REFERENCES clients_info(client_id)
            )
        ''')
        print("Таблица 'call_transcripts' создана или уже существует.")

        # --- Таблица products ---
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                product_id INTEGER PRIMARY KEY AUTOINCREMENT,
                official_name TEXT,
                slang_name TEXT, -- Можно хранить как CSV или JSON строку
                department TEXT,
                is_archived BOOLEAN,
                weight_priority INTEGER,
                needs_clarification BOOLEAN,
                clarification_text TEXT
            )
        ''')
        print("Таблица 'products' создана или уже существует.")

        # --- Таблица jsons ---
        # Примечание: client_id в описании INTEGER, но в clients_info это TEXT (UUID).
        # Для согласованности используем TEXT.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jsons (
                call_id TEXT, -- TEXT, так как в описании указан TEXT
                client_id TEXT, -- Изменил на TEXT для согласованности с clients_info.client_id
                timestamp TEXT, -- DATETIME stored as TEXT (ISO format)
                json_data TEXT
            )
        ''')
        print("Таблица 'jsons' создана или уже существует.")

        # --- (Опционально) Таблица для менеджеров, если assigned_manager_id ссылается сюда ---
        # cursor.execute('''
        #     CREATE TABLE IF NOT EXISTS managers (
        #         manager_id TEXT PRIMARY KEY, -- UUID stored as TEXT
        #         manager_name TEXT
        #         -- Другие поля менеджера
        #     )
        # ''')
        # print("Таблица 'managers' создана или уже существует.")

        # Сохранение изменений и закрытие соединения
        conn.commit()
        print("\nВсе таблицы успешно созданы (если не существовали).")
        print("База данных 'clients.db' готова к использованию.")

    except sqlite3.Error as e:
        print(f"Ошибка при работе с базой данных SQLite: {e}")
    finally:
        if conn:
            conn.close()
            print("Соединение с базой данных закрыто.")

# --- Функция для добавления тестовых данных (опционально) ---
def insert_sample_data():
    """Добавляет несколько тестовых записей для проверки структуры."""
    try:
        conn = sqlite3.connect('clients.db')
        cursor = conn.cursor()

        # Добавление тестового клиента
        client_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO clients_info (
                client_id, phone, name, city_name, region_code, region_name, inn,
                last_call_summary, call_history, assigned_manager_id,
                assigned_manager_id1, assigned_manager_id2, object, organization, comment
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            client_id, "+79123456789", "Иван Иванов", "Москва", "RU-MOW", "Москва",
            "1234567890", "Позвонил уточнить наличие товара", '[]', # Пустой JSON массив
            None, None, None, "ул. Тестовая, д. 1", "ООО Ромашка", "Интересовался матами"
        ))

        # Добавление тестового города
        cursor.execute('''
            INSERT INTO cities_map (
                city_name, region_code, region_name, is_duplicate, aliases, phone_route_code
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', ("Москва", "RU-MOW", "Москва", False, "мск,moskva", "MOW_ROUTE"))

        # Добавление тестового продукта
        cursor.execute('''
            INSERT INTO products (
                official_name, slang_name, department, is_archived, weight_priority,
                needs_clarification, clarification_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            "Минеральная вата", "вата,маты", "Коммерческий", False, 10,
            False, ""
        ))

        conn.commit()
        print("Тестовые данные добавлены.")

    except sqlite3.Error as e:
        print(f"Ошибка при добавлении тестовых данных: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    create_tables()
    # Раскомментируйте следующую строку, если хотите добавить тестовые данные
    insert_sample_data()