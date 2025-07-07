from opcua import Server, ua
from db import obtener_mediciones
import time
import socket
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

def iniciar_opcua():
    server = Server()
    server.set_endpoint(f"opc.tcp://{obtener_ip_servidor()}:4840/")
    server.set_server_name("Servidor OPC UA")
    server.set_security_policy([ua.SecurityPolicyType.NoSecurity])

    namespace = server.register_namespace("http://proyectosemestral.com")
    objeto_sensores = server.nodes.objects.add_object(namespace, "Sensores")

    # Variables dinámicas (estas se actualizarán periódicamente)
    temp_var = objeto_sensores.add_variable(namespace, "Temperatura", 0.0)
    pres_var = objeto_sensores.add_variable(namespace, "Presion", 0.0)
    hum_var = objeto_sensores.add_variable(namespace, "Humedad", 0.0)

    server.start()

    try:
        while True:
            rows = obtener_mediciones()
            if rows:
                last = rows[-1]
                decoded = {
                    "temperatura": last[3],
                    "presion": last[4],
                    "humedad": last[5]
                }
                temp_var.set_value(decoded["temperatura"])
                pres_var.set_value(decoded["presion"])
                hum_var.set_value(decoded["humedad"])
            time.sleep(3)
    finally:
        server.stop()
