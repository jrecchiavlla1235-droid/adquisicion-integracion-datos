"""
Filtro de calidad de datos para la telemetría del sensor (valores negativos, ráfagas extremas y nulos).
"""

from dataclasses import dataclass
import pandas as pd
from config.settings import SENSOR_CONFIG


@dataclass
class QualityReport:
    """Reporte estructurado con métricas de salud de los datos recibidos."""
    total_records: int
    valid_records: int
    rejected_records: int
    valid_percentage: float
    anomalies_detected: dict

    def summary(self) -> str:
        return (
            f"[Quality Report] Total: {self.total_records} | "
            f"Válidos: {self.valid_records} ({self.valid_percentage:.1f}%) | "
            f"Descartados: {self.rejected_records} | "
            f"Fallas: {self.anomalies_detected}"
        )


def clean_sensor_telemetry(
    df_raw: pd.DataFrame,
    config: dict = SENSOR_CONFIG
) -> tuple[pd.DataFrame, QualityReport]:
    """
    Aplica filtros de calidad física a las lecturas del anemómetro/veleta.
    
    Reglas de Calidad:
    1. Viento no puede ser negativo (min_valid_speed_ms = 0.0 m/s).
    2. Viento no puede exceder el límite físico huracanado (max_valid_speed_ms = 45.0 m/s).
    3. Presión atmosférica debe estar dentro de límites marinos normales (850 - 1100 hPa).
    4. Ningún campo crítico puede ser nulo (NaN o None).
    
    Args:
        df_raw: DataFrame con la telemetría en bruto.
        config: Parámetros con los umbrales de validación.
        
    Returns:
        tuple[pd.DataFrame, QualityReport]: DataFrame limpio y reporte de calidad.
    """
    total = len(df_raw)
    if total == 0:
        return df_raw.copy(), QualityReport(0, 0, 0, 0.0, {})

    anomalies = {
        "negative_speed": 0,
        "extreme_speed_spike": 0,
        "abnormal_pressure": 0,
        "null_values": 0,
    }

    # 1. Chequeo de nulos
    null_mask = df_raw[["wind_speed_ms", "pressure_hpa", "timestamp"]].isna().any(axis=1)
    anomalies["null_values"] = int(null_mask.sum())

    # 2. Viento negativo
    neg_speed_mask = df_raw["wind_speed_ms"] < config["min_valid_speed_ms"]
    anomalies["negative_speed"] = int(neg_speed_mask.sum())

    # 3. Viento excesivo (púa irreal de sensor)
    max_speed_mask = df_raw["wind_speed_ms"] > config["max_valid_speed_ms"]
    anomalies["extreme_speed_spike"] = int(max_speed_mask.sum())

    # 4. Presión anómala
    pressure_mask = (
        (df_raw["pressure_hpa"] < config["min_valid_pressure_hpa"]) |
        (df_raw["pressure_hpa"] > config["max_valid_pressure_hpa"])
    )
    anomalies["abnormal_pressure"] = int(pressure_mask.sum())

    # Máscara de registros inválidos
    invalid_mask = null_mask | neg_speed_mask | max_speed_mask | pressure_mask
    valid_df = df_raw[~invalid_mask].copy()

    rejected_count = int(invalid_mask.sum())
    valid_count = len(valid_df)
    valid_pct = (valid_count / total) * 100.0 if total > 0 else 0.0

    report = QualityReport(
        total_records=total,
        valid_records=valid_count,
        rejected_records=rejected_count,
        valid_percentage=valid_pct,
        anomalies_detected={k: v for k, v in anomalies.items() if v > 0},
    )

    return valid_df, report
