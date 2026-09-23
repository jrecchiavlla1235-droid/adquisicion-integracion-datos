"""
Pruebas Unitarias para el Sistema de Evaluación Eólica del Parque Windpeshi.
Valida el control de calidad, la física de la curva de potencia y las reglas de negocio.
"""

import sys
from pathlib import Path

# Agregar raíz del proyecto al path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

import pandas as pd
from src.processing.quality_control import clean_sensor_telemetry
from src.domain.wind_evaluator import WindpeshiEvaluator
from config.settings import TURBINE_SPECS


def test_quality_control_filtering():
    """Prueba que los filtros de calidad detecten y eliminen lecturas anómalas."""
    raw_data = pd.DataFrame([
        {"timestamp": "2026-03-24 10:00:00-0500", "wind_speed_ms": 8.5, "pressure_hpa": 1012.0},  # Válido
        {"timestamp": "2026-03-24 10:10:00-0500", "wind_speed_ms": -4.0, "pressure_hpa": 1012.0}, # Inválido: negativo
        {"timestamp": "2026-03-24 10:20:00-0500", "wind_speed_ms": 85.0, "pressure_hpa": 1012.0}, # Inválido: púa irreal
        {"timestamp": "2026-03-24 10:30:00-0500", "wind_speed_ms": 7.0, "pressure_hpa": 500.0},   # Inválido: presión baja
    ])

    clean_df, report = clean_sensor_telemetry(raw_data)

    assert len(clean_df) == 1, f"Se esperaba 1 registro válido, se obtuvieron {len(clean_df)}"
    assert report.rejected_records == 3, f"Se esperaban 3 descartados, se obtuvieron {report.rejected_records}"
    assert clean_df.iloc[0]["wind_speed_ms"] == 8.5
    print("[PASS] test_quality_control_filtering")


def test_turbine_power_curve_physics():
    """Prueba los umbrales de la curva de potencia (Cut-in, Rated, Cut-out)."""
    evaluator = WindpeshiEvaluator(TURBINE_SPECS)

    # 1. Por debajo de cut-in (3.5 m/s) -> Potencia 0 kW
    p_low = evaluator.calculate_hourly_power(2.0)
    assert p_low == 0.0, f"Potencia por debajo de cut-in debe ser 0 kW, fue: {p_low}"

    # 2. En velocidad nominal (12.0 m/s) -> Potencia nominal máxima (3000 kW)
    p_rated = evaluator.calculate_hourly_power(12.0)
    assert p_rated == 3000.0, f"Potencia en rated debe ser 3000 kW, fue: {p_rated}"

    # 3. En velocidad intermedia (8.0 m/s) -> Potencia positiva creciente
    p_mid = evaluator.calculate_hourly_power(8.0)
    assert 0.0 < p_mid < 3000.0, f"Potencia intermedia incorrecta: {p_mid}"

    # 4. Por encima de cut-out (25.0 m/s) -> Frenos de seguridad, 0 kW
    p_storm = evaluator.calculate_hourly_power(28.0)
    assert p_storm == 0.0, f"Potencia en tormenta (> cut-out) debe ser 0 kW por seguridad, fue: {p_storm}"

    print("[PASS] test_turbine_power_curve_physics")


def test_day_favorability_logic():
    """Prueba las reglas de clasificación de Día Favorable vs No Favorable."""
    evaluator = WindpeshiEvaluator(TURBINE_SPECS)

    # Caso 1: 24 horas de viento suave (2.0 m/s, sub-cut-in)
    unfavorable_df = pd.DataFrame([
        {"hour": h, "sensor_speed_mean_ms": 2.0, "forecast_wind_speed_ms": 2.1, "hist_wind_p50": 8.0}
        for h in range(24)
    ])
    result_unfavorable = evaluator.evaluate_day(unfavorable_df, "2026-03-24")
    assert result_unfavorable.verdict == "DÍA NO FAVORABLE"
    assert result_unfavorable.hours_sub_cut_in == 24

    # Caso 2: 24 horas de viento óptimo (9.5 m/s)
    favorable_df = pd.DataFrame([
        {"hour": h, "sensor_speed_mean_ms": 9.5, "forecast_wind_speed_ms": 9.2, "hist_wind_p50": 8.0}
        for h in range(24)
    ])
    result_favorable = evaluator.evaluate_day(favorable_df, "2026-03-24")
    assert result_favorable.verdict == "DÍA FAVORABLE"
    assert result_favorable.operating_hours == 24

    print("[PASS] test_day_favorability_logic")


if __name__ == "__main__":
    print("[*] Ejecutando suite de pruebas unitarias...")
    test_quality_control_filtering()
    test_turbine_power_curve_physics()
    test_day_favorability_logic()
    print("[ALL TESTS PASSED SUCCESSFULLY!]")
