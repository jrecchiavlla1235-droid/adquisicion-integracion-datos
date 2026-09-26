"""
Cliente HTTP para consultar el pronóstico horario de la API de Open-Meteo (Fuente 4).

Mejoras implementadas en esta versión:
  - Extrae velocidad del viento a 80 m (altura de buje) además de 10 m.
  - Extrae shortwave_radiation como proxy de GHI solar para sistemas híbridos.
  - Implementa caché basada en archivo JSON por fecha para evitar llamadas
    redundantes a la API cuando el pipeline se ejecuta varias veces en el mismo día.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

from config.settings import OPEN_METEO_CONFIG, PROCESSED_DATA_DIR
from src.daq.csv_loader import DataSourceError

logger = logging.getLogger(__name__)

# Directorio donde se guarda el caché de respuestas de la API
_CACHE_DIR = PROCESSED_DATA_DIR / "api_cache"


def _get_cache_path(target_date: str) -> Path:
    """Devuelve la ruta del archivo de caché para una fecha dada."""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _CACHE_DIR / f"open_meteo_{target_date}.json"


def _load_from_cache(target_date: str) -> dict | None:
    """
    Intenta cargar la respuesta de la API desde el caché local.

    ¿Por qué cachear? Open-Meteo es una API pública gratuita con límites de
    peticiones. Si el pipeline se ejecuta varias veces en el mismo día (para
    depuración, pruebas, re-ejecución), evitamos solicitudes redundantes y
    ganamos velocidad de arranque (~0 ms vs. ~500 ms de latencia de red).

    Returns:
        dict con los datos JSON cacheados, o None si no existe caché válida.
    """
    cache_path = _get_cache_path(target_date)
    if cache_path.exists():
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                logger.info("[cache] Cargando pronóstico desde caché local: %s", cache_path.name)
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            logger.warning("[cache] Caché corrupta, se descargará de nuevo.")
    return None


def _save_to_cache(target_date: str, data: dict) -> None:
    """Persiste la respuesta JSON de la API en disco para reutilización futura."""
    cache_path = _get_cache_path(target_date)
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info("[cache] Pronóstico guardado en caché: %s", cache_path.name)
    except OSError as e:
        logger.warning("[cache] No se pudo guardar caché: %s", e)


def fetch_weather_forecast(
    config: dict = OPEN_METEO_CONFIG,
    target_date: str | None = None,
    use_cache: bool = True,
) -> pd.DataFrame:
    """
    Consulta la API REST de Open-Meteo para obtener pronósticos horarios de viento,
    presión, temperatura, irradiancia solar (GHI) y velocidad del viento a 80 m.

    Estrategia de caché:
        Si use_cache=True (por defecto) y ya existe un archivo JSON para la
        fecha solicitada, se retorna sin hacer ninguna llamada HTTP.
        Si no existe caché, hace la petición y guarda el resultado para
        ejecuciones futuras del mismo día.

    Args:
        config:      Configuración de la API (URL, parámetros, timeout).
        target_date: Fecha en formato 'YYYY-MM-DD' usada como clave de caché.
                     Si es None, se usa la fecha actual.
        use_cache:   Si True (default), usa el sistema de caché en disco.

    Returns:
        pd.DataFrame con las predicciones horarias para las coordenadas de Windpeshi.
        Columnas enriquecidas:
          - forecast_wind_speed_ms       → velocidad del viento a 10 m
          - forecast_wind_speed_80m_ms   → velocidad a 80 m (altura de buje) 🆕
          - forecast_wind_direction_deg  → dirección del viento
          - forecast_surface_pressure_hpa
          - forecast_temperature_c
          - forecast_humidity_pct
          - forecast_ghi_wm2             → irradiancia global horizontal (W/m²) 🆕

    Raises:
        DataSourceError: En caso de error de red, timeout o respuesta HTTP no exitosa.
    """
    if target_date is None:
        target_date = datetime.now().strftime("%Y-%m-%d")

    # ── Intentar caché ──────────────────────────────────────────────────────
    data = None
    if use_cache:
        data = _load_from_cache(target_date)

    # ── Llamada HTTP si no hay caché válida ─────────────────────────────────
    if data is None:
        url = config["base_url"]
        params = config["params"]
        timeout = config.get("timeout_seconds", 10)

        try:
            response = requests.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.Timeout as e:
            raise DataSourceError(
                f"Tiempo de espera agotado al conectar con Open-Meteo: {e}"
            ) from e
        except requests.exceptions.RequestException as e:
            raise DataSourceError(
                f"Error en la petición HTTP a Open-Meteo: {e}"
            ) from e
        except ValueError as e:
            raise DataSourceError(
                f"Respuesta inválida (no es JSON) desde Open-Meteo: {e}"
            ) from e

        if use_cache:
            _save_to_cache(target_date, data)

    # ── Validar estructura de la respuesta ──────────────────────────────────
    if "hourly" not in data:
        raise DataSourceError(
            "La respuesta de la API no contiene el bloque esperado 'hourly'."
        )

    hourly_data = data["hourly"]

    # ── Construir DataFrame enriquecido ────────────────────────────────────
    df = pd.DataFrame({
        "timestamp":                    hourly_data.get("time", []),
        # Velocidad de viento de referencia a 10 m (altura estándar meteorológica)
        "forecast_wind_speed_ms":       hourly_data.get("wind_speed_10m", []),
        # Velocidad del viento a 80 m: más cercana a la altura del buje de la turbina.
        # La API de Open-Meteo ofrece este campo directamente si se solicita.
        "forecast_wind_speed_80m_ms":   hourly_data.get("wind_speed_80m", []),
        "forecast_wind_direction_deg":  hourly_data.get("wind_direction_10m", []),
        "forecast_surface_pressure_hpa": hourly_data.get("surface_pressure", []),
        "forecast_temperature_c":       hourly_data.get("temperature_2m", []),
        "forecast_humidity_pct":        hourly_data.get("relative_humidity_2m", []),
        # GHI: Irradiancia Global Horizontal en W/m². Representa la energía solar
        # total que recibe una superficie horizontal (directa + difusa).
        # Es la variable estándar para calcular la generación fotovoltaica.
        "forecast_ghi_wm2":             hourly_data.get("shortwave_radiation", []),
    })

    return df
