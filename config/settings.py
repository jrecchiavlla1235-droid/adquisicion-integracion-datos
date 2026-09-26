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
            "wind_speed_10m",       # Velocidad a 10 m (referencia)
            "wind_speed_80m",       # Velocidad a 80 m (altura de buje real)
            "wind_direction_10m",
            "surface_pressure",
            "temperature_2m",
            "relative_humidity_2m",
            "shortwave_radiation",  # Irradiancia solar GHI (W/m²) — sistema híbrido
        ],
        "timezone": WINDPESHI_LOCATION["timezone"],
        "wind_speed_unit": "ms"  # Solicitamos directamente m/s para facilitar normalización
    }
}

# ==============================================================================
# 6. PARÁMETROS FÍSICOS DEL BALANCE ENERGÉTICO (energy_balance.py)
# ==============================================================================
ENERGY_BALANCE_CONFIG = {
    # --- Parámetros de la turbina para la fórmula P = 0.5 * ρ * A * v³ * Cp ---
    "rotor_diameter_m": 120.0,      # Diámetro del rotor en metros (turbina 3 MW clase Vestas V120)
    "power_coefficient_cp": 0.42,   # Coeficiente de potencia aerodinámico (valor real promedio)
    "hub_height_m": 100.0,          # Altura del buje en metros
    "roughness_length_z0": 0.03,    # Longitud de rugosidad del suelo (z₀) para Uribia: terreno costero

    # --- Densidad del aire en Uribia (La Guajira) ---
    # Se calcula dinámicamente con T y P, pero se provee un valor nominal de referencia
    "nominal_air_density_kgm3": 1.18,  # kg/m³ a nivel del mar, ~30°C, Uribia coast

    # --- Parámetros del sistema solar (GHI → kWh/m²) ---
    # Si se desea sistema híbrido, se activa este módulo
    "solar_panel_efficiency": 0.20,     # Eficiencia de paneles solares (20%)
    "solar_area_m2": 500.0,             # Área total de paneles en m²
    "solar_performance_ratio": 0.80,    # Factor de rendimiento del sistema (pérdidas cableado, inversores)
}

# ==============================================================================
# 7. PERFIL DE DEMANDA INDUSTRIAL (Empresa a evaluar - Uribia)
# ==============================================================================
# Este bloque modela la carga de la empresa/maquinaria que se desea alimentar.
# Los valores son PARÁMETROS DE ENTRADA configurables por el usuario.
INDUSTRIAL_DEMAND_CONFIG = {
    "company_name": "Planta Industrial Uribia",
    "nominal_power_kw": 800.0,       # Potencia nominal instalada de la maquinaria (kW)
    "daily_operation_hours": 16,     # Horas de operación diaria de la planta
    "operation_start_hour": 6,       # Hora de inicio de operaciones (6:00 AM)
    "operation_end_hour": 22,        # Hora de fin de operaciones (10:00 PM)
    # Perfil de carga horario (24 valores, uno por hora del día, en porcentaje de la carga nominal)
    # Hora 0 = medianoche, hora 6 = 6:00 AM, etc.
    "hourly_load_profile_pct": [
        0.05, 0.05, 0.05, 0.05, 0.05, 0.05,  # 00h-05h: carga mínima (guardia/iluminación)
        0.40, 0.70, 0.90, 1.00, 1.00, 1.00,  # 06h-11h: arranque y plena producción
        0.85, 1.00, 1.00, 0.95, 0.90, 0.85,  # 12h-17h: producción sostenida
        0.70, 0.50, 0.30, 0.15, 0.10, 0.05,  # 18h-23h: cierre gradual de planta
    ],
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
