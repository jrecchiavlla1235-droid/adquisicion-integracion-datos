"""
Simulador de sensor anemómetro/veleta IoT para la Fuente 1.
Genera lecturas cada 10 minutos con variación diurna y posibles anomalías para el filtro de calidad.
"""

from datetime import datetime
import numpy as np
import pandas as pd
import pytz
from config.settings import SENSOR_CONFIG, WINDPESHI_LOCATION


class AnemometerIoTSensor:
    """
    Simulador de estación meteorológica y anemómetro IoT instalado en torre de medición.
    Emite lecturas cada 10 minutos (144 paquetes de telemetría por día).
    """

    def __init__(self, sensor_id: str = "ANEMO-WINDPESHI-01", seed: int | None = None):
        self.sensor_id = sensor_id
        self.timezone = pytz.timezone(WINDPESHI_LOCATION["timezone"])
        if seed is not None:
            np.random.seed(seed)

    def generate_single_reading(
        self,
        current_time: datetime,
        base_wind_speed: float = 8.5,
        inject_anomaly: bool = False,
    ) -> dict:
        """
        Genera un paquete de telemetría individual para un instante en el tiempo.
        """
        if inject_anomaly:
            # Tipos de fallas típicas en sensores IoT en campo:
            anomaly_type = np.random.choice(["negative_speed", "spike_sensor_freeze", "pressure_drop"])
            if anomaly_type == "negative_speed":
                wind_speed = -3.2  # Imposible físicamente (falla de polaridad/voltaje)
                pressure = 1010.5
            elif anomaly_type == "spike_sensor_freeze":
                wind_speed = 99.9  # Púa irreal de lectura por desconexión de bus
                pressure = 1011.0
            else:
                wind_speed = base_wind_speed
                pressure = 450.0   # Presión imposible a nivel del mar (vacío o sensor averiado)
        else:
            # Lectura normal con ruido físico del sensor
            noise = np.random.normal(0, SENSOR_CONFIG["simulated_noise_std"])
            wind_speed = max(0.0, round(base_wind_speed + noise, 2))
            pressure = round(1011.5 + np.random.normal(0, 0.8), 1)

        direction = round((70.0 + np.random.normal(0, 10.0)) % 360, 1)

        return {
            "sensor_id": self.sensor_id,
            "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S%z"),
            "wind_speed_ms": wind_speed,
            "wind_direction_deg": direction,
            "pressure_hpa": pressure,
            "battery_pct": round(np.random.uniform(92.0, 99.5), 1),
            "firmware_version": "v2.4.1",
        }

    def simulate_day_stream(
        self,
        target_date: str,
        allow_anomalies: bool = True,
    ) -> pd.DataFrame:
        """
        Simula una jornada completa de 24 horas de telemetría (cada 10 minutos = 144 lecturas).
        
        Args:
            target_date: Fecha a simular en formato 'YYYY-MM-DD'.
            allow_anomalies: Si es True, permite inyección esporádica de fallas para probar el pipeline.
            
        Returns:
            pd.DataFrame con la secuencia temporal de telemetría cruda.
        """
        start_dt = pd.Timestamp(f"{target_date} 00:00:00", tz=WINDPESHI_LOCATION["timezone"])
        end_dt = pd.Timestamp(f"{target_date} 23:50:00", tz=WINDPESHI_LOCATION["timezone"])
        
        timestamps = pd.date_range(start=start_dt, end=end_dt, freq="10min")
        readings = []

        for ts in timestamps:
            # Variación diurna: mayor viento al final de la tarde
            hour = ts.hour
            base_speed = 9.0 + 3.0 * np.sin((hour - 8) * np.pi / 12) + np.random.normal(0, 0.8)
            base_speed = max(1.0, base_speed)

            # Decidir si esta muestra contendrá una anomalía
            has_anomaly = (
                allow_anomalies and np.random.rand() < SENSOR_CONFIG["anomaly_probability"]
            )
            
            reading = self.generate_single_reading(
                current_time=ts.to_pydatetime(),
                base_wind_speed=base_speed,
                inject_anomaly=has_anomaly,
            )
            readings.append(reading)

        return pd.DataFrame(readings)
