import time
import uuid
import sys
import sqlite3

def test_generation_speed(n=100000):
    """Тест скорости генерации"""
    print(f"⏱️  Тест скорости генерации {n:,} ID:")
    
    # UUID
    start = time.time()
    uuid_ids = [str(uuid.uuid4()) for _ in range(n)]
    uuid_time = time.time() - start
    
    # Последовательные числа
    start = time.time()
    seq_ids = [str(i) for i in range(1, n + 1)]
    seq_time = time.time() - start
    
    print(f"  UUID: {uuid_time:.4f} секунд")
    print(f"  Числа: {seq_time:.4f} секунд")
    
    if seq_time > 0:
        print(f"  UUID медленнее в {uuid_time/seq_time:.1f} раз")
    else:
        print(f"  UUID медленнее (время чисел ≈ 0)")
    
    return uuid_ids, seq_ids

def test_memory_usage(uuid_ids, seq_ids):
    """Тест объёма памяти"""
    print("\n💾 Тест объёма памяти (на 1000 ID):")
    
    # Средний размер UUID
    uuid_size = sum(sys.getsizeof(uid) for uid in uuid_ids[:1000]) / 1000
    
    # Средний размер числа
    seq_size = sum(sys.getsizeof(sid) for sid in seq_ids[:1000]) / 1000
    
    print(f"  Средний размер UUID: {uuid_size:.1f} байт")
    print(f"  Средний размер числа: {seq_size:.1f} байт")
    
    if seq_size > 0:
        print(f"  UUID занимает в {uuid_size/seq_size:.1f} раз больше памяти")
    else:
        print("  UUID занимает больше памяти")

def test_uniqueness(uuid_ids, seq_ids):
    """Тест уникальности"""
    print("\n🔄 Тест уникальности:")
    
    # UUID
    uuid_unique = len(set(uuid_ids))
    uuid_duplicates = len(uuid_ids) - uuid_unique
    print(f"  UUID: {uuid_duplicates} дубликатов из {len(uuid_ids):,}")
    
    # Числа
    seq_unique = len(set(seq_ids))
    seq_duplicates = len(seq_ids) - seq_unique
    print(f"  Числа: {seq_duplicates} дубликатов из {len(seq_ids):,}")

def test_database_insert_speed(ids_list, id_type, limit=10000):
    """Тест скорости вставки в БД"""
    print(f"\n📥 Тест вставки в БД ({min(limit, len(ids_list)):,} записей):")
    
    try:
        # Используем in-memory DB для скорости
        conn = sqlite3.connect(':memory:')
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE test_calls (
                call_id TEXT PRIMARY KEY,
                timestamp TEXT,
                client_id TEXT
            )
        ''')
        
        start = time.time()
        for call_id in ids_list[:limit]:
            cursor.execute('''
                INSERT INTO test_calls (call_id, timestamp, client_id)
                VALUES (?, ?, ?)
            ''', (call_id, "2024-01-01 12:00:00", "client_123"))
        
        conn.commit()
        db_time = time.time() - start
        conn.close()
        
        print(f"  {id_type}: {db_time:.4f} секунд")
        return db_time
        
    except Exception as e:
        print(f"  Ошибка: {e}")
        return None

def test_predictability(seq_ids):
    """Тест предсказуемости"""
    print("\n🔮 Тест предсказуемости:")
    
    # Проверяем, насколько легко угадать следующее число
    sample = [int(x) for x in seq_ids[100:105]]
    print(f"  Пример последовательности: {sample}")
    print("  ⚠️  Числа легко предсказать!")
    
    # UUID - невозможно предсказать
    print("  ✅ UUID невозможно предсказать")

def main():
    print("🧪 ПОЛНЫЙ ТЕСТ ID ДЛЯ ЗВОНКОВ")
    print("=" * 50)
    
    n = 100000
    
    # 1. Скорость генерации
    uuid_ids, seq_ids = test_generation_speed(n)
    
    # 2. Память
    test_memory_usage(uuid_ids, seq_ids)
    
    # 3. Уникальность
    test_uniqueness(uuid_ids, seq_ids)
    
    # 4. Скорость вставки в БД
    uuid_db_time = test_database_insert_speed(uuid_ids, "UUID")
    seq_db_time = test_database_insert_speed(seq_ids, "Числа")
    
    if uuid_db_time is not None and seq_db_time is not None and seq_db_time > 0:
        print(f"\n  Вставка UUID медленнее в {uuid_db_time/seq_db_time:.1f} раз")
    
    # 5. Предсказуемость
    test_predictability(seq_ids)
    
    # 6. Вывод
    print("\n📋 ВЫВОД:")
    print("-" * 30)
    print("UUID:")
    print("  ✅ Уникальный, безопасный, распределённый")
    print("  ❌ Медленнее, больше памяти")
    
    print("\nЧисла:")
    print("  ✅ Быстрее, меньше памяти")
    print("  ⚠️  Нужен счётчик, предсказуемы")
    
    print("\n💡 РЕКОМЕНДАЦИЯ:")
    print("  Для распределённой системы — используй UUID")
    print("  Для одной базы с высокой нагрузкой — числа")

if __name__ == "__main__":
    main()