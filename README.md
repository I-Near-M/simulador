# 🛰️ Sentinel-H2O: Simulador de Nodos Telemétricos de Campo

Este microservicio simula el comportamiento físico, químico, hidrodinámico y electrónico de las **6 estaciones de monitoreo** en la cuenca del Río Chancay-Huaral:

1. **`NODO-01-CABECERA`**: Lagunas Vichaycocha (Cuenca Alta / Puna - 4,350 msnm)
2. **`NODO-02-PACARAOS`**: Baños Termominerales Pacaraos (Cuenca Alta-Media - 2,800 msnm)
3. **`NODO-02-CONDUCCION`**: Conducción Central Acos - Santo Domingo (Cuenca Media - 1,250 msnm)
4. **`NODO-04-HUANDO`**: Fundo Huando (Valle Agrícola / Citrícola - 650 msnm)
5. **`NODO-03-PARCELA`**: Bocatoma Parcela Piloto Huayopampa (Parcela Piloto - 320 msnm)
6. **`NODO-06-PUERTO`**: Desembocadura Estuario Puerto de Chancay (Litoral - 15 msnm)

---

## 🌊 Características del Motor de Simulación

- **Inversión Electrónica Exacta**: Calcula los voltajes analógicos de hardware (pH $V_{ph}$, TDS $V_{tds}$, Turbidez $V_{turb}$, Distancia Ultrasónica) para que el backend de Sentinel-H2O aplique sus ecuaciones de calibración y obtenga exactamente las magnitudes físicas reales.
- **Ciclos Diurnos y Carga Solar**:
  - Variación sinusoidal de temperatura del agua ($T_{agua}$) y pH diurno (actividad fotosintética de microalgas).
  - Carga solar diurna de la batería Li-Ion (hasta 4.18V) y descarga nocturna paulatina (hasta ~3.75V).
- **Correlación Hidroambiental y Eventos Anómalos**:
  - En condiciones normales, los parámetros se mantienen estables en línea base con fluctuaciones estocásticas suaves ($1.5\%$).
  - Generación probabilística ($8\%$ de probabilidad por ciclo) de eventos hidrológicos reales:
    - 🌧️ **Avenidas Torrenciales / Lluvias / Huayco**: Aumento drástico de tirante y turbidez, dilución de sales (menor EC) y enfriamiento del agua.
    - 🍊 **Estrés Salino en Riego**: Alza de conductividad eléctrica (EC $> 1,600$ µS/cm) que dispara alertas tempranas para frutales.
    - ⛏️ **Descargas / Vertidos Químicos**: Variación anómala de pH ($<6.2$ o $>8.8$) con duración de 1 a 3 ciclos.
    - ☀️ **Estiaje Severo**: Caída del tirante al $35\%$ con concentración osmótica.

---

## 🚀 Despliegue en VPS o Servidor Remoto

### Opción A: Despliegue con Docker (Recomendado)

```bash
# 1. Crear carpeta o clonar repositorio independiente en tu VPS
mkdir -p ~/sentinel_simulator
cd ~/sentinel_simulator

# 2. Copiar los archivos de este directorio:
#    - Dockerfile
#    - docker-compose.yml
#    - simulator.py
#    - .env.example

# 3. Configurar el archivo .env
cp .env.example .env
nano .env   # Verificar que SENTINEL_API_URL apunte a tu API (ej. https://sentinel.mguillermo.com/api/v1)

# 4. Construir y levantar el contenedor
docker compose up -d --build

# 5. Ver logs de transmisión
docker compose logs -f
```

### Opción B: Ejecución nativa con Python 3 (Sin dependencias externas)

Este script utiliza únicamente la librería estándar de Python (`urllib`, `json`, `math`, `time`). No requiere `pip install`:

```bash
# 1. Copiar simulator.py y .env
python3 simulator.py
```

---

## ⚙️ Variables de Entorno Principales

| Variable | Descripción | Valor por Defecto |
| :--- | :--- | :--- |
| `SENTINEL_API_URL` | URL base de la API REST de Sentinel-H2O | `https://sentinel.mguillermo.com/api/v1` |
| `TELEMETRY_ENDPOINT` | Ruta del endpoint de ingesta | `/telemetry/` |
| `SEND_INTERVAL_SECONDS` | Intervalo de transmisión (segundos) | `600` (10 minutos) |
| `ANOMALY_PROBABILITY` | Probabilidad de disparo de eventos extremos | `0.08` (8%) |
| `AUTO_PROVISION_NODES` | Auto-registro de estaciones en backend | `true` |
| `LOG_LEVEL` | Detalle de logs (`INFO` o `DEBUG`) | `INFO` |
