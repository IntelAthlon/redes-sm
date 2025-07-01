# servidor_final/db.py
import sqlite3
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

def insertar_medicion(sensor):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO mediciones (sensor_id, timestamp, temperatura, presion, humedad)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        sensor['id'],
        sensor['timestamp'],
        sensor['temperatura'],
        sensor['presion'],
        sensor['humedad']
    ))
    conn.commit()
    conn.close()

def obtener_mediciones():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM mediciones ORDER BY timestamp DESC')
    rows = c.fetchall()
    conn.close()
    return rows
