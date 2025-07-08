import base64
import socket
import struct
import threading
from datetime import datetime
import json
import queue
import time
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives import serialization

# CONFIGURACIÓN
PUERTO = 4000
SERVER_FINAL_IP = '192.168.0.40'
SERVER_FINAL_PUERTO = 5000

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

# Verificar firma paquetes
def verificar_firma(datos,firma,sensorId):
    try:
        with open(f"{sensorId}.pem", "rb") as archivo:
            clave_pub = serialization.load_pem_public_key(archivo.read())
        clave_pub.verify(
            firma,
            datos,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return True
    except Exception as e:
        print(f"firma invalida, error: {e}")
        return False

# Decodificar el struct sensordata
def parsear_datos_sensor(datos):
    id, timestamp_raw, temp, pres, hum = struct.unpack('<hQfff', datos)
    timestamp_string = str(timestamp_raw)
    try:
        fecha_hora = datetime.strptime(timestamp_string, "%Y%m%d%H%M%S")
    except ValueError:
        fecha_hora = 0
    return {
        "id": id,
        "timestamp": str(fecha_hora),
        "temperatura": temp,
        "presion": pres,
        "humedad": hum
    }

# Cargar clave privada una vez
with open("clave_intermedio.pem", "rb") as f:
    CLAVE_PRIVADA_INTERMEDIO = serialization.load_pem_private_key(f.read(), password=None)

def firmar_datos(datos):
    mensaje = json.dumps(datos, separators=(',', ':')).encode('utf-8')
    firma = CLAVE_PRIVADA_INTERMEDIO.sign(
        mensaje,
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    return {
        "datos": datos,
        "firma": base64.b64encode(firma).decode('utf-8')
    }

cola_envios = queue.Queue()

# Robustez en sistema: usar cola constante para que no se pierdan datos
def enviar_datos_cola():
    while True:
        try:
            datos = cola_envios.get(timeout=1)
        except queue.Empty:
            time.sleep(1)
            continue

        try:
            with socket.create_connection((SERVER_FINAL_IP, SERVER_FINAL_PUERTO), timeout=2) as s:
                paquete_firmado = firmar_datos(datos)
                paquete_final = json.dumps(paquete_firmado).encode('utf-8') + b'\n'
                s.sendall(paquete_final)
                print(f"Enviado desde cola: {datos}")
        except Exception as e:
            print(f"Error al enviar: {e}, devolviendo a cola")
            cola_envios.put(datos)
            time.sleep(5)  # evitar loop rápido si el servidor final está caído

# Atender una conexión TCP desde el cliente sensor
def recepcion_tcp(conex, dir):
    print(f"conexion desde {dir}")
    # 278 es tamaño exacto del paquete de datos + firma
    # 22 el struct
    # 256 firma
    try:
        paquete = b''
        while len(paquete) < 278:
            token = conex.recv((278) - len(paquete))
            if not token:
                break
            paquete += token

        if len(paquete) < 278:
            print("paquete incompleto!!!!")
            return

        datos = paquete[:22]
        firma = paquete[22:]
        parseado = parsear_datos_sensor(datos)

        if verificar_firma(datos, firma, parseado["id"]):
            print("Firma válida, encolando paquete")
            cola_envios.put(parseado)
        else:
            print("Firma invalida, datos descartados")

    except Exception as e:
        import traceback
        print(f"Error en conexion: {e}")
        traceback.print_exc()
    finally:
        conex.close()

# bucle principal del servidor intermedio
def servidor():
    print(f"escuchando en {obtener_ip_servidor()}:{PUERTO}...")
    threading.Thread(target=enviar_datos_cola, daemon=True).start()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((obtener_ip_servidor(), PUERTO))
        s.listen()
        while True:
            conex, dir = s.accept()
            threading.Thread(target=recepcion_tcp, args=(conex, dir), daemon=True).start()

if __name__ == "__main__":
    servidor()
