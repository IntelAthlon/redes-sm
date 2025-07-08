from datetime import datetime as dt
# datetime tiene un conflicto de nombre con si mismo? lol
import threading
import time
import requests
import socket
import json
import os
from flask import Flask, jsonify, render_template_string

# --- CARGA DE CONFIGURACIÓN ---
CONFIG_PATH = "config.json"

if not os.path.exists(CONFIG_PATH):
    raise FileNotFoundError(f"Archivo de configuración no encontrado: {CONFIG_PATH}")

with open(CONFIG_PATH, "r") as f:
    config = json.load(f)

# --- CONFIGURACIÓN ---
API_URL = config["API_URL"]
TEMP_MIN = config["TEMP_MIN"]
TEMP_MAX = config["TEMP_MAX"]
PRES_MIN = config["PRES_MIN"]
PRES_MAX = config["PRES_MAX"]
HUM_MIN = config["HUM_MIN"]
HUM_MAX = config["HUM_MAX"]
CONSULTA_INTERVALO = config["CONSULTA_INTERVALO"]

# --- ESTADO DE ALERTAS GLOBAL ---
alertas_activas = []
alertas_ids = set()

# --- OBTENER IP ---
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
            alertas_activas.extend(nuevas_alertas)

        time.sleep(CONSULTA_INTERVALO)
        print(f"Cliente disponible en {obtener_ip_servidor()}:9000")

# --- SERVIDOR WEB ---
app = Flask(__name__)

@app.route('/')
def home():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dashboard IoT Tiempo Real</title>
        <meta charset="utf-8">
        <style>
            body { font-family: sans-serif; background: #f4f4f4; padding: 20px; }
            h1, h2 { color: #2c3e50; }
            #alertas { overflow-y: scroll; height: 400px; }
            .alerta { background: #fff0f0; border: 1px solid #e74c3c; padding: 10px; margin-bottom: 10px; }
            .container { display: flex; flex-wrap: wrap; gap: 20px; }
            .panel { background: white; padding: 15px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); flex: 1; min-width: 300px; }
        </style>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body>
        <h1>📡 Dashboard Sensores</h1>

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
            
            <div class="panel" style="width: 100%;">
                <h2>📋 Historial de Mediciones</h2> <button onclick="cargarTabla()">Actualizar</button>
                <table id="tabla" border="1" cellpadding="6" style="border-collapse: collapse; width: 100%; background: white;">
                    <thead>
                        <tr>
                            <th>Sensor ID</th>
                            <th>Timestamp</th>
                            <th>Temperatura (°C)</th>
                            <th>Presión (hPa)</th>
                            <th>Humedad (%)</th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
                <div style="margin-top: 10px;">
                    <button onclick="paginaAnterior()">Anterior</button>
                    <span id="paginaActual">1</span>
                    <button onclick="paginaSiguiente()">Siguiente</button>
                </div>
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
            
            let datosTabla = [];
            let pagina = 1;
            const porPagina = 10;
            
            async function cargarTabla() {
                const res = await fetch('/api/tabla_mediciones');
                datosTabla = await res.json();
                renderizarTabla();
            }
            
            function renderizarTabla() {
                const tbody = document.querySelector("#tabla tbody");
                tbody.innerHTML = '';
            
                const inicio = (pagina - 1) * porPagina;
                const fin = inicio + porPagina;
                const paginaDatos = datosTabla.slice(inicio, fin);
            
                for (const fila of paginaDatos) {
                    const tr = document.createElement("tr");
                    tr.innerHTML = `
                        <td>${fila.sensor_id}</td>
                        <td>${fila.timestamp}</td>
                        <td>${fila.temperatura}</td>
                        <td>${fila.presion}</td>
                        <td>${fila.humedad}</td>
                    `;
                    tbody.appendChild(tr);
                }
            
                document.getElementById("paginaActual").innerText = pagina;
            }
            
            function paginaSiguiente() {
                if ((pagina * porPagina) < datosTabla.length) {
                    pagina++;
                    renderizarTabla();
                }
            }
            
            function paginaAnterior() {
                if (pagina > 1) {
                    pagina--;
                    renderizarTabla();
                }
            }

            window.onload = () => {
                actualizarAlertas();
                actualizarGraficas();
                cargarTabla();
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

    sensores = {}
    ahora = dt.now()

    for d in datos:
        ts = dt.strptime(d['timestamp'], "%Y-%m-%d %H:%M:%S")
        # Filtrar por sensores activos, 30s espera
        if (ahora-ts).total_seconds()<=30:
            sensores[d['sensor_id']] = d

    return jsonify(list(sensores.values()))

@app.route('/api/tabla_mediciones')
def api_tabla_mediciones():
    # Devuelve todos los datos sin filtrar por tiempo ni sensores activos
    datos = consultar_api()
    # Ordena por timestamp descendente (más recientes primero)
    datos_ordenados = sorted(datos, key=lambda x: x['timestamp'], reverse=True)
    return jsonify(datos_ordenados)

# --- EJECUCIÓN ---
if __name__ == "__main__":

    # Hilo para consultar la API en segundo plano
    threading.Thread(target=cliente_consulta, daemon=True).start()

    # Inicia servidor web Flask
    app.run(host=obtener_ip_servidor(), port=9000)

