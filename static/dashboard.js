(function initializeLatencyChart() {
  const chartCanvas = document.getElementById('latencyChart');
  const latencyData = Array.isArray(window.latencyData) ? window.latencyData : [];

  if (!chartCanvas || !latencyData.length || typeof window.Chart !== 'function') {
    return;
  }

  const chartData = latencyData.filter(item => (
    item && typeof item.time === 'string' && typeof item.device === 'string'
    && Number.isFinite(Number(item.latency))
  ));

  if (!chartData.length) {
    return;
  }

  const labels = chartData.map(item => `${item.time} ${item.device}`);
  const latencyValues = chartData.map(item => Number(item.latency));
  const latencyThreshold = Number.isFinite(Number(window.latencyThreshold))
    ? Number(window.latencyThreshold)
    : 0;

  if (window.latencyChart instanceof window.Chart) {
    window.latencyChart.destroy();
  }

  window.latencyChart = new window.Chart(chartCanvas, {
    type: 'line',
    data: {
      labels,
      datasets: [
        { label: 'Latency (ms)', data: latencyValues, borderColor: '#0f766e', backgroundColor: 'rgba(15, 118, 110, .12)', fill: true, tension: .35, pointRadius: 3, pointBackgroundColor: '#0f766e' },
        { label: 'Alert threshold', data: labels.map(() => latencyThreshold), borderColor: '#d97706', borderDash: [6, 5], borderWidth: 2, pointRadius: 0, fill: false, tension: 0 }
      ]
    },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: true, align: 'end', labels: { usePointStyle: true, boxWidth: 7 } }, tooltip: { callbacks: { label: context => `${context.dataset.label}: ${context.parsed.y} ms` } } }, scales: { y: { beginAtZero: true, grid: { color: '#e5e7eb' }, title: { display: true, text: 'Milliseconds' } }, x: { display: false } } }
  });
})();
