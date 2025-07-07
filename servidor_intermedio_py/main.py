import socket
import struct
import threading
from datetime import datetime
import json
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization

# CONFIGURACIÓN
PUERTO = 4000
SERVER_FINAL_IP = '192.168.0.14'
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

# Atender una conexión TCP desde el cliente sensor
def recepcion_tcp(conex, ip):
    print(f"conexion desde {ip}")
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
            print(f"Firma valida")
            try:
                with socket.create_connection((SERVER_FINAL_IP, SERVER_FINAL_PUERTO), timeout=2) as s:
                    paquete_final = json.dumps(parseado).encode('utf-8') + b'\n'
                    s.sendall(paquete_final)
                    print(f"datos reenviados al servidor final: {parseado}")
            except Exception as e:
                print(f"no se pudo enviar al servidor final, error: {e}")
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
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((obtener_ip_servidor(), PUERTO))
        s.listen()
        while True:
            conn, addr = s.accept()
            threading.Thread(target=recepcion_tcp, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    servidor()
