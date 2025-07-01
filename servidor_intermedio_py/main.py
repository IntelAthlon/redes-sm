import socket
import struct
import threading
from datetime import datetime
import json
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization

# CONFIGURACIÓN
IP = '0.0.0.0'
PORT = 4000
PUBLIC_KEY_PATH = 'public.pem'

SERVER_FINAL_IP = '127.0.0.1'
SERVER_FINAL_PORT = 5000

DATA_SIZE = 22
SIG_SIZE = 256

# Cargar clave pública
def load_public_key(path):
    with open(path, "rb") as key_file:
        return serialization.load_pem_public_key(key_file.read())

public_key = load_public_key(PUBLIC_KEY_PATH)

# Verificar firma digital
def verify_signature(data: bytes, signature: bytes) -> bool:
    try:
        public_key.verify(
            signature,
            data,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return True
    except Exception as e:
        print(f"[!] Firma inválida: {e}")
        return False

# Decodificar SensorData
def parse_sensor_data(data: bytes):
    id, timestamp_raw, temp, pres, hum = struct.unpack('<hQfff', data)
    str_ts = str(timestamp_raw)
    try:
        fecha_hora = datetime.strptime(str_ts, "%Y%m%d%H%M%S")
    except ValueError:
        fecha_hora = "INVALID_TIMESTAMP"
    return {
        "id": id,
        "timestamp": str(fecha_hora),
        "temperatura": temp,
        "presion": pres,
        "humedad": hum
    }

# Enviar los datos ya decodificados al servidor final
def send_to_final_server(sensor_dict: dict):
    try:
        with socket.create_connection((SERVER_FINAL_IP, SERVER_FINAL_PORT), timeout=2) as s:
            payload = json.dumps(sensor_dict).encode('utf-8')
            s.sendall(payload)
            print(f"[→] Datos reenviados al servidor final: {sensor_dict}")
    except Exception as e:
        print(f"[X] No se pudo enviar al servidor final: {e}")

# Atender una conexión TCP desde el cliente sensor
def handle_client(conn, addr):
    print(f"[+] Conexión desde {addr}")
    try:
        packet = conn.recv(DATA_SIZE + SIG_SIZE)
        if len(packet) < DATA_SIZE + SIG_SIZE:
            print("[!] Paquete incompleto")
            return

        data = packet[:DATA_SIZE]
        signature = packet[DATA_SIZE:]

        if verify_signature(data, signature):
            parsed = parse_sensor_data(data)
            send_to_final_server(parsed)  # 👈 Reenvío real
        else:
            print("[X] Firma inválida, datos descartados.")
    except Exception as e:
        print(f"[!] Error en conexión: {e}")
    finally:
        conn.close()

# Bucle principal del servidor intermedio
def start_server():
    print(f"[~] Escuchando en {IP}:{PORT}...")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((IP, PORT))
        s.listen()

        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    start_server()
