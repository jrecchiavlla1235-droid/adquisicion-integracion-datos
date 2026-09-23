"""
Capa DAQ (Data Acquisition):
Módulo responsable exclusivamente de la ingesta y extracción de datos desde las fuentes crudas.
Ninguna función aquí debe realizar transformación ni aplicar reglas de negocio.
"""

from .csv_loader import load_historical_wind, load_regional_weather
from .weather_api import fetch_weather_forecast
from .sensor_stream import AnemometerIoTSensor

__all__ = [
    "load_historical_wind",
    "load_regional_weather",
    "fetch_weather_forecast",
    "AnemometerIoTSensor",
]
