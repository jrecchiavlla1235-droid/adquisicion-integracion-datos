"""
Configuración global del proyecto: rutas, ubicación de Windpeshi y parámetros de las turbinas.
"""

from pathlib import Path

# ==============================================================================
# 1. RUTAS DEL SISTEMA (CROSS-PLATFORM PATHS)
# ==============================================================================
# BASE_DIR apunta a la raíz del proyecto (la carpeta principal)
BASE_DIR = Path(__file__).resolve().parent.parent

# Carpetas de almacenamiento de datos
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

# Rutas de los archivos planos específicos (Fuentes 2 y 3)
HISTORICAL_WIND_FILE = RAW_DATA_DIR / "windpeshi_historical.csv"
REGIONAL_WEATHER_FILE = RAW_DATA_DIR / "regional_weather.csv"

# ==============================================================================
# 2. LOCALIZACIÓN GEOGRÁFICA DEL PARQUE WINDPESHI
# ==============================================================================
# Ubicación en los municipios de Uribia y Maicao, La Guajira, Colombia
WINDPESHI_LOCATION = {
    "name": "Parque Eólico Windpeshi",
    "department": "La Guajira",
    "country": "Colombia",
    "latitude": 11.95,       # Latitud norte aproximada
    "longitude": -71.85,     # Longitud oeste aproximada
    "timezone": "America/Bogota",  # Huso horario local UTC-5
}

# ==============================================================================
# 3. ESPECIFICACIONES TÉCNICAS DE LOS AEROGENERADORES (CURVA DE POTENCIA)
# ==============================================================================
# Parámetros operativos estándar para turbinas eólicas Clase I/II (3.0 MW aprox.)
TURBINE_SPECS = {
    "cut_in_speed_ms": 3.5,     # Velocidad mínima de arranque (m/s). Por debajo, la turbina está detenida.
    "rated_speed_ms": 12.0,     # Velocidad nominal óptima (m/s). A partir de aquí produce su potencia máxima.
    "cut_out_speed_ms": 25.0,   # Velocidad de corte por seguridad (m/s). Por encima, frena para evitar daños mecánicos.
    "rated_power_kw": 3000.0,   # Potencia nominal por turbina en kilovatios (3 MW)
    "hub_height_meters": 100.0, # Altura del buje (torre) en metros
}

# ==============================================================================
# 4. CONFIGURACIÓN DE LA API METEOROLÓGICA EXTERNA (OPEN-METEO)
# ==============================================================================
OPEN_METEO_CONFIG = {
    "base_url": "https://api.open-meteo.com/v1/forecast",
    "timeout_seconds": 10,
    "params": {
        "latitude": WINDPESHI_LOCATION["latitude"],
        "longitude": WINDPESHI_LOCATION["longitude"],
        "hourly": [
            "wind_speed_10m",
            "wind_direction_10m",
            "surface_pressure",
            "temperature_2m",
            "relative_humidity_2m"
        ],
        "timezone": WINDPESHI_LOCATION["timezone"],
        "wind_speed_unit": "ms"  # Solicitamos directamente m/s para facilitar normalización
    }
}

# ==============================================================================
# 5. CONFIGURACIÓN DEL SENSOR IOT (STREAMING Y CONTROL DE CALIDAD)
# ==============================================================================
SENSOR_CONFIG = {
    "sampling_interval_seconds": 600,  # Frecuencia de muestreo: cada 10 minutos (600 seg)
    "simulated_noise_std": 0.5,        # Desviación estándar del ruido gaussiano del sensor
    "anomaly_probability": 0.03,       # 3% de probabilidad de generar lecturas anómalas (para test de calidad)
    "min_valid_speed_ms": 0.0,         # Viento no puede ser negativo
    "max_valid_speed_ms": 45.0,        # Ráfagas superiores a 45 m/s (162 km/h) son anomalías o huracán extremo
    "min_valid_pressure_hpa": 850.0,   # Rango atmosférico válido a nivel del mar / costa
    "max_valid_pressure_hpa": 1100.0
}
