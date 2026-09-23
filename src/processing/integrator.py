"""
Cálculo de percentiles históricos (P10, P50, P90) e integración temporal de las 4 fuentes.
"""

import pandas as pd
from .normalizer import ensure_timezone_awareness


def compute_historical_hourly_benchmarks(
    df_hist_wind: pd.DataFrame,
    df_hist_weather: pd.DataFrame
) -> pd.DataFrame:
    """
    Calcula los percentiles de referencia histórica (P10, P50, P90) para cada hora del día (0 a 23).
    
    ¿Por qué percentiles en lugar de solo promedios?
    En ingeniería eólica, el percentil P10 indica el viento mínimo garantizado (escenario conservador),
    P50 es la mediana típica y P90 representa un recurso eólico sobresaliente.
    """
    df_w = ensure_timezone_awareness(df_hist_wind, "timestamp")
    df_m = ensure_timezone_awareness(df_hist_weather, "timestamp")

    # Extraer la hora del día (0 a 23)
    df_w["hour"] = df_w["timestamp"].dt.hour
    df_m["hour"] = df_m["timestamp"].dt.hour

    # Benchmarks de viento
    wind_stats = df_w.groupby("hour")["wind_speed_ms"].agg(
        hist_wind_p10=lambda x: x.quantile(0.10),
        hist_wind_p50=lambda x: x.quantile(0.50),
        hist_wind_p90=lambda x: x.quantile(0.90),
        hist_wind_mean="mean",
        hist_power_kw_mean=lambda x: df_w.loc[x.index, "power_output_kw"].mean()
    ).round(2).reset_index()

    # Benchmarks meteorológicos
    weather_stats = df_m.groupby("hour").agg(
        hist_temp_mean=("temperature_c", "mean"),
        hist_humidity_mean=("humidity_pct", "mean"),
        hist_pressure_mean=("pressure_hpa", "mean")
    ).round(1).reset_index()

    benchmarks = pd.merge(wind_stats, weather_stats, on="hour")
    return benchmarks


def integrate_daily_sources(
    df_sensor_hourly: pd.DataFrame,
    df_forecast: pd.DataFrame,
    df_benchmarks: pd.DataFrame,
    target_date: str
) -> pd.DataFrame:
    """
    Realiza el cruce exacto (Merge/Join) de las fuentes para las 24 horas del día seleccionado.
    """
    # 1. Asegurar formato de fechas y horas
    df_sensor = ensure_timezone_awareness(df_sensor_hourly, "timestamp")
    df_sensor["hour"] = df_sensor["timestamp"].dt.hour

    df_fc = ensure_timezone_awareness(df_forecast, "timestamp")
    # Filtrar solo el día objetivo de la predicción de la API
    df_fc = df_fc[df_fc["timestamp"].dt.strftime("%Y-%m-%d") == target_date].copy()
    df_fc["hour"] = df_fc["timestamp"].dt.hour

    # 2. Cruce: Sensor + Pronóstico
    integrated = pd.merge(
        df_sensor,
        df_fc[["hour", "forecast_wind_speed_ms", "forecast_wind_direction_deg", "forecast_temperature_c"]],
        on="hour",
        how="outer"
    )

    # 3. Cruce con Benchmarks Históricos
    integrated = pd.merge(
        integrated,
        df_benchmarks,
        on="hour",
        how="left"
    )

    # Ordenar cronológicamente por hora (0 a 23)
    integrated = integrated.sort_values("hour").reset_index(drop=True)
    return integrated
