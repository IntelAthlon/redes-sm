import threading
import time
import requests
from datetime import datetime
from flask import Flask, jsonify, render_template_string

# --- CONFIGURACIÓN ---
API_URL = "http://127.0.0.1:8000/api/mediciones"
TEMP_MIN, TEMP_MAX = 21.0, 29.0
PRES_MIN, PRES_MAX = 992.0, 1022.0
HUM_MIN, HUM_MAX = 35.0, 68.0
CONSULTA_INTERVALO = 10  # segundos

# --- ESTADO DE ALERTAS GLOBAL ---
alertas_activas = []
alertas_ids = set()

# --- LÓGICA DE ALERTA ---
def verificar_alertas(medicion):
    alertas = []
    if not (TEMP_MIN <= medicion["temperatura"] <= TEMP_MAX):
        alertas.append(f"[{medicion['timestamp']}] Sensor {medicion['sensor_id']} - Temperatura fuera de rango: {medicion['temperatura']} °C")

    if not (PRES_MIN <= medicion["presion"] <= PRES_MAX):
        alertas.append(f"[{medicion['timestamp']}] Sensor {medicion['sensor_id']} - Presión fuera de rango: {medicion['presion']} hPa")

    if not (HUM_MIN <= medicion["humedad"] <= HUM_MAX):
        alertas.append(f"[{medicion['timestamp']}] Sensor {medicion['sensor_id']} - Humedad fuera de rango: {medicion['humedad']} %")

    return alertas

def consultar_api():
    try:
        response = requests.get(API_URL, timeout=3)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[X] Error al consultar API: {e}")
        return []

def cliente_consulta():
    global alertas_activas, alertas_ids
    print("[~] Cliente de consulta corriendo...")
    while True:
        datos = consultar_api()
        nuevas_alertas = []

        for medicion in datos:
            clave = (medicion["sensor_id"], medicion["timestamp"])
            if clave not in alertas_ids:
                resultado = verificar_alertas(medicion)
                if resultado:
                    nuevas_alertas.extend(resultado)
                    alertas_ids.add(clave)

        if nuevas_alertas:
            print(f"\n--- ALERTAS NUEVAS ---")
            for a in nuevas_alertas:
                print(a)
            alertas_activas.extend(nuevas_alertas)

        time.sleep(CONSULTA_INTERVALO)

# --- SERVIDOR WEB ---
app = Flask(__name__)

@app.route('/')
def home():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dashboard IoT - Alertas y Métricas</title>
        <meta charset="utf-8">
        <style>
            body { font-family: sans-serif; background: #f4f4f4; padding: 20px; }
            h1, h2 { color: #2c3e50; }
            .alerta { background: #fff0f0; border: 1px solid #e74c3c; padding: 10px; margin-bottom: 10px; }
            .container { display: flex; flex-wrap: wrap; gap: 20px; }
            .panel { background: white; padding: 15px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); flex: 1; min-width: 300px; }
        </style>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body>
        <h1>📡 Dashboard IoT - Industrial</h1>

        <div class="container">
            <div class="panel">
                <h2>🔔 Alertas recientes</h2>
                <div id="alertas">Cargando alertas...</div>
            </div>

            <div class="panel">
                <h2>🌡️ Temperatura</h2>
                <canvas id="tempChart"></canvas>
            </div>

            <div class="panel">
                <h2>📈 Presión</h2>
                <canvas id="presChart"></canvas>
            </div>

            <div class="panel">
                <h2>💧 Humedad</h2>
                <canvas id="humChart"></canvas>
            </div>
        </div>

        <script>
            let tempChart, presChart, humChart;

            async function actualizarAlertas() {
                const res = await fetch('/api/alertas');
                const alertas = await res.json();
                const contenedor = document.getElementById('alertas');
                contenedor.innerHTML = '';
                alertas.slice().reverse().forEach(a => {
                    const div = document.createElement('div');
                    div.className = 'alerta';
                    div.innerText = a;
                    contenedor.appendChild(div);
                });
            }

            async function actualizarGraficas() {
                const res = await fetch('/api/ultimas_mediciones');
                const datos = await res.json();

                const labels = datos.map(d => "Sensor " + d.sensor_id);
                const temperaturas = datos.map(d => d.temperatura);
                const presiones = datos.map(d => d.presion);
                const humedades = datos.map(d => d.humedad);

                if (!tempChart) {
                    tempChart = new Chart(document.getElementById('tempChart'), {
                        type: 'bar',
                        data: {
                            labels: labels,
                            datasets: [{ label: 'Temperatura (°C)', data: temperaturas, backgroundColor: '#e67e22' }]
                        },
                        options: { responsive: true, scales: { y: { beginAtZero: true } } }
                    });
                } else {
                    tempChart.data.labels = labels;
                    tempChart.data.datasets[0].data = temperaturas;
                    tempChart.update();
                }

                if (!presChart) {
                    presChart = new Chart(document.getElementById('presChart'), {
                        type: 'bar',
                        data: {
                            labels: labels,
                            datasets: [{ label: 'Presión (hPa)', data: presiones, backgroundColor: '#2980b9' }]
                        },
                        options: { responsive: true, scales: { y: { beginAtZero: true } } }
                    });
                } else {
                    presChart.data.labels = labels;
                    presChart.data.datasets[0].data = presiones;
                    presChart.update();
                }

                if (!humChart) {
                    humChart = new Chart(document.getElementById('humChart'), {
                        type: 'bar',
                        data: {
                            labels: labels,
                            datasets: [{ label: 'Humedad (%)', data: humedades, backgroundColor: '#27ae60' }]
                        },
                        options: { responsive: true, scales: { y: { beginAtZero: true } } }
                    });
                } else {
                    humChart.data.labels = labels;
                    humChart.data.datasets[0].data = humedades;
                    humChart.update();
                }
            }

            setInterval(() => {
                actualizarAlertas();
                actualizarGraficas();
            }, 5000);

            window.onload = () => {
                actualizarAlertas();
                actualizarGraficas();
            }
        </script>
    </body>
    </html>
    """
    return render_template_string(html)

@app.route('/api/alertas')
def api_alertas():
    return jsonify(alertas_activas[-20:])  # últimas 20 alertas

@app.route('/api/ultimas_mediciones')
def api_ultimas_mediciones():
    datos = consultar_api()
    # Agrupa por sensor_id y toma la última medición por sensor
    sensores = {}
    for d in datos:
        sensores[d['sensor_id']] = d
    return jsonify(list(sensores.values()))

# --- EJECUCIÓN ---
if __name__ == "__main__":
    # Hilo para consultar la API en segundo plano
    threading.Thread(target=cliente_consulta, daemon=True).start()

    # Inicia servidor web Flask
    app.run(host="127.0.0.1", port=9000)

