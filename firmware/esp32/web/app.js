"use strict";
const $ = (id) => document.getElementById(id);
const pageNames = {
  overview: "Resumen",
  connections: "Conexiones",
  base: "Base / rover",
  recording: "Registro / PPK",
  corrections: "Correcciones",
  settings: "Configuración",
  diagnostics: "Diagnóstico",
};
let accessKey = "";
let config = null;
let latestStatus = null;
let timer;
let polling = false;
let refreshMs = 2000;
let awaitingRestart = false;
let dirty = false;
let saving = false;

function message(value, error = false) {
  $("save-message").textContent = value;
  $("save-message").classList.toggle("error", error);
}
function goTo(page) {
  if (!pageNames[page]) page = "overview";
  document.querySelectorAll(".page").forEach((el) => {
    el.hidden = el.id !== `page-${page}`;
  });
  document.querySelectorAll(".nav-item").forEach((el) => {
    el.classList.toggle("active", el.dataset.page === page);
    if (el.dataset.page === page) el.setAttribute("aria-current", "page");
    else el.removeAttribute("aria-current");
  });
  $("page-title").textContent = pageNames[page];
  if (location.hash !== `#${page}`) history.replaceState(null, "", `#${page}`);
}
document
  .querySelectorAll("[data-page]")
  .forEach((el) => el.addEventListener("click", () => goTo(el.dataset.page)));
window.addEventListener("hashchange", () => goTo(location.hash.slice(1)));

async function api(path, method = "GET", body) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 7000);
  try {
    const headers = { "X-TresVizo-Client": "portal" };
    if (accessKey) headers["X-Device-Key"] = accessKey;
    if (body !== undefined) headers["Content-Type"] = "application/json";
    const response = await fetch(path, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
      cache: "no-store",
    });
    let data;
    try {
      data = await response.json();
    } catch {
      throw new Error("La respuesta del instrumento no es válida.");
    }
    if (response.status === 401) {
      if (!$("login-dialog").open) $("login-dialog").showModal();
      throw new Error("La clave del instrumento no es válida.");
    }
    if (!response.ok)
      throw new Error(data.message || "No se pudo completar la operación.");
    return data;
  } catch (error) {
    if (error.name === "AbortError")
      throw new Error("El instrumento no respondió a tiempo.");
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}
function text(id, value) {
  $(id).textContent = value;
}
function duration(ms) {
  const seconds = Math.floor(ms / 1000);
  return [
    Math.floor(seconds / 3600),
    Math.floor(seconds / 60) % 60,
    seconds % 60,
  ]
    .map((n) => String(n).padStart(2, "0"))
    .join(":");
}
const kib = (n) => `${Math.round(n / 1024)} KB`;
function connected(ok) {
  $("connection-pill").className =
    `connection-pill ${ok ? "online" : "offline"}`;
  text(
    "connection-text",
    ok
      ? "Instrumento conectado"
      : awaitingRestart
        ? "Reiniciando…"
        : "Sin conexión",
  );
  $("offline-notice").hidden = ok || awaitingRestart || $("login-dialog").open;
  $("save-settings").disabled =
    saving || !ok || !config || !config.persistence_ready;
  $("restart-button").disabled = !ok;
  $("export-diagnostics").disabled = !ok;
  if (!ok) {
    latestStatus = null;
    if (!window.benchActive) renderGnss(null);
    document.querySelectorAll("[data-live]").forEach((el) => {
      if (window.benchActive && el.id.startsWith("gnss-")) return;
      el.textContent = "—";
    });
    text("ap-state", "Sin comunicación");
    text("station-state", "Sin comunicación");
    text("ap-summary", "Esperando conexión");
    text("last-updated", "Sin datos actuales del equipo");
  }
}
function renderGnss(data) {
  const health = data?.subsystems?.gnss;
  const solution = data?.solution || {};
  const state = health?.state;
  const labels = {
    not_integrated: "Sin enlace GNSS", waiting_data: "Esperando datos",
    receiving: "Recibiendo", stale: "Datos antiguos", start_failed: "Error de UART",
  };
  const qualities = {
    invalid: "Sin solución", standalone: "Autónoma", differential: "Diferencial",
    pps: "PPS", rtk_fixed: "RTK fijo", rtk_float: "RTK flotante",
    dead_reckoning: "Estimada", manual: "Manual", simulated: "Simulada",
  };
  const current = state === "receiving";
  const position = current && Number.isFinite(solution.latitude_deg) && Number.isFinite(solution.longitude_deg);
  text("gnss-state", labels[state] || "Sin comunicación");
  text("gnss-title", position ? "Posición recibida" : "Aún no hay posición vigente");
  text("gnss-description", position ? "La calidad indicada por el receptor no garantiza la exactitud." :
    current ? "El receptor comunica, pero todavía no entrega una posición válida." :
    state === "stale" ? "Se detuvo la recepción. La posición anterior ya no está vigente." :
    "Esperando datos del receptor conectado al ESP32.");
  text("gnss-latitude", position ? `${solution.latitude_deg.toFixed(8)}°` : "—");
  text("gnss-longitude", position ? `${solution.longitude_deg.toFixed(8)}°` : "—");
  text("gnss-height", position && Number.isFinite(solution.height_m) ?
    `${solution.height_m.toFixed(3)} m · ${solution.height_reference === "receiver_msl" ? "MSL del receptor" : solution.height_reference === "ellipsoidal_user_configured" ? "Elipsoidal configurada" : "Referencia no confirmada"}` : "—");
  text("gnss-quality", current ? qualities[solution.fix] || "Sin datos" : "Sin datos vigentes");
}

function renderStatus(data) {
  if (
    data.api_version !== 1 ||
    typeof data.uptime_ms !== "number" ||
    !data.wifi
  )
    throw new Error("Versión de protocolo no compatible.");
  latestStatus = data;
  if (!window.benchActive) renderGnss(data);
  refreshMs = [1000, 2000, 5000].includes(data.refresh_ms)
    ? data.refresh_ms
    : 2000;
  connected(true);
  text("device-name", data.device_name);
  const ble = data.subsystems?.ble;
  text("ble-state", ble?.state === "advertising" ? "Disponible para emparejar" : ble?.state === "authorized" ? "App autenticada" : ble?.state === "connected" ? "Cliente conectado" : "No disponible en este firmware");
  text("uptime", duration(data.uptime_ms));
  text("heap", kib(data.free_heap_bytes));
  text("firmware", `v${data.firmware_version}`);
  text("ap-name", data.wifi.ap_ssid);
  text(
    "ap-summary",
    data.wifi.ap_ready
      ? `Panel en ${data.wifi.ap_ip}`
      : "No se pudo iniciar la red",
  );
  text("network-ap-name", data.wifi.ap_ssid);
  text("network-ap-ip", data.wifi.ap_ip);
  text("network-clients", String(data.wifi.ap_clients));
  text("ap-state", data.wifi.ap_ready ? "Activa" : "Error de arranque");
  const states = {
    connected: "Conectado",
    connecting: "Intentando conectar",
    not_configured: "Sin configurar",
  };
  text("station-state", states[data.wifi.station_state] || "Desconocido");
  text("station-ssid", data.wifi.station_ssid || "Sin configurar");
  text("station-ip", data.wifi.station_ip || "—");
  text(
    "station-rssi",
    data.wifi.rssi_dbm === null ? "—" : `${data.wifi.rssi_dbm} dBm`,
  );
  text("diag-chip", `${data.chip} · rev. ${data.chip_revision}`);
  text("diag-cpu", `${data.cpu_mhz} MHz`);
  text("diag-flash", `${data.flash_bytes / 1048576} MB`);
  text(
    "diag-psram",
    data.psram_enabled_bytes
      ? kib(data.psram_enabled_bytes)
      : "Desactivada en esta versión",
  );
  text("diag-min-heap", kib(data.min_free_heap_bytes));
  const reasons = {
    1: "Encendido",
    3: "Reinicio por software",
    4: "Excepción",
    5: "Watchdog de interrupción",
    6: "Watchdog de tarea",
    9: "Caída de tensión",
  };
  text(
    "diag-reset",
    reasons[data.reset_reason_code] || `Código ${data.reset_reason_code}`,
  );
  text("diag-config", data.config_ready ? "Disponible" : "Requiere atención");
  text(
    "last-updated",
    `Actualizado ${new Date().toLocaleTimeString("es-MX", { hour12: false })}`,
  );
}
async function poll() {
  if (polling || awaitingRestart) return;
  polling = true;
  clearTimeout(timer);
  try {
    renderStatus(await api("/api/status"));
    if (!config && !$("login-dialog").open) await loadConfig();
  } catch {
    connected(false);
  } finally {
    polling = false;
    timer = setTimeout(poll, refreshMs);
  }
}
function fillConfig(value) {
  config = value;
  $("device-name-input").value = value.device_name;
  $("refresh-input").value = String(value.refresh_ms);
  $("wifi-ssid-input").value = value.wifi_ssid;
  $("wifi-password-input").value = "";
  $("forget-wifi").checked = false;
  text(
    "password-help",
    value.wifi_password_saved
      ? "Ya hay una contraseña guardada. Deja vacío para conservarla si usas la misma red."
      : "Entre 8 y 63 caracteres. La contraseña no se devuelve al navegador.",
  );
  $("save-settings").disabled =
    saving || !latestStatus || !value.persistence_ready;
  dirty = false;
}
async function loadConfig() {
  try {
    fillConfig(await api("/api/config"));
    message(
      config.stored_config_valid
        ? "Ajustes cargados del instrumento."
        : "La configuración guardada no era válida. Revisa y guarda los ajustes.",
      !config.stored_config_valid,
    );
  } catch (error) {
    message(error.message, true);
  }
}
$("settings-form").addEventListener("input", () => {
  dirty = true;
  message("Tienes cambios sin guardar.");
});
$("reload-settings").addEventListener("click", loadConfig);
$("settings-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!config || saving) return;
  saving = true;
  $("save-settings").disabled = true;
  $("reload-settings").disabled = true;
  message("Guardando en el instrumento…");
  const body = {
    revision: config.revision,
    device_name: $("device-name-input").value,
    refresh_ms: Number($("refresh-input").value),
    wifi_ssid: $("wifi-ssid-input").value,
    wifi_password: $("wifi-password-input").value,
    forget_wifi: $("forget-wifi").checked,
  };
  try {
    fillConfig(await api("/api/config", "PUT", body));
    message("Ajustes guardados en el instrumento.");
    poll();
  } catch (error) {
    message(error.message, true);
  } finally {
    saving = false;
    $("reload-settings").disabled = false;
    $("save-settings").disabled = !latestStatus || !config.persistence_ready;
  }
});
$("login-dialog").addEventListener("cancel", (event) => event.preventDefault());
$("login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  accessKey = $("access-key").value.trim();
  text("login-message", "Verificando…");
  try {
    const status = await api("/api/status");
    $("login-dialog").close();
    $("access-key").value = "";
    text("login-message", "");
    renderStatus(status);
    await loadConfig();
  } catch (error) {
    accessKey = "";
    text("login-message", error.message);
  }
});
$("restart-button").addEventListener("click", () =>
  $("restart-dialog").showModal(),
);
$("cancel-restart").addEventListener("click", () =>
  $("restart-dialog").close(),
);
$("confirm-restart").addEventListener("click", async () => {
  $("confirm-restart").disabled = true;
  awaitingRestart = true;
  clearTimeout(timer);
  try {
    await api("/api/restart", "POST", {});
    $("restart-dialog").close();
    config = null;
    dirty = false;
    connected(false);
    setTimeout(() => {
      awaitingRestart = false;
      poll();
    }, 4000);
  } catch (error) {
    awaitingRestart = false;
    $("restart-dialog").close();
    message(error.message, true);
    goTo("settings");
    poll();
  } finally {
    $("confirm-restart").disabled = false;
  }
});
$("export-diagnostics").addEventListener("click", () => {
  if (!latestStatus) return;
  // Excluir redes y nombres para un diagnóstico compartible.
  const data = JSON.parse(JSON.stringify(latestStatus));
  delete data.wifi;
  delete data.device_name;
  delete data.solution;
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = `tresvizo-diagnostic-${new Date().toISOString().slice(0, 10)}.json`;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
window.addEventListener("beforeunload", (event) => {
  if (dirty) {
    event.preventDefault();
    event.returnValue = "";
  }
});
goTo(location.hash.slice(1));
poll();


let preparedBase = null;
function invalidateBasePlan() {
  preparedBase = null;
  $("base-export").disabled = true;
  text("base-result", "Cambios sin validar. El plan no se guarda ni aplica al equipo.");
}
$("base-plan-form").addEventListener("input", invalidateBasePlan);
$("base-method").addEventListener("change", () => {
  const known = $("base-method").value === "known";
  $("base-known").hidden = !known;
  $("base-known").disabled = !known;
  $("base-average").hidden = known;
  $("base-average").disabled = known;
  invalidateBasePlan();
});
$("base-plan-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const method = $("base-method").value;
  const plan = { method, station_id: Number($("base-id").value) };
  if (method === "known") Object.assign(plan, {
    latitude_deg: Number($("base-lat").value), longitude_deg: Number($("base-lon").value),
    datum: $("base-datum").value.trim(), coordinate_epoch: $("base-epoch").value === "" ? null : Number($("base-epoch").value),
    height_point: $("base-height-point").value, ellipsoid_height_m: Number($("base-height").value),
    antenna_vertical_m: Number($("base-antenna").value),
  });
  else Object.assign(plan, { average_seconds: Number($("base-seconds").value), reuse_distance_m: Number($("base-reuse").value) });
  const marker = ++basePlanRequest;
  try {
    const result = await api("/api/base/plan", "POST", plan);
    if (marker !== basePlanRequest) return;
    preparedBase = {...result, request: plan};
    $("base-export").disabled = false;
    text("base-result", result.message + (result.plan.arp_ellipsoid_height_m !== undefined ?
      ` Altura elipsoidal ARP: ${result.plan.arp_ellipsoid_height_m.toFixed(4)} m.` :
      " El promedio no garantiza exactitud absoluta."));
  } catch (error) {
    if (marker !== basePlanRequest) return;
    preparedBase = null;
    $("base-export").disabled = true;
    text("base-result", error.message);
  }
});
let basePlanRequest = 0;
$("base-plan-form").addEventListener("input", () => { ++basePlanRequest; });
$("base-plan-form").addEventListener("change", () => { ++basePlanRequest; });
$("base-export").addEventListener("click", () => {
  if (!preparedBase) return;
  const url = URL.createObjectURL(new Blob([JSON.stringify(preparedBase, null, 2)], { type: "application/json" }));
  const link = document.createElement("a");
  link.href = url; link.download = "tresvizo-base-plan.json"; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});

$("correction-source-form").addEventListener("submit", async event => {
  event.preventDefault();
  try {
    const result = await api("/api/corrections/source","PUT",{source:$("correction-source").value});
    text("correction-source-message", `Fuente seleccionada: ${result.active_source}. ${result.receiver_ready ? "UART disponible." : "GPS–ESP32 sin conectar; aún no se entregan correcciones."}`);
  } catch (error) { text("correction-source-message",error.message); }
});
