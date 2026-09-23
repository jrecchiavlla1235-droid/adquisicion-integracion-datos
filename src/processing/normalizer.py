"""
Normalización de zona horaria (UTC-5) y agregación de telemetría de 10 min a resolución de 1 hora.
"""

import pandas as pd
from config.settings import WINDPESHI_LOCATION


def ensure_timezone_awareness(df: pd.DataFrame, timestamp_col: str = "timestamp") -> pd.DataFrame:
    """
    Convierte la columna de fecha a tipo datetime consciente de la zona horaria local de La Guajira.
    """
    df = df.copy()
    target_tz = WINDPESHI_LOCATION["timezone"]

    # Convertir a datetime de pandas
    df[timestamp_col] = pd.to_datetime(df[timestamp_col], utc=True)
    
    # Convertir al huso horario local (UTC-5)
    df[timestamp_col] = df[timestamp_col].dt.tz_convert(target_tz)
    return df


def align_to_hourly_resolution(df_sensor_clean: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega las lecturas de 10 minutos del sensor en promedios horarios.
    
    Para análisis eólico profesional se calculan:
    - Velocidad media horaria (wind_speed_ms_mean)
    - Ráfaga máxima registrada en la hora (wind_gust_ms_max)
    - Dirección media del viento (wind_direction_deg)
    - Presión media (pressure_hpa_mean)
    - Muestras válidas por hora (sample_count)
    """
    if df_sensor_clean.empty:
        return pd.DataFrame()

    df = ensure_timezone_awareness(df_sensor_clean, "timestamp")
    df = df.set_index("timestamp")

    # Resampleo horario
    hourly = df.resample("1h").agg({
        "wind_speed_ms": ["mean", "max"],
        "wind_direction_deg": "mean",
        "pressure_hpa": "mean",
        "sensor_id": "count"
    })

    # Aplanar el MultiIndex de columnas para facilitar su uso posterior
    hourly.columns = [
        "sensor_speed_mean_ms",
        "sensor_gust_max_ms",
        "sensor_direction_deg",
        "sensor_pressure_hpa",
        "sensor_sample_count"
    ]

    hourly = hourly.reset_index()
    # Redondear para presentación clara
    hourly["sensor_speed_mean_ms"] = hourly["sensor_speed_mean_ms"].round(2)
    hourly["sensor_gust_max_ms"] = hourly["sensor_gust_max_ms"].round(2)
    hourly["sensor_direction_deg"] = hourly["sensor_direction_deg"].round(1)
    hourly["sensor_pressure_hpa"] = hourly["sensor_pressure_hpa"].round(1)

    return hourly
