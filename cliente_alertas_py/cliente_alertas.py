import requests
import time
from datetime import datetime

# Umbrales de alerta
TEMP_MIN, TEMP_MAX = 21.0, 29.0
PRES_MIN, PRES_MAX = 992.0, 1022.0
HUM_MIN, HUM_MAX = 35.0, 68.0

API_URL = "http://127.0.0.1:8000/api/mediciones"

def verificar_alertas(medicion):
    alertas = []

    if not (TEMP_MIN <= medicion["temperatura"] <= TEMP_MAX):
        alertas.append(f"[ALERTA] Temperatura fuera de rango: {medicion['temperatura']} °C")

    if not (PRES_MIN <= medicion["presion"] <= PRES_MAX):
        alertas.append(f"[ALERTA] Presión fuera de rango: {medicion['presion']} hPa")

    if not (HUM_MIN <= medicion["humedad"] <= HUM_MAX):
        alertas.append(f"[ALERTA] Humedad fuera de rango: {medicion['humedad']} %")

    return alertas

def consultar_api():
    try:
        response = requests.get(API_URL, timeout=3)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[X] Error al consultar API: {e}")
        return []

def main():
    print("[~] Cliente de Consulta iniciado. Verificando datos cada 10 segundos...")
    ultimos_ids = set()

    while True:
        datos = consultar_api()

        for medicion in datos:
            clave = (medicion["sensor_id"], medicion["timestamp"])
            if clave not in ultimos_ids:
                alertas = verificar_alertas(medicion)
                if alertas:
                    print(f"\n--- ALERTAS [{datetime.now().isoformat()}] ---")
                    for alerta in alertas:
                        print(alerta)
                ultimos_ids.add(clave)

        time.sleep(10)

if __name__ == "__main__":
    main()
