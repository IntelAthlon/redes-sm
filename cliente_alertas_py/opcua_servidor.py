from opcua import Server
from db import obtener_mediciones
import time
import base64
import json
def iniciar_opcua():
    server = Server()
    server.set_endpoint("opc.tcp://0.0.0.0:4840/")
    server.set_server_name("Servidor OPC UA IoT Industrial")

    namespace = server.register_namespace("http://iot-industrial.com")
    objeto_sensores = server.nodes.objects.add_object(namespace, "Sensores")

    # Variables dinámicas (estas se actualizarán periódicamente)
    temp_var = objeto_sensores.add_variable(namespace, "Temperatura", 0.0)
    pres_var = objeto_sensores.add_variable(namespace, "Presion", 0.0)
    hum_var = objeto_sensores.add_variable(namespace, "Humedad", 0.0)

    temp_var.set_writable()
    pres_var.set_writable()
    hum_var.set_writable()

    server.start()
    print("[~] Servidor OPC UA activo en puerto 4840...")

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

if __name__ == "__main__":
    iniciar_opcua()
