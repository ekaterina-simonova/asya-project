import sqlite3
import uuid

conn = sqlite3.connect('clients.db')
cursor = conn.cursor()

cursor.execute('''
    INSERT INTO clients_info (
        client_id, phone, name, city_name
    ) VALUES (?, ?, ?, ?)
''', (
    str(uuid.uuid4()),
    "+79991234563",
    "Тест Алиасович",
    "питер"  # ← это алиас!
))

conn.commit()
conn.close()