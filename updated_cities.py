import csv
import sqlite3
import json

def update_cities_from_csv(csv_file_path):
    try:
        conn = sqlite3.connect('clients.db')
        cursor = conn.cursor()
        
        # 1. Очищаем таблицу
        cursor.execute("DELETE FROM cities_map")
        print("Таблица cities_map очищена")
        
        # 2. Загружаем новые данные
        with open(csv_file_path, 'r', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            cities_added = 0
            
            for row in reader:
                # Преобразование is_duplicate
                is_duplicate_str = row.get('is_duplicate', '0').strip().upper()
                is_duplicate = is_duplicate_str in ('1', 'TRUE')
                
                city_name = row.get('city_name', '')
                region_code = row.get('region_code', '')
                region_name = row.get('region_name', '')
                aliases = row.get('aliases', '').strip()
                phone_route_code = row.get('phone_route_code', '').strip()

                cursor.execute('''
                    INSERT INTO cities_map (
                        city_name, region_code, region_name, is_duplicate, aliases, phone_route_code
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    city_name,
                    region_code,
                    region_name,
                    is_duplicate,
                    aliases,  # JSON-строка
                    phone_route_code
                ))
                cities_added += 1
                
        conn.commit()
        print(f"✅ Успешно загружено {cities_added} городов")
        
    except FileNotFoundError:
        print(f"❌ Файл {csv_file_path} не найден")
    except sqlite3.Error as e:
        print(f"❌ Ошибка SQLite: {e}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    update_cities_from_csv(r'C:\Users\Ekaterina.Simonova\Downloads\Ася\_Cities_maps_.csv')  # Укажи путь к твоему исправленному CSV