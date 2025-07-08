import threading
import socket
import json
from flask import Flask, jsonify
from db import inicializar_db, insertar_medicion, obtener_mediciones
import base64
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from opcua_servidor import iniciar_opcua


# Obtener IP
# Código obtenido de stackoverflow, pregunta 166506
def obtener_ip_servidor():
    s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        s.connect(('10.254.254.254', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP
IP = obtener_ip_servidor()
PUERTO_RECEPCION = 5000
PUERTO_API = 8000
PUERTO_OPCUA = 4840

# Cargar clave pública del servidor intermedio
with open("pub_intermedio.pem", "rb") as f:
    CLAVE_PUB_INTERMEDIO = serialization.load_pem_public_key(f.read())

# Verificar firma paquete serv intermedio
def verificar_firma(mensaje, firma_cod):
    try:
        firma = base64.b64decode(firma_cod.encode('utf-8'))
        serializado = json.dumps(mensaje, separators=(',', ':')).encode('utf-8')
        CLAVE_PUB_INTERMEDIO.verify(
            signature=firma,
            data=serializado,
            padding=padding.PKCS1v15(),
            algorithm=hashes.SHA256()
        )
        return True
    except Exception as e:
        print(f"firma inválida, error: {e}")
        return False

# Inicializar base de datos
inicializar_db()

# Servidor TCP que recibe datos del intermediario
def servidor():
    print(f"Servidor final escuchando en {IP}:{PUERTO_RECEPCION} (TCP)")
    print(f"API funcionando en {IP}:{PUERTO_API}")
    print(f"Servidor OPC UA activo en {IP}:4840")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((IP, PUERTO_RECEPCION))
        s.listen()

        while True:
            conex,ip = s.accept()
            threading.Thread(target=recepcion_datos, args=(conex, ip), daemon=True).start()

def recepcion_datos(conex, ip):
    with conex:
        buffer = b""
        try:
            while True:
                data = conex.recv(1024)
                if not data:
                    break
                buffer += data
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    sensor_data = json.loads(line.decode('utf-8'))
                    datos = sensor_data.get("datos")
                    firma = sensor_data.get("firma")
                    if verificar_firma(datos, firma):
                        codificado = base64.b64encode(json.dumps(datos).encode('utf-8')).decode('utf-8')
                        insertar_medicion(codificado)
                        print(f"Medición almacenada desde sensor {sensor_data['id']}")
                    else:
                        print("Medición rechazada por firma de servidor inválida")
                    print(f"Servidor final escuchando en {IP}:{PUERTO_RECEPCION} (TCP)")
                    print(f"API funcionando en {IP}:{PUERTO_API}")
                    print(f"Servidor OPC UA activo en {IP}:4840")
        except Exception as e:
            print(f"Error procesando datos: {e}")


# API REST para consulta
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

# Lanzamiento de servidor socket y API REST
if __name__ == '__main__':
    threading.Thread(target=servidor, daemon=True).start()
    threading.Thread(target=iniciar_opcua, daemon=True).start()
    app.run(host=obtener_ip_servidor(), port=PUERTO_API)
