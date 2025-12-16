import sqlite3

def update_trigger_safe():
    try:
        conn = sqlite3.connect('clients.db')
        cursor = conn.cursor()
        
        # Удаляем старый триггер
        cursor.execute("DROP TRIGGER IF EXISTS update_region_from_city")
        cursor.execute("DROP TRIGGER IF EXISTS update_region_on_update")
        
        # Создаём новый триггер с проверкой на JSON
        cursor.execute('''
            CREATE TRIGGER update_region_from_city
            AFTER INSERT ON clients_info
            FOR EACH ROW
            WHEN NEW.city_name IS NOT NULL AND NEW.city_name != ''
            BEGIN
                UPDATE clients_info 
                SET region_code = (
                    SELECT region_code FROM cities_map 
                    WHERE LOWER(NEW.city_name) = LOWER(city_name)
                       OR (
                           json_valid(aliases) 
                           AND EXISTS (
                               SELECT 1 FROM json_each(aliases) 
                               WHERE LOWER(value) = LOWER(NEW.city_name)
                           )
                       )
                    LIMIT 1
                ),
                region_name = (
                    SELECT region_name FROM cities_map 
                    WHERE LOWER(NEW.city_name) = LOWER(city_name)
                       OR (
                           json_valid(aliases) 
                           AND EXISTS (
                               SELECT 1 FROM json_each(aliases) 
                               WHERE LOWER(value) = LOWER(NEW.city_name)
                           )
                       )
                    LIMIT 1
                )
                WHERE client_id = NEW.client_id;
            END;
        ''')
        
        # Аналогично для UPDATE
        cursor.execute('''
            CREATE TRIGGER update_region_on_update
            AFTER UPDATE OF city_name ON clients_info
            FOR EACH ROW
            WHEN NEW.city_name IS NOT NULL AND NEW.city_name != ''
            BEGIN
                UPDATE clients_info 
                SET region_code = (
                    SELECT region_code FROM cities_map 
                    WHERE LOWER(NEW.city_name) = LOWER(city_name)
                       OR (
                           json_valid(aliases) 
                           AND EXISTS (
                               SELECT 1 FROM json_each(aliases) 
                               WHERE LOWER(value) = LOWER(NEW.city_name)
                           )
                       )
                    LIMIT 1
                ),
                region_name = (
                    SELECT region_name FROM cities_map 
                    WHERE LOWER(NEW.city_name) = LOWER(city_name)
                       OR (
                           json_valid(aliases) 
                           AND EXISTS (
                               SELECT 1 FROM json_each(aliases) 
                               WHERE LOWER(value) = LOWER(NEW.city_name)
                           )
                       )
                    LIMIT 1
                )
                WHERE client_id = NEW.client_id;
            END;
        ''')
        
        conn.commit()
        print("✅ Триггеры обновлены: теперь безопасно работают с JSON")
        
    except sqlite3.Error as e:
        print(f"❌ Ошибка: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    update_trigger_safe()