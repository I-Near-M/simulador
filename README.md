# 🛰️ Sentinel-H2O: Simulador de Nodos Telemétricos (VPS Producción)

Este microservicio simula el comportamiento físico, electroquímico, hidrodinámico y electrónico de las **6 estaciones registradas en la base de datos de producción**:

1. **`NODO-01-CABECERA`**: Estación Lagunas Vichaycocha / Bofedales (Cuenca Alta - 4,350 msnm)
2. **`NODO-02-RAVIRA`**: Estación Subcuenca Ravira / Pacaraos (Cuenca Alta-Media - 2,850 msnm)
3. **`NODO-03-ACOS`**: Estación Conducción Matriz Acos - Santo Domingo (Cuenca Media - 1,250 msnm)
4. **`NODO-04-HUANDO`**: Estación Bocatoma Matriz Huando - Palpa (Cuenca Baja - 450 msnm)
5. **`NODO-05-HUAYOPAMPA`**: Estación Sector Huayopampa / Parcela Piloto (Parcela Piloto - 320 msnm)
6. **`NODO-06-CHANCAY`**: Estación Valle Bajo y Desembocadura Chancay (Desembocadura - 25 msnm)

---

## 🚀 Despliegue Rápido en tu VPS

### 1. Crear carpeta del simulador en el servidor
```bash
mkdir -p ~/sentinel_simulator
cd ~/sentinel_simulator
```

### 2. Copiar los archivos
Copia los siguientes 4 archivos a dicha carpeta:
- `Dockerfile`
- `docker-compose.yml`
- `simulator.py`
- `.env`

### 3. Iniciar el simulador en segundo plano
```bash
docker compose up -d --build
```

### 4. Verificar logs de transmisión cada 10 minutos
```bash
docker compose logs -f
```

---

## ⚡ Ejecución directa con Python (Sin Docker)
```bash
python3 simulator.py
```
