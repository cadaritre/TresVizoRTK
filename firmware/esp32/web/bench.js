"use strict";
// El banco USB tiene procedencia propia y no cambia el estado UART del firmware.
(() => {
  if (!["127.0.0.1", "localhost"].includes(location.hostname)) return;
  let since = 0, enabled = false, busy = false, catalogAt = 0;
  const format = (n, digits = 1) => Number.isFinite(n) ? n.toFixed(digits) : "—";
  async function request(path, body) {
    const response = await fetch(path, {method: body ? "POST" : "GET", cache: "no-store",
      headers: {"X-TresVizo-Client": "portal", "Content-Type": "application/json"},
      body: body ? JSON.stringify(body) : undefined, signal: AbortSignal.timeout(20000)});
    if (response.status === 404) return null;
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || "No se pudo completar la operación de banco.");
    return data;
  }
  function show(data) {
    const s = data.solution;
    if (!window.instrumentGnssEnabled) renderGnss({subsystems: {gnss: {state: data.state}}, solution: s});
    text("bench-state", data.state === "receiving" ? "USB recibiendo" : data.error || "Sin datos vigentes");
    text("bench-hz", `${format(data.measurement_hz)} Hz / ${format(data.arrival_hz)} Hz`);
    text("bench-sats", `${s.satellites_used ?? "—"} / ${format(s.hdop)}`);
    text("bench-age", `${data.age_ms ?? "—"} ms / ${s.correction_age_s ?? "—"} s`);
    text("bench-sigma", `${format(s.sigma_lat_m, 3)} / ${format(s.sigma_lon_m, 3)} / ${format(s.sigma_height_m, 3)} m`);
    text("bench-mode", data.mode || "Sin consultar");
    if (data.ntrip) text("bench-ntrip-state", `${data.ntrip.state} · ${data.ntrip.frames} tramas · ${data.ntrip.bytes} bytes`);
    if (data.caster) text("bench-caster-state", `${data.caster.state} · ${data.caster.clients ?? 0} rovers · ${data.caster.frames ?? 0} tramas`);
    if (!window.instrumentGnssEnabled && data.state === "receiving") text("gnss-description", "Fuente: GPS por USB a la Mac. Calidad reportada por el receptor.");
    // Rehacer solo la lista de señales a 1 Hz; solución y épocas se consultan aparte.
    if (Date.now() - catalogAt > 1000) {
      const rows = data.signals.map(signal => {
        const row = document.createElement("div"); row.className = "signal-row";
        const label = document.createElement("span");
        label.textContent = `${signal.constellation} ${signal.prn} · señal ${signal.signal_id || "—"}`;
        const bar = document.createElement("meter"); bar.min = 0; bar.max = 60; bar.value = signal.cn0_dbhz ?? 0;
        bar.setAttribute("aria-label", label.textContent + " C/N₀");
        const value = document.createElement("span"); value.textContent = `${signal.cn0_dbhz ?? "—"} dB-Hz`;
        row.append(label, bar, value); return row;
      });
      $("bench-signals").replaceChildren(...rows);
    }
  }
  async function sessions() {
    const data = await request("/api/bench/sessions");
    if (!data) return;
    const rows = data.sessions.map(session => {
      const row = document.createElement("p");
      row.textContent = `${session.name} · ${session.state} · ${session.bytes} bytes · pérdidas ${session.dropped_bytes} bytes `;
      if (!["recording", "closing", "error"].includes(session.state)) {
        const artifacts = [session.state === "interrupted" ? "stream.part" : "stream.bin", "manifest.json"];
        if (session.rinex_available) artifacts.push("observations.obs", "navigation.nav");
        for (const artifact of artifacts) {
          const link = document.createElement("a"); link.href = `/api/bench/file/${session.id}/${artifact}`;
          link.textContent = ` ${artifact} `;
          link.download = `${session.id}-${artifact}`; row.append(link);
        }
      }
      if (session.state === "closed" && !session.rinex_available) {
        const convert = document.createElement("button"); convert.className = "button secondary";
        convert.textContent = session.conversion_state === "running" ? "Convirtiendo…" : "Convertir a RINEX";
        convert.disabled = session.conversion_state === "running";
        convert.addEventListener("click", async () => {
          convert.disabled = true;
          try { await request("/api/bench/action", {action:"convert",session_id:session.id}); await sessions(); }
          catch (error) { text("bench-record-message",error.message); convert.disabled=false; }
        });
        row.append(convert);
      }
      if (session.conversion_error) row.append(document.createTextNode(session.conversion_error));
      return row;
    });
    $("bench-sessions").replaceChildren(...rows);
  }
  document.querySelectorAll("[data-bench-action]").forEach(button => button.addEventListener("click", async () => {
    if (busy) return;
    busy = true;
    document.querySelectorAll("[data-bench-action]").forEach(b => b.disabled = true);
    text("bench-message", "Esperando respuesta del receptor…");
    text("bench-record-message", "Procesando…");
    try {
      const body = {action: button.dataset.benchAction};
      if (body.action === "record_start") body.name = $("bench-session-name").value;
      const result = await request("/api/bench/action", body);
      if (!result) throw new Error("Banco USB no disponible.");
      const description = result.state === "confirmed" ? "Comandos confirmados por el receptor. Sin SAVECONFIG." :
        `Sesión: ${result.state}. Almacenamiento en la Mac.`;
      text("bench-message", description); text("bench-record-message", description);
      await sessions();
    } catch (error) {
      text("bench-message", error.message); text("bench-record-message", error.message); text("bench-corrections-message", error.message);
    } finally {
      busy = false;
      document.querySelectorAll("[data-bench-action]").forEach(b => b.disabled = false);
    }
  }));
  $("bench-base-apply").addEventListener("click", async () => {
    if (busy) return;
    if (!preparedBase?.request) { text("bench-base-message","Valida primero el plan con sus coordenadas y alturas."); return; }
    busy = true; $("bench-base-apply").disabled = true;
    try {
      const result = await request("/api/bench/base", preparedBase.request);
      if (!result) throw new Error("Banco no disponible.");
      text("bench-base-message",result.state === "confirmed" ? "Modo y coordenadas leídos del receptor. No se envió SAVECONFIG." : "Promedio iniciado. Todavía no hay coordenadas de base verificadas.");
    } catch (error) { text("bench-base-message",error.message); }
    finally { busy = false; $("bench-base-apply").disabled = false; }
  });
  for (const name of ["ntrip", "caster"]) $("bench-" + name + "-form").addEventListener("submit", async event => {
    event.preventDefault();
    if (busy) return;
    busy = true;
    const prefix = "bench-" + name + "-";
    const config = {host: $(prefix + "host").value, port: Number($(prefix + "port").value),
      mountpoint: $(prefix + "mount").value, username: $(prefix + "user").value,
      password: $(prefix + "password").value};
    if (name === "ntrip") Object.assign(config, {role: $(prefix + "role").value, tls: $(prefix + "tls").checked});
    else { config.source_password = $(prefix + "source").value; config.source = $(prefix + "kind").value; }
    try {
      const result = await request("/api/bench/action", {action: name + "_start", config});
      if (!result) throw new Error("Banco no disponible.");
      $(prefix + "password").value = "";
      if (name === "caster") $(prefix + "source").value = "";
      text("bench-corrections-message", "Solicitud recibida. Revisa el estado de conexión.");
    } catch (error) { text("bench-corrections-message", error.message); }
    finally { busy = false; }
  });
  async function pollBench() {
    let retry = 100;
    try {
      const data = await request(`/api/bench/gnss?since=${since}`);
      if (!data) { if (!enabled) return; throw new Error("Banco no disponible"); }
      enabled = true;
      window.benchActive = !window.instrumentGnssEnabled;
      $("bench-panel").hidden = $("bench-recording").hidden = $("bench-corrections").hidden = $("bench-base").hidden = false;
      since = data.sequence;
      show(data);
      if (Date.now() - catalogAt > 1000) {
        if (location.hash === "#recording") await sessions();
        catalogAt = Date.now();
      }
    } catch {
      if (enabled) {
        if (!window.instrumentGnssEnabled) renderGnss(null);
        text("bench-state", "Puente USB sin conexión");
        text("bench-hz", "—"); text("bench-sats", "—"); text("bench-age", "—"); text("bench-sigma", "—");
        $("bench-signals").replaceChildren();
      }
      retry = 1000;
    }
    setTimeout(pollBench, retry);
  }
  pollBench();
})();
