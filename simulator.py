#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SENTINEL-H2O - SIMULADOR DINÁMICO DE NODOS TELEMÉTRICOS DE CAMPO
================================================================================
Simula el comportamiento físico, electroquímico e hidrodinámico de las 6
estaciones de monitoreo en la cuenca del Río Chancay-Huaral.

Emula el envío continuo de telemetría hacia la API REST de Sentinel-H2O
con ciclos diurnos/nocturnos, correlación física de variables, carga solar de
batería y generación probabilística de eventos extremos o anómalos.
================================================================================
"""

import os
import sys
import time
import math
import random
import signal
import logging
import datetime
import json
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional, Tuple

# Cargar variables de entorno simples desde .env si existe (sin requerir python-dotenv obligatorio)
def load_simple_env(env_path: str = ".env"):
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k not in os.environ:
                            os.environ[k] = v
        except Exception as e:
            print(f"Aviso leyendo .env: {e}")

load_simple_env()

# ============================================================================
# CONFIGURACIÓN GENERAL DEL SERVICIO
# ============================================================================
API_BASE_URL = os.getenv("SENTINEL_API_URL", "http://localhost:8000/api/v1").rstrip("/")
TELEMETRY_ENDPOINT = os.getenv("TELEMETRY_ENDPOINT", "/telemetry/")
SEND_INTERVAL_SECONDS = int(os.getenv("SEND_INTERVAL_SECONDS", "600"))  # 10 min por defecto
MASTER_API_KEY = os.getenv("MASTER_API_KEY", "sentinel_master_key_chancay_2026_secure")
AUTO_PROVISION_NODES = os.getenv("AUTO_PROVISION_NODES", "true").lower() in ("true", "1", "yes")
ANOMALY_PROBABILITY = float(os.getenv("ANOMALY_PROBABILITY", "0.08"))  # 8% prob de evento por ciclo
JITTER_RATIO = float(os.getenv("STATION_JITTER_RATIO", "0.015"))       # 1.5% ruido gaussiano
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("SentinelSimulator")

# ============================================================================
# PERFILES HIDROAMBIENTALES DE LAS 6 ESTACIONES DE LA CUENCA CHANCAY-HUARAL
# ============================================================================
STATIONS_PROFILES: List[Dict[str, Any]] = [
    {
        "id_nodo": "NODO-01-CABECERA",
        "nombre": "Estación Cabecera Lagunas Vichaycocha",
        "api_key": os.getenv("API_KEY_NODO_01", "hash_key_cabecera_secure_01"),
        "sector": "CUENCA_ALTA",
        "subcuenca": "Vichaycocha",
        "cota_msnm": 4350.0,
        "lat": -11.0254,
        "lon": -76.5123,
        "base_temp_c": 9.5,
        "temp_amp_c": 2.8,
        "base_ph": 7.45,
        "base_ec_us_cm": 220.0,
        "base_tds_ppm": 110.0,
        "base_turb_ntu": 3.5,
        "fondo_sensor_cm": 150.0,
        "base_tirante_cm": 55.0,
        "caudal_k": 1.45,
        "caudal_n": 1.60,
        "avg_rssi": 22,
        "tipo_fuente": "LAGUNA_REPRESADA"
    },
    {
        "id_nodo": "NODO-02-PACARAOS",
        "nombre": "Estación Aguas Termominerales Pacaraos",
        "api_key": os.getenv("API_KEY_NODO_02", "hash_key_pacaraos_secure_02"),
        "sector": "CUENCA_ALTA_MEDIA",
        "subcuenca": "Pacaraos",
        "cota_msnm": 2800.0,
        "lat": -11.1520,
        "lon": -76.6830,
        "base_temp_c": 14.0,
        "temp_amp_c": 2.5,
        "base_ph": 7.30,
        "base_ec_us_cm": 560.0,
        "base_tds_ppm": 280.0,
        "base_turb_ntu": 8.0,
        "fondo_sensor_cm": 180.0,
        "base_tirante_cm": 65.0,
        "caudal_k": 1.80,
        "caudal_n": 1.55,
        "avg_rssi": 19,
        "tipo_fuente": "RIO_PRINCIPAL"
    },
    {
        "id_nodo": "NODO-02-CONDUCCION",
        "nombre": "Estación Conducción Central Acos - Santo Domingo",
        "api_key": os.getenv("API_KEY_NODO_03", "hash_key_conduccion_secure_02"),
        "sector": "CUENCA_MEDIA",
        "subcuenca": "Acos",
        "cota_msnm": 1250.0,
        "lat": -11.2789,
        "lon": -76.8241,
        "base_temp_c": 17.5,
        "temp_amp_c": 3.0,
        "base_ph": 7.60,
        "base_ec_us_cm": 780.0,
        "base_tds_ppm": 390.0,
        "base_turb_ntu": 18.0,
        "fondo_sensor_cm": 200.0,
        "base_tirante_cm": 80.0,
        "caudal_k": 2.10,
        "caudal_n": 1.55,
        "avg_rssi": 24,
        "tipo_fuente": "RIO_PRINCIPAL"
    },
    {
        "id_nodo": "NODO-04-HUANDO",
        "nombre": "Estación Agrícola Fundo Huando",
        "api_key": os.getenv("API_KEY_NODO_04", "hash_key_huando_secure_04"),
        "sector": "CUENCA_MEDIA_BAJA",
        "subcuenca": "Huando",
        "cota_msnm": 650.0,
        "lat": -11.4120,
        "lon": -76.9530,
        "base_temp_c": 20.5,
        "temp_amp_c": 3.2,
        "base_ph": 7.80,
        "base_ec_us_cm": 1100.0,
        "base_tds_ppm": 550.0,
        "base_turb_ntu": 28.0,
        "fondo_sensor_cm": 160.0,
        "base_tirante_cm": 50.0,
        "caudal_k": 1.20,
        "caudal_n": 1.50,
        "avg_rssi": 28,
        "tipo_fuente": "CANAL_DERIVACION"
    },
    {
        "id_nodo": "NODO-03-PARCELA",
        "nombre": "Estación Bocatoma Parcela Piloto Huayopampa",
        "api_key": os.getenv("API_KEY_NODO_05", "hash_key_parcela_secure_03"),
        "sector": "PARCELA_PILOTO",
        "subcuenca": "Añasmayo",
        "cota_msnm": 320.0,
        "lat": -11.4521,
        "lon": -77.0145,
        "base_temp_c": 21.8,
        "temp_amp_c": 3.0,
        "base_ph": 7.88,
        "base_ec_us_cm": 1260.0,
        "base_tds_ppm": 630.0,
        "base_turb_ntu": 35.0,
        "fondo_sensor_cm": 100.0,
        "base_tirante_cm": 42.0,
        "caudal_k": 0.85,
        "caudal_n": 1.50,
        "avg_rssi": 25,
        "tipo_fuente": "BOCATOMA_PARCELA"
    },
    {
        "id_nodo": "NODO-06-PUERTO",
        "nombre": "Estación Estuario Puerto de Chancay",
        "api_key": os.getenv("API_KEY_NODO_06", "hash_key_puerto_secure_06"),
        "sector": "CUENCA_BAJA_LITORAL",
        "subcuenca": "Litoral",
        "cota_msnm": 15.0,
        "lat": -11.5640,
        "lon": -77.2680,
        "base_temp_c": 22.5,
        "temp_amp_c": 2.8,
        "base_ph": 8.12,
        "base_ec_us_cm": 1750.0,
        "base_tds_ppm": 875.0,
        "base_turb_ntu": 48.0,
        "fondo_sensor_cm": 250.0,
        "base_tirante_cm": 95.0,
        "caudal_k": 2.40,
        "caudal_n": 1.58,
        "avg_rssi": 29,
        "tipo_fuente": "ESTUARIO_DESEMBOCADURA"
    }
]

# ============================================================================
# MOTOR DE INVERSIÓN FÍSICA Y ELECTRÓNICA DE SENSORES
# ============================================================================
class SensorVoltageConverter:
    @staticmethod
    def ph_to_voltage(ph_target: float, offset_v: float = 2.50, slope: float = -0.18) -> float:
        v = offset_v + slope * (ph_target - 7.0)
        return round(max(0.0, min(3.30, v)), 3)

    @staticmethod
    def tds_to_voltage(tds_target_ppm: float, temp_c: float) -> float:
        coef_termico = 1.0 + 0.02 * (temp_c - 25.0)
        if coef_termico <= 0.1:
            coef_termico = 0.1
        tds_raw_target = max(0.0, tds_target_ppm * coef_termico)

        low_v = 0.0
        high_v = 3.30
        for _ in range(24):
            mid_v = (low_v + high_v) / 2.0
            calc_tds = 0.5 * (133.42 * (mid_v ** 3) - 255.86 * (mid_v ** 2) + 857.39 * mid_v)
            if calc_tds < tds_raw_target:
                low_v = mid_v
            else:
                high_v = mid_v
        return round(max(0.0, min(3.30, (low_v + high_v) / 2.0)), 3)

    @staticmethod
    def turb_to_voltage(ntu_target: float, v_clear: float = 4.20, v_turbid: float = 2.50, divider: float = 1.5) -> float:
        ntu_clamped = max(0.5, min(3000.0, ntu_target))
        if ntu_clamped <= 0.5:
            v_sensor = v_clear
        else:
            frac = (ntu_clamped / 3000.0) ** (1.0 / 1.3)
            frac = min(1.0, max(0.0, frac))
            v_sensor = v_clear - frac * (v_clear - v_turbid)
        
        raw_v = v_sensor / divider
        return round(max(0.0, min(3.30, raw_v)), 3)

    @staticmethod
    def tirante_to_distance(tirante_cm: float, fondo_cm: float) -> float:
        raw_dist = fondo_cm - tirante_cm
        return round(max(5.0, raw_dist), 2)


# ============================================================================
# CLIENTE HTTP RESILIENTE
# ============================================================================
class HttpClient:
    @staticmethod
    def post(url: str, payload: dict, timeout: int = 12) -> Tuple[int, Optional[dict], str]:
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Sentinel-H2O-NodeSimulator/2.0 (Huancayo-Chancay)"
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status_code = resp.status
                body = resp.read().decode("utf-8")
                try:
                    return status_code, json.loads(body), body
                except Exception:
                    return status_code, None, body
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8") if e.fp else str(e)
            try:
                return e.code, json.loads(body), body
            except Exception:
                return e.code, None, body
        except Exception as e:
            return 0, None, str(e)

    @staticmethod
    def get(url: str, timeout: int = 10) -> Tuple[int, Optional[dict], str]:
        req = urllib.request.Request(
            url,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Sentinel-H2O-NodeSimulator/2.0 (Huancayo-Chancay)"
            },
            method="GET"
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status_code = resp.status
                body = resp.read().decode("utf-8")
                try:
                    return status_code, json.loads(body), body
                except Exception:
                    return status_code, None, body
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8") if e.fp else str(e)
            try:
                return e.code, json.loads(body), body
            except Exception:
                return e.code, None, body
        except Exception as e:
            return 0, None, str(e)


# ============================================================================
# GESTOR DE ESTADO Y EVENTOS DINÁMICOS
# ============================================================================
class DynamicChancaySimulator:
    def __init__(self):
        self.running = True
        self.uptime_start = time.time()
        self.active_events: Dict[str, Dict[str, Any]] = {}
        self.battery_levels: Dict[str, float] = {
            st["id_nodo"]: random.uniform(3.92, 4.12) for st in STATIONS_PROFILES
        }

    def stop(self, *args):
        logger.info("Recibida señal de detención. Cerrando simulador...")
        self.running = False

    def get_diurnal_factor(self) -> float:
        now = datetime.datetime.now()
        hour_fraction = now.hour + now.minute / 60.0
        angle = (hour_fraction - 14.5) * (2 * math.pi / 24.0)
        return math.cos(angle)

    def update_battery(self, id_nodo: str, diurnal_factor: float) -> float:
        current_v = self.battery_levels.get(id_nodo, 4.0)
        if diurnal_factor > 0:
            delta_v = (4.18 - current_v) * 0.05 * diurnal_factor
        else:
            delta_v = -0.015 * abs(diurnal_factor)
        
        current_v += delta_v + random.uniform(-0.005, 0.005)
        current_v = max(3.55, min(4.20, current_v))
        self.battery_levels[id_nodo] = round(current_v, 2)
        return self.battery_levels[id_nodo]

    def check_and_trigger_events(self):
        expired_events = []
        for id_nodo, evt in self.active_events.items():
            evt["remaining_cycles"] -= 1
            if evt["remaining_cycles"] <= 0:
                expired_events.append(id_nodo)
        
        for id_nodo in expired_events:
            logger.info(f"[EVENTO_FIN] Evento '{self.active_events[id_nodo]['tipo']}' finalizado en {id_nodo}. Retornando a línea base.")
            del self.active_events[id_nodo]

        if random.random() < ANOMALY_PROBABILITY:
            target_station = random.choice(STATIONS_PROFILES)
            id_nodo = target_station["id_nodo"]
            if id_nodo not in self.active_events:
                event_types = [
                    "LLUVIA_TORRENCIAL_AVENIDA",
                    "ESTRES_SALINO_RIEGO",
                    "VERTIDO_ACIDO_MINERO",
                    "DESCARGA_ALCALINA",
                    "ESTIAJE_BAJO_CAUDAL"
                ]
                
                if target_station["sector"] in ("CUENCA_ALTA", "CUENCA_ALTA_MEDIA"):
                    evt_type = random.choice(["LLUVIA_TORRENCIAL_AVENIDA", "VERTIDO_ACIDO_MINERO", "LLUVIA_TORRENCIAL_AVENIDA"])
                elif target_station["sector"] in ("CUENCA_MEDIA_BAJA", "PARCELA_PILOTO"):
                    evt_type = random.choice(["ESTRES_SALINO_RIEGO", "DESCARGA_ALCALINA", "ESTIAJE_BAJO_CAUDAL"])
                else:
                    evt_type = random.choice(event_types)

                cycles = random.randint(1, 3)
                self.active_events[id_nodo] = {
                    "tipo": evt_type,
                    "remaining_cycles": cycles,
                    "intensity": random.uniform(1.2, 1.8)
                }
                logger.warning(f"[EVENTO_INICIO] ⚠️ Se ha detonado evento '{evt_type}' en {id_nodo} ({target_station['nombre']}) por {cycles} ciclo(s).")

    def compute_station_telemetry(self, station: Dict[str, Any]) -> Dict[str, Any]:
        id_nodo = station["id_nodo"]
        diurnal = self.get_diurnal_factor()

        temp_c = station["base_temp_c"] + (station["temp_amp_c"] * diurnal) + random.gauss(0, 0.3)
        temp_c = round(temp_c, 2)

        ph = station["base_ph"] + (0.10 * diurnal) + random.gauss(0, 0.04)
        tirante_cm = station["base_tirante_cm"] * (1.0 + random.gauss(0, JITTER_RATIO))
        ec_us_cm = station["base_ec_us_cm"] * (1.0 + random.gauss(0, JITTER_RATIO))
        turb_ntu = station["base_turb_ntu"] * (1.0 + abs(random.gauss(0, JITTER_RATIO * 2)))

        if id_nodo in self.active_events:
            evt = self.active_events[id_nodo]
            tipo = evt["tipo"]
            intensity = evt["intensity"]

            if tipo == "LLUVIA_TORRENCIAL_AVENIDA":
                tirante_cm *= (1.8 * intensity)
                turb_ntu = (turb_ntu * 8.0 * intensity) + random.uniform(60, 180)
                ec_us_cm *= 0.65
                temp_c -= 2.0
            elif tipo == "ESTRES_SALINO_RIEGO":
                ec_us_cm = max(1600.0, ec_us_cm * 1.55 * intensity)
                ph += 0.3
            elif tipo == "VERTIDO_ACIDO_MINERO":
                ph = random.uniform(5.4, 6.2)
                turb_ntu += random.uniform(30, 80)
                ec_us_cm *= 1.30
            elif tipo == "DESCARGA_ALCALINA":
                ph = random.uniform(8.7, 9.3)
                ec_us_cm *= 1.25
            elif tipo == "ESTIAJE_BAJO_CAUDAL":
                tirante_cm = max(8.0, tirante_cm * 0.35)
                ec_us_cm *= 1.25
                temp_c += 1.8

        ph = round(max(4.0, min(10.5, ph)), 2)
        tirante_cm = round(max(2.0, min(station["fondo_sensor_cm"] - 10.0, tirante_cm)), 2)
        ec_us_cm = round(max(50.0, min(5000.0, ec_us_cm)), 2)
        tds_ppm = round(ec_us_cm * 0.50, 2)
        turb_ntu = round(max(0.5, min(2800.0, turb_ntu)), 2)

        raw_v_ph = SensorVoltageConverter.ph_to_voltage(ph)
        raw_v_tds = SensorVoltageConverter.tds_to_voltage(tds_ppm, temp_c)
        raw_v_turb = SensorVoltageConverter.turb_to_voltage(turb_ntu)
        raw_dist_cm = SensorVoltageConverter.tirante_to_distance(tirante_cm, station["fondo_sensor_cm"])

        battery_v = self.update_battery(id_nodo, diurnal)
        signal_rssi = max(10, min(31, int(station["avg_rssi"] + random.randint(-2, 2))))

        uptime_ms = int((time.time() - self.uptime_start) * 1000)

        payload = {
            "node_id": station["id_nodo"],
            "api_key": station["api_key"],
            "battery_v": battery_v,
            "signal_rssi": signal_rssi,
            "temp_c": temp_c,
            "raw_dist_cm": raw_dist_cm,
            "raw_v_ph": raw_v_ph,
            "raw_v_tds": raw_v_tds,
            "raw_v_turb": raw_v_turb,
            "timestamp_ms": uptime_ms
        }

        return payload

    def send_telemetry_for_station(self, station: Dict[str, Any]) -> bool:
        payload = self.compute_station_telemetry(station)
        id_nodo = station["id_nodo"]
        url = f"{API_BASE_URL}{TELEMETRY_ENDPOINT}"

        status_code, data, text = HttpClient.post(url, payload, timeout=12)
        if status_code == 201 and data:
            alerta_tag = "🚨 [ALERTA DISPARADA]" if data.get("alerta_disparada") else "✅ [NORMAL]"
            logger.info(
                f"{alerta_tag} [{id_nodo}] "
                f"pH={data.get('ph')} | EC={data.get('ec_us_cm')}uS/cm | "
                f"Turb={data.get('turbidez_ntu')}NTU | Tirante={data.get('tirante_agua_cm')}cm | "
                f"Q={data.get('caudal_ls')}L/s | WQI={data.get('wqi_score')} ({data.get('wqi_categoria')}) | "
                f"Bat={payload['battery_v']}V (CSQ {payload['signal_rssi']})"
            )
            return True
        elif status_code in (401, 404):
            logger.error(f"❌ [{id_nodo}] Error de Autenticación/Registro ({status_code}): {text}")
            return False
        else:
            logger.warning(f"⚠️ [{id_nodo}] Respuesta ({status_code}): {text}")
            return False

    def auto_provision_if_needed(self):
        if not AUTO_PROVISION_NODES:
            return

        logger.info("Comprobando registro de nodos en la plataforma Sentinel-H2O...")
        try:
            nodes_url = f"{API_BASE_URL}/nodes/"
            status_code, data, text = HttpClient.get(nodes_url, timeout=10)
            existing_ids = set()
            if status_code == 200 and isinstance(data, list):
                existing_ids = {n.get("id_nodo") for n in data if isinstance(n, dict)}
            
            for st in STATIONS_PROFILES:
                if st["id_nodo"] not in existing_ids:
                    logger.info(f"Provisionando nodo faltante '{st['id_nodo']}' ({st['nombre']})...")
                    prov_url = f"{API_BASE_URL}/nodes/provision"
                    prov_payload = {
                        "id_nodo": st["id_nodo"],
                        "nombre": st["nombre"],
                        "sector_cuenca": st["sector"],
                        "subcuenca": st["subcuenca"],
                        "latitud": st["lat"],
                        "longitud": st["lon"],
                        "cota_msnm": st["cota_msnm"],
                        "tipo_fuente": st["tipo_fuente"],
                        "intervalo_envio_min": 10,
                        "descripcion": f"Nodo telemétrico en {st['nombre']}.",
                        "distancia_fondo_sensor_cm": st["fondo_sensor_cm"],
                        "caudal_coef_k": st["caudal_k"],
                        "caudal_exp_n": st["caudal_n"]
                    }
                    p_code, p_data, p_text = HttpClient.post(prov_url, prov_payload, timeout=10)
                    if p_code == 201 and p_data:
                        st["api_key"] = p_data.get("api_key_generada", st["api_key"])
                        logger.info(f"✅ Nodo '{st['id_nodo']}' provisionado con éxito. API Key asignada.")
        except Exception as e:
            logger.warning(f"Aviso: No se pudo verificar auto-provisión de nodos ({e}). Continuando con claves configuradas...")

    def run(self):
        logger.info("================================================================")
        logger.info("🚀 INICIANDO SIMULADOR DE NODOS TELEMÉTRICOS - SENTINEL-H2O")
        logger.info(f"📍 API Objetivo: {API_BASE_URL}{TELEMETRY_ENDPOINT}")
        logger.info(f"⏱️  Intervalo de Envío: {SEND_INTERVAL_SECONDS} segundos ({SEND_INTERVAL_SECONDS / 60.0:.1f} min)")
        logger.info(f"📊 Nodos Monitoreados: {len(STATIONS_PROFILES)} estaciones")
        logger.info(f"⚡ Probabilidad de Eventos Anómalos: {ANOMALY_PROBABILITY * 100:.1f}%")
        logger.info("================================================================")

        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)

        time.sleep(3)
        self.auto_provision_if_needed()

        cycle_count = 0
        while self.running:
            cycle_count += 1
            logger.info(f"\n--- [CICLO #{cycle_count} - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ---")
            
            self.check_and_trigger_events()

            for idx, station in enumerate(STATIONS_PROFILES, 1):
                if not self.running:
                    break
                self.send_telemetry_for_station(station)
                time.sleep(1.2)

            logger.info(f"Próximo ciclo en {SEND_INTERVAL_SECONDS} segundos...")
            elapsed = 0
            while elapsed < SEND_INTERVAL_SECONDS and self.running:
                time.sleep(1)
                elapsed += 1

        logger.info("Simulador Sentinel-H2O finalizado con éxito.")


if __name__ == "__main__":
    simulator = DynamicChancaySimulator()
    simulator.run()
