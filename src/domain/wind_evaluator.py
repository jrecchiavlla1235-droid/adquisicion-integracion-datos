"""
Evaluación de la curva de potencia de la turbina y clasificación de favorabilidad del día.
"""

from dataclasses import dataclass
from typing import List
import pandas as pd
from config.settings import TURBINE_SPECS


@dataclass
class DayEvaluationResult:
    """Resultado cuantitativo y justificación de la favorabilidad del día."""
    target_date: str
    verdict: str                  # "FAVORABLE" o "NO FAVORABLE"
    operating_hours: int          # Horas dentro del rango operativo [Cut-in, Cut-out]
    hours_sub_cut_in: int         # Horas de viento insuficiente (< 3.5 m/s)
    hours_super_cut_out: int      # Horas de tormenta/frenado de emergencia (> 25 m/s)
    avg_integrated_speed_ms: float
    historical_p50_benchmark_ms: float
    estimated_daily_energy_mwh: float
    reasons: List[str]

    def formatted_summary(self) -> str:
        border = "=" * 70
        return (
            f"\n{border}\n"
            f"  INFORME DE EVALUACIÓN EÓLICA - PARQUE WINDPESHI ({self.target_date})\n"
            f"{border}\n"
            f"  VEREDICTO FINAL:               >>> {self.verdict} <<<\n"
            f"  Velocidad Media Integrada:     {self.avg_integrated_speed_ms:.2f} m/s\n"
            f"  Referencia Histórica (P50):    {self.historical_p50_benchmark_ms:.2f} m/s\n"
            f"  Horas Operativas (3.5 - 25m/s):{self.operating_hours} / 24 horas\n"
            f"  Horas con Viento Insuficiente: {self.hours_sub_cut_in} horas\n"
            f"  Horas con Riesgo de Tormenta:  {self.hours_super_cut_out} horas\n"
            f"  Generación Estimada (1 Turb):  {self.estimated_daily_energy_mwh:.2f} MWh\n"
            f"{border}\n"
            f"  JUSTIFICACIÓN TÉCNICA:\n"
            + "\n".join(f"  - {r}" for r in self.reasons) + "\n"
            f"{border}\n"
        )


class WindpeshiEvaluator:
    """
    Evaluador de reglas de negocio para turbinas eólicas.
    """

    def __init__(self, specs: dict = TURBINE_SPECS):
        self.cut_in = specs["cut_in_speed_ms"]
        self.rated = specs["rated_speed_ms"]
        self.cut_out = specs["cut_out_speed_ms"]
        self.rated_power_kw = specs["rated_power_kw"]

    def calculate_hourly_power(self, wind_speed: float) -> float:
        """Calcula la potencia instantánea generada en kW según la curva de potencia."""
        if wind_speed < self.cut_in:
            return 0.0
        elif self.cut_in <= wind_speed < self.rated:
            fraction = (wind_speed - self.cut_in) / (self.rated - self.cut_in)
            return self.rated_power_kw * (fraction ** 3)
        elif self.rated <= wind_speed <= self.cut_out:
            return self.rated_power_kw
        else:
            return 0.0

    def evaluate_day(self, df_integrated: pd.DataFrame, target_date: str) -> DayEvaluationResult:
        """
        Evalúa las 24 horas integradas y emite el veredicto oficial.
        
        Criterio Senior de Decisión:
        1. Para cada hora se toma la velocidad más representativa:
           Si hay lectura real de sensor, se le da mayor peso (70% sensor, 30% forecast).
           Si no hay sensor disponible en esa hora, se usa 100% el forecast.
        2. Condiciones para "DÍA FAVORABLE":
           - Al menos 16 horas del día (>= 66%) deben estar dentro del rango operativo [3.5 m/s, 25 m/s].
           - No más de 2 horas de riesgo extremo por superación de velocidad de corte (cut-out).
           - La velocidad media integrada debe ser competitiva frente al percentil histórico P50.
        """
        speeds = []
        hourly_powers = []
        hours_in_range = 0
        hours_below = 0
        hours_above = 0

        for _, row in df_integrated.iterrows():
            sensor_v = row.get("sensor_speed_mean_ms")
            forecast_v = row.get("forecast_wind_speed_ms")

            # Combinación ponderada sensor + forecast
            if pd.notna(sensor_v) and pd.notna(forecast_v):
                v_effective = (0.7 * sensor_v) + (0.3 * forecast_v)
            elif pd.notna(sensor_v):
                v_effective = sensor_v
            elif pd.notna(forecast_v):
                v_effective = forecast_v
            else:
                v_effective = row.get("hist_wind_p50", 8.0)

            speeds.append(v_effective)
            p = self.calculate_hourly_power(v_effective)
            hourly_powers.append(p)

            if v_effective < self.cut_in:
                hours_below += 1
            elif v_effective > self.cut_out:
                hours_above += 1
            else:
                hours_in_range += 1

        avg_speed = float(pd.Series(speeds).mean()) if speeds else 0.0
        hist_p50 = float(df_integrated["hist_wind_p50"].mean()) if "hist_wind_p50" in df_integrated else 8.5
        total_energy_mwh = sum(hourly_powers) / 1000.0  # de kWh a MWh

        # Reglas de negocio para el veredicto
        reasons = []
        is_favorable = True

        # Regla 1: Disponibilidad de recurso eólico
        if hours_in_range >= 16:
            reasons.append(
                f"Excelente disponibilidad: {hours_in_range}/24 horas se encuentran dentro de la curva de potencia óptima."
            )
        else:
            is_favorable = False
            reasons.append(
                f"Baja disponibilidad operativa: solo {hours_in_range}/24 horas superan la velocidad de arranque ({self.cut_in} m/s)."
            )

        # Regla 2: Seguridad ante ráfagas extremas (Cut-out)
        if hours_above > 2:
            is_favorable = False
            reasons.append(
                f"Alerta de seguridad: {hours_above} horas registraron vientos mayores a {self.cut_out} m/s, "
                f"obligando al frenado aerodinámico de protección."
            )
        elif hours_above > 0:
            reasons.append(
                f"Precaución: se registraron {hours_above} horas con picos cercanos al límite de corte."
            )

        # Regla 3: Comparativa con benchmark histórico
        if avg_speed >= hist_p50:
            reasons.append(
                f"Rendimiento superior: La velocidad media ({avg_speed:.2f} m/s) supera o iguala la mediana histórica ({hist_p50:.2f} m/s)."
            )
        else:
            diff = hist_p50 - avg_speed
            reasons.append(
                f"Rendimiento moderado: La velocidad media ({avg_speed:.2f} m/s) está {diff:.2f} m/s por debajo de la mediana histórica."
            )

        verdict = "DÍA FAVORABLE" if is_favorable else "DÍA NO FAVORABLE"

        return DayEvaluationResult(
            target_date=target_date,
            verdict=verdict,
            operating_hours=hours_in_range,
            hours_sub_cut_in=hours_below,
            hours_super_cut_out=hours_above,
            avg_integrated_speed_ms=avg_speed,
            historical_p50_benchmark_ms=hist_p50,
            estimated_daily_energy_mwh=total_energy_mwh,
            reasons=reasons,
        )
