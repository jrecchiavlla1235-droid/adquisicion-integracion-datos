"""
Cliente HTTP para consultar el pronóstico horario de la API de Open-Meteo (Fuente 4).
"""

import requests
import pandas as pd
from config.settings import OPEN_METEO_CONFIG
from src.daq.csv_loader import DataSourceError


def fetch_weather_forecast(config: dict = OPEN_METEO_CONFIG) -> pd.DataFrame:
    """
    Consulta la API REST de Open-Meteo para obtener pronósticos horarios de viento y clima.
    
    Args:
        config: Diccionario con la URL base, parámetros de consulta y timeout.
        
    Returns:
        pd.DataFrame con las predicciones horarias para las coordenadas de Windpeshi.
        
    Raises:
        DataSourceError: En caso de error de red, timeout o respuesta HTTP no exitosa.
    """
    url = config["base_url"]
    params = config["params"]
    timeout = config.get("timeout_seconds", 10)

    try:
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()  # Genera excepción para códigos 4xx o 5xx
        data = response.json()
    except requests.exceptions.Timeout as e:
        raise DataSourceError(f"Tiempo de espera agotado al conectar con Open-Meteo: {e}") from e
    except requests.exceptions.RequestException as e:
        raise DataSourceError(f"Error en la petición HTTP a Open-Meteo: {e}") from e
    except ValueError as e:
        raise DataSourceError(f"Respuesta inválida (no es JSON) desde Open-Meteo: {e}") from e

    # Validar que contenga la sección 'hourly'
    if "hourly" not in data:
        raise DataSourceError("La respuesta de la API no contiene el bloque esperado 'hourly'.")

    hourly_data = data["hourly"]
    
    # Construir DataFrame con los datos horarios
    df = pd.DataFrame({
        "timestamp": hourly_data.get("time", []),
        "forecast_wind_speed_ms": hourly_data.get("wind_speed_10m", []),
        "forecast_wind_direction_deg": hourly_data.get("wind_direction_10m", []),
        "forecast_surface_pressure_hpa": hourly_data.get("surface_pressure", []),
        "forecast_temperature_c": hourly_data.get("temperature_2m", []),
        "forecast_humidity_pct": hourly_data.get("relative_humidity_2m", []),
    })

    return df
