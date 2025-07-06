import sqlite3
import base64
import json
from datetime import datetime

DB_PATH = 'database.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS mediciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sensor_id INTEGER,
            timestamp TEXT,
            temperatura REAL,
            presion REAL,
            humedad REAL
        )
    ''')
    conn.commit()
    conn.close()

def insertar_medicion(encoded_json_str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO mediciones (sensor_id, timestamp, temperatura, presion, humedad)
        VALUES (?, datetime('now'), NULL, NULL, NULL)
    ''', (-1,))  # marcamos como temporal
    conn.commit()
    conn.close()

    # Luego actualizamos con JSON decodificado
    data = json.loads(base64.b64decode(encoded_json_str.encode('utf-8')).decode('utf-8'))
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE mediciones
        SET sensor_id=?, timestamp=?, temperatura=?, presion=?, humedad=?
        WHERE id=(SELECT MAX(id) FROM mediciones)
    ''', (data['id'], data['timestamp'], data['temperatura'], data['presion'], data['humedad']))
    conn.commit()
    conn.close()

def obtener_mediciones():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM mediciones ORDER BY timestamp DESC')
    rows = c.fetchall()
    conn.close()
    return rows
