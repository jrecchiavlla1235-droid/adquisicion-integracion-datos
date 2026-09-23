"""
Pipeline que orquesta las etapas de adquisición, limpieza, integración y evaluación.
"""

from pathlib import Path
import pandas as pd
from config.settings import PROCESSED_DATA_DIR
from src.daq import (
    load_historical_wind,
    load_regional_weather,
    fetch_weather_forecast,
    AnemometerIoTSensor,
)
from src.processing import (
    clean_sensor_telemetry,
    align_to_hourly_resolution,
    integrate_daily_sources,
    QualityReport,
)
from src.processing.integrator import compute_historical_hourly_benchmarks
from src.domain import WindpeshiEvaluator, DayEvaluationResult


class WindpeshiPipeline:
    """
    Orquestador del flujo ETL + Evaluación para el Parque Windpeshi.
    """

    def __init__(self):
        self.sensor = AnemometerIoTSensor()
        self.evaluator = WindpeshiEvaluator()

    def run(self, target_date: str) -> tuple[DayEvaluationResult, pd.DataFrame, QualityReport]:
        """
        Ejecuta el ciclo de vida completo de los datos para un día seleccionado.
        
        Etapas:
        1. DAQ: Adquisición de las 4 fuentes (Sensor IoT, CSV Viento, CSV Clima, API Open-Meteo).
        2. QA: Control de calidad y depuración de anomalías del sensor.
        3. Normalización: Agregación de 10 min a resolución horaria (1h) en UTC-5.
        4. Integración: Cruce temporal y cálculo de percentiles históricos.
        5. Dominio: Evaluación física de la curva de potencia y determinación de favorabilidad.
        6. Persistencia: Almacenamiento del dataset integrado en data/processed/.
        
        Args:
            target_date: Fecha a procesar en formato 'YYYY-MM-DD'.
            
        Returns:
            tuple: (Resultado de evaluación, DataFrame integrado, Reporte de calidad de datos)
        """
        print(f"[*] INICIANDO PIPELINE DE ADQUISICIÓN E INTEGRACIÓN - FECHA: {target_date}")

        # ----------------------------------------------------------------------
        # ETAPA 1: ADQUISICIÓN (DAQ)
        # ----------------------------------------------------------------------
        print("  [1/5] Adquiriendo datos de las 4 fuentes independientes...")
        df_hist_wind = load_historical_wind()
        df_hist_weather = load_regional_weather()
        df_forecast = fetch_weather_forecast()
        df_sensor_raw = self.sensor.simulate_day_stream(target_date=target_date, allow_anomalies=True)
        print(f"        - Sensor IoT crudo: {len(df_sensor_raw)} lecturas.")
        print(f"        - Pronóstico API:   {len(df_forecast)} horas recibidas.")
        print(f"        - Históricos:       {len(df_hist_wind)} registros de viento cargados.")

        # ----------------------------------------------------------------------
        # ETAPA 2: CONTROL DE CALIDAD Y LIMPIEZA (QA)
        # ----------------------------------------------------------------------
        print("  [2/5] Aplicando reglas de calidad y detección de anomalías...")
        df_sensor_clean, quality_report = clean_sensor_telemetry(df_sensor_raw)
        print(f"        - {quality_report.summary()}")

        # ----------------------------------------------------------------------
        # ETAPA 3: NORMALIZACIÓN Y ARMONIZACIÓN TEMPORAL
        # ----------------------------------------------------------------------
        print("  [3/5] Normalizando husos horarios y agregando a resolución horaria...")
        df_sensor_hourly = align_to_hourly_resolution(df_sensor_clean)

        # ----------------------------------------------------------------------
        # ETAPA 4: TRANSFORMACIÓN E INTEGRACIÓN MULTIFUENTE
        # ----------------------------------------------------------------------
        print("  [4/5] Integrando fuentes y cruzando con percentiles históricos (P10, P50, P90)...")
        benchmarks = compute_historical_hourly_benchmarks(df_hist_wind, df_hist_weather)
        df_integrated = integrate_daily_sources(
            df_sensor_hourly=df_sensor_hourly,
            df_forecast=df_forecast,
            df_benchmarks=benchmarks,
            target_date=target_date
        )

        # ----------------------------------------------------------------------
        # ETAPA 5: MOTOR DE DECISIÓN EÓLICA (DOMINIO)
        # ----------------------------------------------------------------------
        print("  [5/5] Evaluando reglas de física eólica y curva de potencia...")
        evaluation_result = self.evaluator.evaluate_day(df_integrated, target_date)

        # ----------------------------------------------------------------------
        # ETAPA 6: PERSISTENCIA (EXPORTACIÓN A CSV Y EXCEL)
        # ----------------------------------------------------------------------
        PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

        # 1. Exportación a archivo plano CSV
        csv_file = PROCESSED_DATA_DIR / f"integrated_{target_date}.csv"
        df_integrated.to_csv(csv_file, index=False)
        print(f"[OK] Archivo CSV generado en: {csv_file}")

        # 2. Exportación a libro Microsoft Excel (.xlsx) con dos hojas
        excel_file = PROCESSED_DATA_DIR / f"integrated_{target_date}.xlsx"
        
        # Eliminar información de timezone de las columnas datetime para compatibilidad con Excel
        df_excel = df_integrated.copy()
        for col in df_excel.select_dtypes(include=["datetimetz"]).columns:
            df_excel[col] = df_excel[col].dt.tz_localize(None)

        df_kpis = pd.DataFrame([
            {"Métrica": "Fecha Evaluada", "Valor": target_date},
            {"Métrica": "Veredicto Oficial", "Valor": evaluation_result.verdict},
            {"Métrica": "Velocidad Media Integrada (m/s)", "Valor": round(evaluation_result.avg_integrated_speed_ms, 2)},
            {"Métrica": "Referencia Histórica P50 (m/s)", "Valor": round(evaluation_result.historical_p50_benchmark_ms, 2)},
            {"Métrica": "Horas Operativas (3.5 - 25 m/s)", "Valor": f"{evaluation_result.operating_hours} / 24 hrs"},
            {"Métrica": "Energía Proyectada (MWh)", "Valor": round(evaluation_result.estimated_daily_energy_mwh, 2)},
            {"Métrica": "Total Muestras Sensor IoT", "Valor": quality_report.total_records},
            {"Métrica": "Muestras Válidas (%)", "Valor": f"{quality_report.valid_percentage:.1f}%"},
            {"Métrica": "Anomalías Filtradas", "Valor": quality_report.rejected_records},
        ])

        with pd.ExcelWriter(excel_file, engine="openpyxl") as writer:
            df_excel.to_excel(writer, sheet_name="Datos_Horarios_24h", index=False)
            df_kpis.to_excel(writer, sheet_name="Resumen_Ejecutivo", index=False)
        print(f"[OK] Libro Excel (.xlsx) generado en: {excel_file}")

        return evaluation_result, df_integrated, quality_report
