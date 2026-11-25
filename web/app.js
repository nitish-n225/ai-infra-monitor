// AegisLog SIEM Dashboard Client Logic
let socket = null;
let reconnectTimer = null;
let isStreamPaused = false;

// In-memory data store for UI
let logBuffer = [];
const MAX_LOGS = 60;
let alertsList = [];

// Chart instances
let threatChart = null;
let velocityChart = null;
const velocityData = {
  labels: [],
  normalCounts: [],
  threatCounts: []
};
const MAX_VELOCITY_POINTS = 12;

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  initCharts();
  connectWebSocket();
  bindSimulationButtons();
  bindControls();
  fetchInitialData();
});

// ----------------- WebSocket Communication -----------------
function connectWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws/logs`;

  const statusPill = document.getElementById("connectionStatus");
  const statusText = document.getElementById("connectionText");

  try {
    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      console.log("WebSocket connected.");
      statusPill.className = "status-pill connected";
      statusText.textContent = "LIVE MONITORING";
      if (reconnectTimer) {
        clearInterval(reconnectTimer);
        reconnectTimer = null;
      }
    };

    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        handleSocketMessage(message);
      } catch (e) {
        console.error("Failed to parse socket message:", e);
      }
    };

    socket.onclose = () => {
      console.warn("WebSocket closed. Attempting reconnect...");
      statusPill.className = "status-pill disconnected";
      statusText.textContent = "OFFLINE (RECONNECTING)";
      scheduleReconnect();
    };

    socket.onerror = (err) => {
      console.error("WebSocket error:", err);
      try { socket.close(); } catch(e) {}
    };
  } catch (err) {
    scheduleReconnect();
  }
}

// Keepalive ping to prevent idle timeout
setInterval(() => {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send("ping");
  }
}, 10000);

function scheduleReconnect() {
  if (!reconnectTimer) {
    reconnectTimer = setInterval(() => {
      connectWebSocket();
    }, 2500);
  }
}

function handleSocketMessage(msg) {
  if (msg.type === "INIT") {
    updateKPIs(msg.stats);
    updateThreatChart(msg.stats.threat_distribution);
  } else if (msg.type === "NEW_LOG") {
    handleNewLog(msg.data);
    if (msg.stats) {
      updateKPIs(msg.stats);
      updateThreatChart(msg.stats.threat_distribution);
    }
  } else if (msg.type === "RESET") {
    logBuffer = [];
    alertsList = [];
    renderLogsTable();
    renderAlertsFeed();
    updateKPIs(msg.stats);
    updateThreatChart({});
  }
}

// ----------------- UI & Data Handlers -----------------
function handleNewLog(log) {
  logBuffer.unshift(log);
  if (logBuffer.length > MAX_LOGS) {
    logBuffer.pop();
  }
  renderLogsTable();

  // If this log produced an alert or is a threat
  if (log.is_threat && log.threat_details) {
    const alertItem = {
      id: log.alert_id || Date.now(),
      timestamp: log.timestamp,
      client_ip: log.client_ip,
      threat_type: log.threat_type,
      severity: log.severity,
      threat_source: log.threat_source,
      details: log.threat_details.details,
      recommendation: log.threat_details.recommendation,
      status: "ACTIVE"
    };
    alertsList.unshift(alertItem);
    if (alertsList.length > 30) alertsList.pop();
    renderAlertsFeed();
  }

  // Update velocity chart
  recordVelocity(log.is_threat);
}

function updateKPIs(stats) {
  if (!stats) return;

  document.getElementById("valTotalLogs").textContent = (stats.total_logs || 0).toLocaleString();
  document.getElementById("valThreatLogs").textContent = (stats.threat_logs || 0).toLocaleString();
  document.getElementById("valActiveAlerts").textContent = stats.active_alerts || 0;
  document.getElementById("valCriticalAlerts").textContent = `${stats.critical_alerts || 0} Critical Incidents`;

  const total = stats.total_logs || 0;
  const threats = stats.threat_logs || 0;
  const pct = total > 0 ? ((threats / total) * 100).toFixed(1) : "0.0";
  document.getElementById("valThreatPercent").textContent = `${pct}% of total traffic`;

  document.getElementById("alertsCountBadge").textContent = stats.active_alerts || 0;
}

function renderLogsTable() {
  const tbody = document.getElementById("logTableBody");
  const searchTerm = (document.getElementById("logSearchInput").value || "").toLowerCase();
  const threatsOnly = document.getElementById("threatsOnlyToggle").checked;

  const filtered = logBuffer.filter((log) => {
    if (threatsOnly && !log.is_threat) return false;
    if (!searchTerm) return true;
    return (
      (log.client_ip && log.client_ip.toLowerCase().includes(searchTerm)) ||
      (log.endpoint && log.endpoint.toLowerCase().includes(searchTerm)) ||
      (log.method && log.method.toLowerCase().includes(searchTerm)) ||
      (log.threat_type && log.threat_type.toLowerCase().includes(searchTerm))
    );
  });

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 2rem; color: #64748b;">No matching logs found.</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.map((log) => {
    const isThreat = log.is_threat === 1;
    const timeFormatted = log.timestamp ? log.timestamp.substring(11, 19) : "--:--:--";
    const statusClass = getStatusClass(log.status_code);
    const sourceClass = log.threat_source === "ML_ISOLATION_FOREST" ? "source-ml" : (log.threat_source === "RULE_ENGINE" ? "source-rule" : "");

    return `
      <tr class="${isThreat ? 'log-threat-row' : ''}">
        <td>${timeFormatted}</td>
        <td style="color:#38bdf8;">${escapeHtml(log.client_ip || '127.0.0.1')}</td>
        <td><strong>${escapeHtml(log.method || 'GET')}</strong></td>
        <td style="max-width:240px; overflow:hidden; text-overflow:ellipsis;" title="${escapeHtml(log.endpoint)}">
          ${escapeHtml(log.endpoint || '/')}
        </td>
        <td><span class="status-badge ${statusClass}">${log.status_code || 200}</span></td>
        <td>
          ${isThreat 
            ? `<span class="tag-threat">🚨 ${escapeHtml(log.threat_type)}</span>` 
            : `<span class="tag-normal">NORMAL</span>`}
        </td>
        <td>
          <span class="source-badge ${sourceClass}">${escapeHtml(log.threat_source || 'NONE')}</span>
        </td>
      </tr>
    `;
  }).join("");
}

function renderAlertsFeed() {
  const container = document.getElementById("alertsFeedList");
  if (!alertsList || alertsList.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <span class="empty-icon">🛡️</span>
        <p>No active threats detected. System is secure.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = alertsList.map((a) => {
    const sevClass = (a.severity || "MEDIUM").toLowerCase();
    const time = a.timestamp ? a.timestamp.substring(11, 19) : "";

    return `
      <div class="alert-item alert-${sevClass}" id="alert-card-${a.id}">
        <div class="alert-header">
          <span class="alert-severity-badge badge-${sevClass}">${a.severity}</span>
          <span class="alert-time">${time}</span>
        </div>
        <div class="alert-title">${escapeHtml(a.threat_type)}</div>
        <div class="alert-detail">${escapeHtml(a.details)}</div>
        <div class="alert-footer">
          <span class="alert-ip">IP: ${escapeHtml(a.client_ip)}</span>
          <button class="btn-resolve" onclick="resolveAlert(${a.id})">✓ Resolve</button>
        </div>
      </div>
    `;
  }).join("");
}

function getStatusClass(status) {
  if (status >= 200 && status < 300) return "status-2xx";
  if (status >= 300 && status < 400) return "status-3xx";
  if (status >= 400 && status < 500) return "status-4xx";
  return "status-5xx";
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// ----------------- Chart.js Visualizations -----------------
function initCharts() {
  // 1. Doughnut Chart: Threat Distribution
  const ctxThreat = document.getElementById("threatDistributionChart").getContext("2d");
  threatChart = new Chart(ctxThreat, {
    type: "doughnut",
    data: {
      labels: ["Normal"],
      datasets: [{
        data: [1],
        backgroundColor: [
          "#10b981", "#ef4444", "#f59e0b", "#f97316",
          "#a855f7", "#ec4899", "#3b82f6"
        ],
        borderWidth: 2,
        borderColor: "#0f172a"
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "right",
          labels: { color: "#94a3b8", font: { family: "Inter", size: 11 } }
        }
      },
      cutout: "68%"
    }
  });

  // 2. Line Chart: Velocity
  const ctxVelocity = document.getElementById("trafficVelocityChart").getContext("2d");
  velocityChart = new Chart(ctxVelocity, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: "Normal Requests",
          data: [],
          borderColor: "#06b6d4",
          backgroundColor: "rgba(6, 182, 212, 0.1)",
          fill: true,
          tension: 0.35,
          borderWidth: 2
        },
        {
          label: "Detected Threats",
          data: [],
          borderColor: "#ef4444",
          backgroundColor: "rgba(239, 68, 68, 0.15)",
          fill: true,
          tension: 0.35,
          borderWidth: 2
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          grid: { color: "rgba(255,255,255,0.04)" },
          ticks: { color: "#64748b", font: { size: 10 } }
        },
        y: {
          beginAtZero: true,
          grid: { color: "rgba(255,255,255,0.04)" },
          ticks: { color: "#64748b", font: { size: 10 }, stepSize: 1 }
        }
      },
      plugins: {
        legend: {
          labels: { color: "#94a3b8", font: { family: "Inter", size: 11 } }
        }
      }
    }
  });
}

function updateThreatChart(distribution) {
  if (!threatChart) return;
  const labels = Object.keys(distribution);
  const data = Object.values(distribution);

  if (labels.length === 0) {
    threatChart.data.labels = ["Normal Traffic"];
    threatChart.data.datasets[0].data = [1];
    threatChart.data.datasets[0].backgroundColor = ["#10b981"];
  } else {
    threatChart.data.labels = labels;
    threatChart.data.datasets[0].data = data;
    threatChart.data.datasets[0].backgroundColor = [
      "#ef4444", "#f59e0b", "#f97316", "#a855f7",
      "#ec4899", "#dc2626", "#06b6d4"
    ];
  }
  threatChart.update();
}

let tempNormalCounter = 0;
let tempThreatCounter = 0;

function recordVelocity(isThreat) {
  if (isThreat) tempThreatCounter++;
  else tempNormalCounter++;
}

// Periodically push point to velocity chart every 3 seconds
setInterval(() => {
  if (!velocityChart) return;
  const timeLabel = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

  if (velocityChart.data.labels.length >= MAX_VELOCITY_POINTS) {
    velocityChart.data.labels.shift();
    velocityChart.data.datasets[0].data.shift();
    velocityChart.data.datasets[1].data.shift();
  }

  velocityChart.data.labels.push(timeLabel);
  velocityChart.data.datasets[0].data.push(tempNormalCounter);
  velocityChart.data.datasets[1].data.push(tempThreatCounter);
  velocityChart.update();

  tempNormalCounter = 0;
  tempThreatCounter = 0;
}, 3000);

// ----------------- Simulation & Controls -----------------
function bindSimulationButtons() {
  const buttons = document.querySelectorAll(".sim-btn");
  buttons.forEach((btn) => {
    btn.addEventListener("click", async () => {
      const attackType = btn.dataset.attack;
      try {
        btn.style.opacity = "0.5";
        await fetch(`/api/simulate/${attackType}`, { method: "POST" });
      } catch (e) {
        console.error("Simulation failed:", e);
      } finally {
        setTimeout(() => { btn.style.opacity = "1"; }, 300);
      }
    });
  });
}

function bindControls() {
  document.getElementById("logSearchInput").addEventListener("input", renderLogsTable);
  document.getElementById("threatsOnlyToggle").addEventListener("change", renderLogsTable);

  document.getElementById("toggleStreamBtn").addEventListener("click", async () => {
    const res = await fetch("/api/stream/toggle", { method: "POST" });
    const data = await res.json();
    isStreamPaused = !data.background_streaming;
    const btn = document.getElementById("toggleStreamBtn");
    if (isStreamPaused) {
      btn.innerHTML = `<span class="btn-icon">▶</span> Resume Stream`;
      btn.classList.add("btn-paused");
    } else {
      btn.innerHTML = `<span class="btn-icon">⏸</span> Pause Stream`;
      btn.classList.remove("btn-paused");
    }
  });

  document.getElementById("clearDataBtn").addEventListener("click", async () => {
    if (confirm("Reset all stored logs and alerts for a fresh presentation?")) {
      await fetch("/api/clear", { method: "POST" });
    }
  });
}

window.resolveAlert = async function(alertId) {
  try {
    await fetch(`/api/alerts/${alertId}/resolve`, { method: "POST" });
    alertsList = alertsList.filter((a) => a.id !== alertId);
    renderAlertsFeed();
    const statsRes = await fetch("/api/stats");
    const stats = await statsRes.json();
    updateKPIs(stats);
  } catch (err) {
    console.error("Failed to resolve alert:", err);
  }
};

async function fetchInitialData() {
  try {
    const [statsRes, logsRes, alertsRes] = await Promise.all([
      fetch("/api/stats"),
      fetch("/api/logs?limit=40"),
      fetch("/api/alerts?limit=20")
    ]);
    const stats = await statsRes.json();
    const logs = await logsRes.json();
    const alerts = await alertsRes.json();

    updateKPIs(stats);
    updateThreatChart(stats.threat_distribution);

    logBuffer = logs || [];
    alertsList = alerts || [];
    renderLogsTable();
    renderAlertsFeed();
  } catch (err) {
    console.error("Initial data load error:", err);
  }
}
