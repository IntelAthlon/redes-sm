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
            sensor_id INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            temperatura REAL,
            presion REAL,
            humedad REAL,
            UNIQUE(sensor_id, timestamp)
        )
    ''')
    conex.commit()
    conex.close()

def insertar_medicion(json_crudo):
    try:
        # Decodificar JSON desde base64
        json_decodificado = base64.b64decode(json_crudo.encode('utf-8')).decode('utf-8')
        datos = json.loads(json_decodificado)
        assert "id" in datos and "timestamp" in datos # Validación

    except Exception as e:
        print("Error procesando paquete: ", e)
        return

    try:
        conex = sqlite3.connect(BASEDATOS)
        cursor = conex.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO mediciones (sensor_id, timestamp, temperatura, presion, humedad)
            VALUES (?, ?, ?, ?, ?)
        ''', (datos['id'], datos['timestamp'], datos['temperatura'], datos['presion'], datos['humedad']))
        conex.commit()

        if cursor.rowcount == 0:
            print("Dato duplicado ignorado: ", datos)
        else:
            print("Dato insertado: ", datos)

    except Exception as e:
        print("Error con base de datos:", e)

    finally:
        conex.close()

def obtener_mediciones():
    conex = sqlite3.connect(BASEDATOS)
    c = conex.cursor()
    c.execute('SELECT * FROM mediciones ORDER BY timestamp DESC')
    filas = c.fetchall()
    conex.close()
    return filas
