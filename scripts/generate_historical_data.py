"""
Script Generador de Datos Históricos Sintéticos para el Parque Eólico Windpeshi.

Fundamento Físico e Ingenieril:
1. Distribución de Weibull: Modela la velocidad del viento con parámetros k (forma) y c (escala)
   específicos para el régimen de vientos Alisios en La Guajira, Colombia.
2. Ciclo diurno: Refleja mayor velocidad en horas de la tarde debido al gradiente térmico mar-desierto.
3. Curva de potencia eólica real:
   - v < Cut-in (3.5 m/s): 0 kW (turbina parada).
   - Cut-in <= v < Rated (12.0 m/s): Crecimiento cúbico de potencia (P ~ v^3).
   - Rated <= v <= Cut-out (25.0 m/s): Potencia nominal constante (3000 kW) regulada por 'pitch control'.
   - v > Cut-out (25.0 m/s): 0 kW (frenos activados por protección contra tormentas).
"""

import sys
from pathlib import Path

# Permitir que el script encuentre el paquete config importando desde la raíz
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

import numpy as np
import pandas as pd
from config.settings import (
    HISTORICAL_WIND_FILE,
    REGIONAL_WEATHER_FILE,
    TURBINE_SPECS,
    WINDPESHI_LOCATION,
)


def calculate_wind_power(wind_speed: float, specs: dict) -> tuple[float, str]:
    """
    Calcula la potencia de salida en kW y el estado operativo según la curva de potencia.
    
    Args:
        wind_speed: Velocidad del viento en m/s.
        specs: Diccionario con especificaciones de la turbina.
        
    Returns:
        tuple[float, str]: (potencia en kW, estado operativo).
    """
    cut_in = specs["cut_in_speed_ms"]
    rated = specs["rated_speed_ms"]
    cut_out = specs["cut_out_speed_ms"]
    p_rated = specs["rated_power_kw"]

    if wind_speed < cut_in:
        return 0.0, "STOPPED_LOW_WIND"
    elif cut_in <= wind_speed < rated:
        # Crecimiento cúbico de la energía cinética del viento: P = P_rated * ((v - cut_in) / (rated - cut_in))^3
        fraction = (wind_speed - cut_in) / (rated - cut_in)
        power = round(p_rated * (fraction ** 3), 2)
        return power, "OPERATIONAL"
    elif rated <= wind_speed <= cut_out:
        # Control de paso de pala mantiene la potencia al máximo nominal sin sobrecargar el generador
        return p_rated, "OPERATIONAL_MAX"
    else:
        # Sistema de frenado aerodinámico y mecánico ante ráfagas peligrosas
        return 0.0, "STOPPED_HIGH_WIND_PROTECTION"


def generate_synthetic_datasets(year: int = 2025):
    """
    Genera los dos datasets en archivos planos requeridos por el proyecto:
    1. Fuente 2: windpeshi_historical.csv (datos horarios de viento y generación eléctrica).
    2. Fuente 3: regional_weather.csv (datos horarios meteorológicos regionales).
    """
    print(f"[*] Iniciando generación de datasets históricos para el año {year}...")
    np.random.seed(42)  # Garantiza reproducibilidad científica

    # 8760 horas en un año no bisiesto
    date_range = pd.date_range(
        start=f"{year}-01-01 00:00:00",
        end=f"{year}-12-31 23:00:00",
        freq="h",
        tz=WINDPESHI_LOCATION["timezone"]
    )
    total_hours = len(date_range)

    # --------------------------------------------------------------------------
    # 1. GENERACIÓN DE VELOCIDAD DEL VIENTO (DISTRIBUCIÓN DE WEIBULL)
    # --------------------------------------------------------------------------
    # Parámetros para La Guajira: k = 2.2 (forma, vientos estables), c = 9.8 m/s (escala, alta energía)
    k_shape = 2.2
    c_scale = 9.8
    base_weibull = c_scale * np.random.weibull(k_shape, total_hours)

    # Modular con el ciclo diurno (más viento entre 14:00 y 20:00 por convección térmica)
    hours = date_range.hour
    diurnal_factor = 1.0 + 0.25 * np.sin((hours - 8) * np.pi / 12)
    wind_speed = np.maximum(0.0, base_weibull * diurnal_factor)
    wind_speed = np.round(wind_speed, 2)

    # Dirección del viento en La Guajira: Vientos Alisios del Este-Noreste (60° a 80°)
    wind_direction = np.random.normal(loc=70.0, scale=15.0, size=total_hours) % 360
    wind_direction = np.round(wind_direction, 1)

    # --------------------------------------------------------------------------
    # 2. CÁLCULO DE POTENCIA ELÉCTRICA Y ESTADO
    # --------------------------------------------------------------------------
    power_outputs = []
    statuses = []
    for ws in wind_speed:
        p, st = calculate_wind_power(ws, TURBINE_SPECS)
        power_outputs.append(p)
        statuses.append(st)

    # Dataset Fuente 2
    df_historical = pd.DataFrame({
        "timestamp": date_range.strftime("%Y-%m-%d %H:%M:%S%z"),
        "wind_speed_ms": wind_speed,
        "wind_direction_deg": wind_direction,
        "power_output_kw": power_outputs,
        "turbine_status": statuses
    })

    HISTORICAL_WIND_FILE.parent.mkdir(parents=True, exist_ok=True)
    df_historical.to_csv(HISTORICAL_WIND_FILE, index=False)
    print(f"[+] Fuente 2 creada: {HISTORICAL_WIND_FILE} ({len(df_historical)} registros).")

    # --------------------------------------------------------------------------
    # 3. GENERACIÓN DE METEOROLOGÍA REGIONAL (FUENTE 3)
    # --------------------------------------------------------------------------
    # Clima desértico costero de Uribia: 26°C a 36°C, humedad 60%-85%, presión ~1010 hPa
    temp_base = 29.0 + 4.0 * np.sin((hours - 9) * np.pi / 12) + np.random.normal(0, 1.2, total_hours)
    temperature_c = np.round(temp_base, 1)

    humidity_base = 75.0 - 15.0 * np.sin((hours - 9) * np.pi / 12) + np.random.normal(0, 3.0, total_hours)
    humidity_pct = np.clip(np.round(humidity_base, 1), 30.0, 100.0)

    pressure_base = 1011.0 + np.random.normal(0, 2.0, total_hours)
    pressure_hpa = np.round(pressure_base, 1)

    df_weather = pd.DataFrame({
        "timestamp": date_range.strftime("%Y-%m-%d %H:%M:%S%z"),
        "temperature_c": temperature_c,
        "humidity_pct": humidity_pct,
        "pressure_hpa": pressure_hpa
    })

    REGIONAL_WEATHER_FILE.parent.mkdir(parents=True, exist_ok=True)
    df_weather.to_csv(REGIONAL_WEATHER_FILE, index=False)
    print("[OK] Datasets sinteticos listos y guardados en data/raw/.")


if __name__ == "__main__":
    generate_synthetic_datasets(year=2025)
