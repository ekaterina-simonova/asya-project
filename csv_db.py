import csv
import sqlite3

def load_cities_from_csv(csv_file_path):
    conn = None  # ← ВАЖНО: объявляем заранее
    try:
        print(f"Пытаюсь открыть файл: {csv_file_path}")
        
        with open(csv_file_path, 'r', encoding='utf-8-sig') as csvfile:  # ← utf-8-sig игнорирует BOM
            # Проверим первые строки файла
            first_lines = [next(csvfile) for _ in range(3)]
            print("Первые 3 строки файла:")
            for i, line in enumerate(first_lines):
                print(f"  {i+1}: {line.strip()}")
            
            csvfile.seek(0)
            reader = csv.DictReader(csvfile)
            
            print("Заголовки из CSV:", reader.fieldnames)
            
            # Проверим, есть ли city_name (учитываем BOM)
            city_name_field = None
            for field in reader.fieldnames:
                if 'city_name' in field:
                    city_name_field = field
                    break
            
            if not city_name_field:
                print("❌ В заголовках нет 'city_name'!")
                return
                
            # Подключение к БД
            conn = sqlite3.connect('clients.db')
            cursor = conn.cursor()
            cities_added = 0
            
            for row in reader:
                is_duplicate_str = row.get(city_name_field.replace('city_name', 'is_duplicate'), '0').strip().upper()
                is_duplicate = is_duplicate_str in ('1', 'TRUE')
                
                city_name = row.get(city_name_field, '')
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
                    aliases,
                    phone_route_code
                ))
                cities_added += 1
                
        conn.commit()
        print(f"Успешно загружено {cities_added} городов из файла {csv_file_path}")
        
    except FileNotFoundError:
        print(f"Файл {csv_file_path} не найден")
    except sqlite3.Error as e:
        print(f"Ошибка при работе с базой данных: {e}")
    except Exception as e:
        print(f"Ошибка при чтении CSV файла: {e}")
    finally:
        if conn:
            conn.close()

# === ВСТАВЬ ЭТО В КОНЕЦ ФАЙЛА ===
if __name__ == "__main__":
    # Убедись, что файл clients.db создан
    
    
    # Загружаем города из CSV
    load_cities_from_csv(r'C:\Users\Ekaterina.Simonova\Downloads\Ася\_Cities_maps_.csv')