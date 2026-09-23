/**
 * Lógica del Cliente - Dashboard Interactivo del Parque Eólico Windpeshi
 */

document.addEventListener("DOMContentLoaded", () => {
  const datePicker = document.getElementById("datePicker");
  const btnEvaluate = document.getElementById("btnEvaluate");
  const loadingOverlay = document.getElementById("loadingOverlay");
  const resultsSection = document.getElementById("resultsSection");

  // Elementos del Banner de Veredicto
  const verdictBanner = document.getElementById("verdictBanner");
  const verdictTitle = document.getElementById("verdictTitle");
  const verdictSubtitle = document.getElementById("verdictSubtitle");
  const verdictIcon = document.getElementById("verdictIcon");
  const displayTargetDate = document.getElementById("displayTargetDate");

  // Elementos de KPIs
  const kpiAvgSpeed = document.getElementById("kpiAvgSpeed");
  const kpiHistoricalP50 = document.getElementById("kpiHistoricalP50");
  const kpiOperatingHours = document.getElementById("kpiOperatingHours");
  const kpiEnergyMwh = document.getElementById("kpiEnergyMwh");
  const kpiQualityPct = document.getElementById("kpiQualityPct");
  const kpiQualityAnomalies = document.getElementById("kpiQualityAnomalies");

  // Justificación y Tabla
  const reasonsList = document.getElementById("reasonsList");
  const hourlyTableBody = document.getElementById("hourlyTableBody");

  // 1. Inicializar con la fecha de hoy
  const today = new Date().toISOString().split("T")[0];
  datePicker.value = today;

  // 2. Función para consultar el pipeline al backend
  async function evaluateDate(targetDate) {
    if (!targetDate) {
      alert("Por favor selecciona una fecha válida.");
      return;
    }

    // Activar estado de carga
    loadingOverlay.classList.remove("hidden");
    resultsSection.classList.add("hidden");
    btnEvaluate.disabled = true;

    try {
      const response = await fetch(`/api/evaluate?date=${encodeURIComponent(targetDate)}`);
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `Error HTTP ${response.status}`);
      }

      const data = await response.json();
      renderDashboard(data);
    } catch (error) {
      console.error("Error al evaluar:", error);
      alert(`Ocurrió un error al procesar el pipeline: ${error.message}`);
    } finally {
      loadingOverlay.classList.add("hidden");
      resultsSection.classList.remove("hidden");
      btnEvaluate.disabled = false;
    }
  }

  // 3. Renderizar los datos en la interfaz
  function renderDashboard(data) {
    displayTargetDate.textContent = `Jornada: ${data.target_date}`;

    // Actualizar enlaces de descarga
    const btnDownloadCsv = document.getElementById("btnDownloadCsv");
    const btnDownloadExcel = document.getElementById("btnDownloadExcel");
    if (btnDownloadCsv) {
      btnDownloadCsv.href = `/api/download?type=csv&date=${encodeURIComponent(data.target_date)}`;
      btnDownloadCsv.setAttribute("download", `integrated_${data.target_date}.csv`);
    }
    if (btnDownloadExcel) {
      btnDownloadExcel.href = `/api/download?type=excel&date=${encodeURIComponent(data.target_date)}`;
      btnDownloadExcel.setAttribute("download", `integrated_${data.target_date}.xlsx`);
    }

    // A. Veredicto
    const isFavorable = data.verdict === "DÍA FAVORABLE";
    verdictBanner.className = `verdict-banner ${isFavorable ? "verdict-favorable" : "verdict-unfavorable"}`;
    verdictTitle.textContent = data.verdict;
    verdictIcon.textContent = isFavorable ? "⚡" : "⚠️";
    verdictSubtitle.textContent = isFavorable
      ? "Condiciones meteorológicas excelentes para la inyección de energía a la red eléctrica nacional."
      : "Condiciones no aptas: recurso eólico insuficiente o riesgo meteorológico en aerogeneradores.";

    // B. KPIs
    kpiAvgSpeed.textContent = data.avg_integrated_speed_ms;
    kpiHistoricalP50.textContent = `Mediana Histórica (P50): ${data.historical_p50_benchmark_ms} m/s`;
    kpiOperatingHours.textContent = data.operating_hours;
    kpiEnergyMwh.textContent = data.estimated_daily_energy_mwh;
    kpiQualityPct.textContent = data.quality.valid_percentage;

    const anomaliesList = Object.entries(data.quality.anomalies)
      .map(([k, v]) => `${v} ${k}`)
      .join(", ");
    kpiQualityAnomalies.textContent = anomaliesList
      ? `Anomalías filtradas: ${anomaliesList}`
      : "0 anomalías detectadas (sensor 100% íntegro)";

    // C. Justificaciones Técnicas
    reasonsList.innerHTML = "";
    data.reasons.forEach((reason) => {
      const li = document.createElement("li");
      li.textContent = reason;
      reasonsList.appendChild(li);
    });

    // D. Tabla de 24 Horas
    hourlyTableBody.innerHTML = "";
    data.hourly_data.forEach((row) => {
      const tr = document.createElement("tr");

      const hourStr = `${String(row.hour).padStart(2, "0")}:00`;
      const sensorMean = row.sensor_speed_mean_ms != null ? `${row.sensor_speed_mean_ms.toFixed(2)} m/s` : "N/A";
      const sensorGust = row.sensor_gust_max_ms != null ? `${row.sensor_gust_max_ms.toFixed(2)} m/s` : "N/A";
      const forecastSpeed = row.forecast_wind_speed_ms != null ? `${row.forecast_wind_speed_ms.toFixed(2)} m/s` : "N/A";
      const p50 = row.hist_wind_p50 != null ? `${row.hist_wind_p50.toFixed(2)} m/s` : "N/A";
      const temp = row.forecast_temperature_c != null ? `${row.forecast_temperature_c.toFixed(1)} °C` : "--";

      // Determinar badge de estado operativo
      const speed = row.sensor_speed_mean_ms || row.forecast_wind_speed_ms || 0;
      let badgeClass = "status-optimal";
      let statusText = "Operación Óptima";

      if (speed < 3.5) {
        badgeClass = "status-sub";
        statusText = "Sub-Arranque";
      } else if (speed >= 12.0 && speed <= 25.0) {
        badgeClass = "status-max";
        statusText = "Generación Máx";
      } else if (speed > 25.0) {
        badgeClass = "status-risk";
        statusText = "Freno Emergencia";
      }

      tr.innerHTML = `
        <td><strong>${hourStr}</strong></td>
        <td>${sensorMean}</td>
        <td><span style="color: #38bdf8;">${sensorGust}</span></td>
        <td>${forecastSpeed}</td>
        <td>${p50}</td>
        <td>${temp}</td>
        <td><span class="status-pill ${badgeClass}">${statusText}</span></td>
      `;

      hourlyTableBody.appendChild(tr);
    });
  }

  // 4. Listeners de eventos
  btnEvaluate.addEventListener("click", () => {
    evaluateDate(datePicker.value);
  });

  datePicker.addEventListener("change", () => {
    evaluateDate(datePicker.value);
  });

  // Ejecución inicial automática
  evaluateDate(today);
});
