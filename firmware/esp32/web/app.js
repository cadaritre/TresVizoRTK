"use strict";
const $ = (id) => document.getElementById(id);
// Orden deliberado: lo que se usa parado en el terreno va primero; la plomería
// interna (UART, memoria, versiones) vive al final, en Diagnóstico.
const pageNames = {
  field: "Campo",
  base: "Base / rover",
  corrections: "Correcciones",
  recording: "Registro / PPK",
  gps: "GPS avanzado",
  connections: "Conexiones",
  settings: "Configuración",
  diagnostics: "Diagnóstico",
};
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
  if (!pageNames[page]) page = "field";
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
  $("offline-notice").hidden = ok || awaitingRestart;
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

  // --- Vista de campo -------------------------------------------------
  // Se lee de un vistazo y de lejos. Nunca muestra una posición que no esté
  // vigente: en el terreno una coordenada vieja es peor que ninguna.
  text("field-quality", current ? qualities[solution.fix] || "Sin datos" : state === "stale" ? "Datos antiguos" : "Sin solución");
  text("field-latitude", position ? `${solution.latitude_deg.toFixed(8)}°` : "—");
  text("field-longitude", position ? `${solution.longitude_deg.toFixed(8)}°` : "—");
  text("field-height", position && Number.isFinite(solution.height_m) ? `${solution.height_m.toFixed(3)} m` : "—");
  text("field-height-reference", !position ? "—" :
    solution.height_reference === "receiver_msl" ? "MSL del receptor" :
    solution.height_reference === "ellipsoidal_user_configured" ? "Elipsoidal configurada" : "Referencia no confirmada");
  text("field-satellites", current && Number.isFinite(solution.satellites_used) ? String(solution.satellites_used) : "—");
  text("field-hdop", current && Number.isFinite(solution.hdop) ? solution.hdop.toFixed(1) : "—");
  // Sigma declarada por el receptor, no exactitud comprobada. Se muestra en
  // metros porque es lo que se pregunta en campo; el matiz va en la nota.
  text("field-sigma-h", current && Number.isFinite(solution.horizontal_sigma_m)
    ? `${solution.horizontal_sigma_m.toFixed(3)} m` : "—");
  text("field-sigma-v", current && Number.isFinite(solution.vertical_sigma_m)
    ? `${solution.vertical_sigma_m.toFixed(3)} m` : "—");
  text("field-age", Number.isFinite(health?.age_ms) ? `${(health.age_ms / 1000).toFixed(1)} s` : "—");
  // Tramas RTCM entregadas al receptor: es el dato que dice si las correcciones
  // llegaron de verdad, no solo si el caster las envió.
  text("field-corrections", Number.isFinite(health?.correction_frames_sent) ? String(health.correction_frames_sent) : "—");
  renderFixBadge(current ? solution.fix : null, health?.correction_frames_sent);
}

// Indicador permanente de la cabecera. En campo la pregunta constante es "¿ya
// fijó?" y "¿me están llegando correcciones?", y no debe costar navegar.
let lastCorrectionFrames = null;
let lastCorrectionGrowth = 0;
function renderFixBadge(fix, frames) {
  const badge = $("fix-badge");
  const corrections = $("corrections-state");
  if (!badge || !corrections) return;
  // El receptor distingue más estados que los tres del rótulo: diferencial no es
  // RTK pero tampoco es autónoma, y ocultarlo engañaría.
  const map = {
    rtk_fixed: ["FIX", "fix"],
    rtk_float: ["FLOAT", "float"],
    differential: ["DGPS", "float"],
    standalone: ["SINGLE", "single"],
  };
  const [label, tone] = map[fix] || ["SIN FIX", "none"];
  badge.textContent = label;
  badge.className = `fix-badge ${tone}`;
  // "Recibiendo" se decide por tramas que de verdad entraron al GPS entre dos
  // sondeos, no por que el cliente NTRIP diga estar conectado.
  if (Number.isFinite(frames)) {
    if (lastCorrectionFrames !== null && frames > lastCorrectionFrames) {
      lastCorrectionGrowth = Date.now();
    }
    lastCorrectionFrames = frames;
  }
  const flowing = Date.now() - lastCorrectionGrowth < 8000;
  corrections.textContent = flowing
    ? "Recibiendo correcciones"
    : "Sin correcciones recibidas";
  corrections.className = `corrections-state ${flowing ? "ok" : "none"}`;
}

function renderStatus(data) {
  if (
    data.api_version !== 1 ||
    typeof data.uptime_ms !== "number" ||
    !data.wifi
  )
    throw new Error("Versión de protocolo no compatible.");
  latestStatus = data;
  window.instrumentGnssEnabled = !!data.subsystems?.gnss && data.subsystems.gnss.state !== "not_integrated";
  if (window.instrumentGnssEnabled) window.benchActive = false;
  if (!window.benchActive) renderGnss(data);
  refreshMs = [1000, 2000, 5000].includes(data.refresh_ms)
    ? data.refresh_ms
    : 2000;
  connected(true);
  text("device-name", data.device_name);
  const ble = data.subsystems?.ble;
  text("ble-state", ble?.state === "advertising" ? "Disponible para emparejar" : ble?.state === "authorized" ? "App autenticada" : ble?.state === "connected" ? "Cliente conectado" : "No disponible en este firmware");
  text("uptime", duration(data.uptime_ms));
  text("heap", kib(data.memory?.internal_free_bytes ?? data.free_heap_bytes));
  text("firmware", `v${data.firmware_version}`);
  // Del equipo, no escrita en el HTML: escribirla a mano ya provocó un desfase.
  text("sidebar-version", data.firmware_version || "—");
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
  text("diag-min-heap", kib(data.memory?.internal_min_free_bytes ?? data.min_free_heap_bytes));
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
    if (!config) await loadConfig();
  } catch {
    connected(false);
  } finally {
    polling = false;
    timer = setTimeout(poll, refreshMs);
  }
}
function fillConfig(value) {
  config = value;
  $("refresh-input").value = String(value.refresh_ms);
  $("ap-password-input").value = value.ap_password || "";
  renderSaved(value);
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
    refresh_ms: Number($("refresh-input").value),
    ap_password: $("ap-password-input").value,
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

// --- Redes Wi-Fi guardadas -------------------------------------------------
// El equipo se une solo, así que el panel no elige red: solo mantiene la lista
// y enseña lo que la radio ve de verdad.
let wifiBusy = false;
let wifiPending = null;
let wifiScanTimer = null;

function wifiMessage(value, error = false) {
  text("wifi-message", value);
  $("wifi-message").classList.toggle("error", error);
}
function signalLabel(rssi) {
  if (typeof rssi !== "number") return "señal desconocida";
  if (rssi >= -60) return "señal fuerte";
  if (rssi >= -70) return "señal media";
  if (rssi >= -80) return "señal débil";
  return "señal muy débil";
}
function listRow(label, button) {
  const row = document.createElement("li");
  const name = document.createElement("span");
  name.textContent = label;
  row.append(name, button);
  return row;
}
function renderSaved(value) {
  const list = $("wifi-saved-list");
  list.textContent = "";
  const saved = value && Array.isArray(value.networks) ? value.networks : [];
  const max = value && value.networks_max ? value.networks_max : 0;
  text("wifi-count", max ? `${saved.length} de ${max} guardadas` : "—");
  if (!saved.length) {
    const empty = document.createElement("li");
    empty.className = "hint";
    empty.textContent =
      "Ninguna guardada. Busca una red y añádela para que el equipo se conecte solo al encender.";
    list.append(empty);
    return;
  }
  saved.forEach((network) => {
    const forget = document.createElement("button");
    forget.type = "button";
    forget.className = "button secondary";
    forget.textContent = "Olvidar";
    forget.addEventListener("click", () => forgetNetwork(network.ssid));
    list.append(listRow(network.ssid, forget));
  });
}
async function forgetNetwork(ssid) {
  if (wifiBusy) return;
  wifiBusy = true;
  wifiMessage(`Olvidando ${ssid}…`);
  try {
    renderSaved(await api("/api/wifi/networks", "POST", { forget: ssid }));
    wifiMessage(`Se olvidó ${ssid}.`);
  } catch (error) {
    wifiMessage(error.message, true);
  } finally {
    wifiBusy = false;
  }
}
async function saveNetwork(ssid, password) {
  if (wifiBusy) return;
  wifiBusy = true;
  wifiMessage(`Guardando ${ssid}…`);
  try {
    renderSaved(await api("/api/wifi/networks", "POST", { ssid, password }));
    wifiMessage(`${ssid} guardada. El equipo intentará conectarse en unos segundos.`);
  } catch (error) {
    wifiMessage(error.message, true);
  } finally {
    wifiBusy = false;
  }
}
function renderScan(value) {
  const list = $("wifi-scan-list");
  if (value.state === "scanning") {
    text("wifi-scan-state", "Buscando redes…");
    return;
  }
  list.textContent = "";
  if (value.state === "failed") {
    text("wifi-scan-state", "La búsqueda falló. Vuelve a intentarlo.");
    return;
  }
  if (value.state !== "ready") {
    text("wifi-scan-state", "");
    return;
  }
  const found = Array.isArray(value.networks) ? value.networks : [];
  text(
    "wifi-scan-state",
    found.length
      ? `${found.length} a la vista${value.truncated ? ", lista recortada" : ""}.`
      : "No se vio ninguna red. Acerca el equipo o revisa que el hotspot sea de 2.4 GHz.",
  );
  found.forEach((network) => {
    const action = document.createElement("button");
    action.type = "button";
    action.className = "button secondary";
    if (!network.secure) {
      action.disabled = true;
      action.textContent = "Abierta";
    } else if (network.saved) {
      action.disabled = true;
      action.textContent = "Guardada";
    } else {
      action.textContent = "Añadir";
      action.addEventListener("click", () => askPassword(network.ssid));
    }
    list.append(listRow(`${network.ssid} · ${signalLabel(network.rssi_dbm)}`, action));
  });
}
async function pollScan() {
  try {
    const value = await api("/api/wifi/scan");
    renderScan(value);
    if (value.state === "scanning") {
      wifiScanTimer = setTimeout(pollScan, 1500);
      return;
    }
    $("wifi-scan").disabled = false;
  } catch (error) {
    $("wifi-scan").disabled = false;
    text("wifi-scan-state", error.message);
  }
}
function askPassword(ssid) {
  wifiPending = ssid;
  text("wifi-password-title", `Contraseña de ${ssid}`);
  $("wifi-password-value").value = "";
  $("wifi-password-dialog").showModal();
}
$("wifi-password-cancel").addEventListener("click", () => {
  wifiPending = null;
  $("wifi-password-value").value = "";
  $("wifi-password-dialog").close();
});
$("wifi-password-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const ssid = wifiPending;
  const password = $("wifi-password-value").value;
  wifiPending = null;
  $("wifi-password-value").value = "";
  $("wifi-password-dialog").close();
  if (ssid) saveNetwork(ssid, password);
});
$("wifi-scan").addEventListener("click", async () => {
  $("wifi-scan").disabled = true;
  text("wifi-scan-state", "Buscando redes…");
  clearTimeout(wifiScanTimer);
  try {
    renderScan(await api("/api/wifi/scan", "POST"));
    wifiScanTimer = setTimeout(pollScan, 1500);
  } catch (error) {
    $("wifi-scan").disabled = false;
    text("wifi-scan-state", error.message);
  }
});
