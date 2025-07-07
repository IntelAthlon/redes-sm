import sqlite3
import base64
import json
from datetime import datetime

BASEDATOS = 'database.db'

def inicializar_db():
    conex = sqlite3.connect(BASEDATOS)
    c = conex.cursor()
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
    conex.commit()
    conex.close()

def insertar_medicion(json_crudo):
    conex = sqlite3.connect(BASEDATOS)
    cursor = conex.cursor()
    cursor.execute('''
        INSERT INTO mediciones (sensor_id, timestamp, temperatura, presion, humedad)
        VALUES (?, datetime('now'), NULL, NULL, NULL)
    ''', (-1,))
    conex.commit()
    conex.close()

    data = json.loads(base64.b64decode(json_crudo.encode('utf-8')).decode('utf-8'))
    conex = sqlite3.connect(BASEDATOS)
    cursor = conex.cursor()
    cursor.execute('''
        UPDATE mediciones
        SET sensor_id=?, timestamp=?, temperatura=?, presion=?, humedad=?
        WHERE id=(SELECT MAX(id) FROM mediciones)
    ''', (data['id'], data['timestamp'], data['temperatura'], data['presion'], data['humedad']))
    conex.commit()
    conex.close()

def obtener_mediciones():
    conex = sqlite3.connect(BASEDATOS)
    c = conex.cursor()
    c.execute('SELECT * FROM mediciones ORDER BY timestamp DESC')
    filas = c.fetchall()
    conex.close()
    return filas
