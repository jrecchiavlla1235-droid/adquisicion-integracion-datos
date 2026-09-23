"""
Carga y validación básica de los archivos CSV históricos (Fuentes 2 y 3).
"""

from pathlib import Path
import pandas as pd
from config.settings import HISTORICAL_WIND_FILE, REGIONAL_WEATHER_FILE


class DataSourceError(Exception):
    """Excepción personalizada para fallos de adquisición de datos."""
    pass


def load_historical_wind(filepath: Path = HISTORICAL_WIND_FILE) -> pd.DataFrame:
    """
    Carga el dataset histórico de viento y generación eléctrica de Windpeshi (Fuente 2).
    
    Args:
        filepath: Ruta del archivo CSV.
        
    Returns:
        pd.DataFrame con los datos crudos del parque.
        
    Raises:
        DataSourceError: Si el archivo no existe o no contiene las columnas requeridas.
    """
    if not filepath.exists():
        raise DataSourceError(
            f"No se encontró el archivo histórico de viento en: {filepath}. "
            f"Ejecuta primero el script 'scripts/generate_historical_data.py'."
        )

    expected_columns = {
        "timestamp",
        "wind_speed_ms",
        "wind_direction_deg",
        "power_output_kw",
        "turbine_status",
    }

    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        raise DataSourceError(f"Error al leer el archivo CSV {filepath}: {e}") from e

    missing = expected_columns - set(df.columns)
    if missing:
        raise DataSourceError(
            f"El archivo {filepath} no cumple con el esquema esperado. Columnas faltantes: {missing}"
        )

    return df


def load_regional_weather(filepath: Path = REGIONAL_WEATHER_FILE) -> pd.DataFrame:
    """
    Carga el dataset de condiciones meteorológicas regionales (Fuente 3).
    
    Args:
        filepath: Ruta del archivo CSV.
        
    Returns:
        pd.DataFrame con los datos meteorológicos crudos.
        
    Raises:
        DataSourceError: Si el archivo no existe o faltan columnas esperadas.
    """
    if not filepath.exists():
        raise DataSourceError(
            f"No se encontró el archivo meteorológico regional en: {filepath}."
        )

    expected_columns = {"timestamp", "temperature_c", "humidity_pct", "pressure_hpa"}

    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        raise DataSourceError(f"Error al leer el archivo meteorológico {filepath}: {e}") from e

    missing = expected_columns - set(df.columns)
    if missing:
        raise DataSourceError(
            f"El archivo {filepath} no cumple con el esquema esperado. Columnas faltantes: {missing}"
        )

    return df
