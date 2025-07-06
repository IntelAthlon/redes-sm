import threading
import socket
import json
from flask import Flask, jsonify
from db import init_db, insertar_medicion, obtener_mediciones
import base64

# Inicializar base de datos
init_db()

# =========================
# Servidor TCP que recibe datos del intermediario
# =========================
def start_socket_server():
    IP = '127.0.0.1'
    PORT = 5000
    print(f"[~] Servidor final escuchando en {IP}:{PORT} (TCP)...")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((IP, PORT))
        s.listen()

        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_connection, args=(conn, addr), daemon=True).start()

def handle_connection(conn, addr):
    with conn:
        buffer = b""
        try:
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                buffer += data
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    sensor_data = json.loads(line.decode('utf-8'))
                    # Codifica el dict como JSON, luego a base64
                    encoded = base64.b64encode(json.dumps(sensor_data).encode('utf-8')).decode('utf-8')
                    insertar_medicion(encoded)
                    print(f"[✓] Medición almacenada desde sensor {sensor_data['id']}")
        except Exception as e:
            print(f"[X] Error procesando datos: {e}")


# =========================
# API REST para consulta
# =========================
app = Flask(__name__)

@app.route('/api/mediciones', methods=['GET'])
def api_mediciones():
    rows = obtener_mediciones()
    resultados = [
        {
            'id': r[0],
            'sensor_id': r[1],
            'timestamp': r[2],
            'temperatura': r[3],
            'presion': r[4],
            'humedad': r[5]
        }
        for r in rows
    ]
    return jsonify(resultados)

# =========================
# Lanzamiento de servidor socket y API REST
# =========================
if __name__ == '__main__':
    threading.Thread(target=start_socket_server, daemon=True).start()
    app.run(host='127.0.0.1', port=8000)
