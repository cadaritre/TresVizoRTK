"use strict";
// Configuracion avanzada del receptor. Cada formulario envia una sola operacion
// al gestor de comandos del firmware y espera su confirmacion; no hay consola
// libre ni comandos compuestos desde el navegador.
(() => {
  const SYSTEMS = [
    ["gps", "gps-sys-gps", "GPS"],
    ["bds", "gps-sys-bds", "BeiDou"],
    ["glo", "gps-sys-glo", "GLONASS"],
    ["gal", "gps-sys-gal", "Galileo"],
    ["qzss", "gps-sys-qzss", "QZSS"],
  ];
  let pending = false;

  // Envia la operacion y espera a que el trabajo salga de "running". Reportar
  // "enviado" no basta: el receptor puede rechazar el comando o no contestar.
  async function submit(body, target) {
    if (pending) return;
    pending = true;
    text(target, "Enviando al receptor…");
    try {
      const started = await api("/api/gnss/control", "POST", body);
      for (let attempt = 0; attempt < 40; ++attempt) {
        await new Promise((resolve) => setTimeout(resolve, 250));
        const control = await api("/api/gnss/control");
        if (control.job_id !== started.job_id) continue;
        if (control.state === "running") continue;
        if (control.state === "confirmed") {
          text(target, `Confirmado por el receptor (${control.completed_commands} de ${control.total_commands}).`);
        } else {
          text(target, `Terminó en estado ${control.state}. ${control.error || ""} Consulta la configuración antes de repetir.`);
        }
        await refresh();
        return;
      }
      text(target, "El receptor no confirmó a tiempo; consulta la configuración antes de repetir.");
    } catch (error) {
      text(target, error.message);
    } finally {
      pending = false;
    }
  }

  function rows(formId) {
    return [...$(formId).querySelectorAll(".output-row")]
      .filter((row) => row.querySelector("input").checked)
      .map((row) => ({ name: row.dataset.message, hz: Number(row.querySelector("select").value) }));
  }

  $("gps-mask-form").addEventListener("submit", (event) => {
    event.preventDefault();
    submit({ action: "mask", elevation_deg: Number($("gps-mask").value) }, "gps-mask-message");
  });

  $("gps-constellations-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const body = { action: "constellations" };
    for (const [key, id] of SYSTEMS) body[key] = $(id).checked;
    if (!SYSTEMS.some(([key]) => body[key])) {
      text("gps-constellations-message", "Deja al menos una constelación habilitada.");
      return;
    }
    submit(body, "gps-constellations-message");
  });

  $("gps-outputs-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const messages = rows("gps-outputs-form");
    if (!messages.length) {
      text("gps-outputs-message", "Selecciona al menos una sentencia, o usa «detener todas las salidas».");
      return;
    }
    submit({ action: "outputs", messages }, "gps-outputs-message");
  });

  $("gps-rtcm-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const messages = rows("gps-rtcm-form");
    if (!messages.length) {
      text("gps-rtcm-message", "Selecciona al menos un mensaje RTCM.");
      return;
    }
    submit({ action: "rtcm_base", messages }, "gps-rtcm-message");
  });

  $("gps-dgps-form").addEventListener("submit", (event) => {
    event.preventDefault();
    submit({ action: "dgps_timeout", seconds: Number($("gps-dgps").value) }, "gps-dgps-message");
  });

  $("gps-query").addEventListener("click", () => submit({ action: "config_query" }, "gps-message"));
  $("gps-stop-outputs").addEventListener("click", () =>
    submit({ action: "stop_outputs" }, "gps-message"));

  // SAVECONFIG escribe la NVM del receptor: exige marcar la casilla primero.
  $("gps-save-confirm").addEventListener("change", () => {
    $("gps-save").disabled = !$("gps-save-confirm").checked;
  });
  $("gps-save").addEventListener("click", () => {
    if (!$("gps-save-confirm").checked) return;
    submit({ action: "save", confirm: true }, "gps-message");
  });

  async function refresh() {
    try {
      const profile = await api("/api/gnss/profile");
      if (!profile.available) {
        text("gps-availability", "El control del receptor no está disponible en este firmware.");
        return;
      }
      text("gps-availability", "Los valores marcados como aplicados los envió este equipo; el resto son valores de fábrica del receptor.");
      text("gps-state-mask", profile.elevation_mask_applied
        ? `${profile.elevation_mask_deg}° aplicada`
        : `${profile.elevation_mask_deg}° por defecto del receptor, sin aplicar desde aquí`);
      const enabled = SYSTEMS.filter(([key]) => profile.constellations?.[key]).map(([, , label]) => label);
      text("gps-state-systems", profile.constellations_applied
        ? enabled.join(", ") || "ninguna"
        : "Sin aplicar desde aquí; se asume el valor de fábrica");
      text("gps-state-outputs", profile.nmea_outputs || "Sin aplicar desde aquí");
      text("gps-state-rtcm", profile.rtcm_profile || "Sin aplicar desde aquí");
      text("gps-state-dgps", Number.isFinite(profile.dgps_timeout_s) ? `${profile.dgps_timeout_s} s` : "Sin aplicar desde aquí");
      text("gps-state-height", profile.height_reference === "ellipsoidal_user_configured"
        ? "Elipsoidal configurada" : "MSL del receptor");
      text("gps-state-readback", profile.mask_readback || "Sin leer");
      text("gps-state-saved", profile.persisted_to_receiver
        ? "Sí, guardado en esta sesión"
        : "No. Se pierde al apagar el receptor.");
    } catch (error) {
      text("gps-availability", error.message);
    }
  }

  async function poll() {
    // Solo consulta con la pagina visible: en campo no conviene gastar enlace
    // ni CPU refrescando una pantalla que nadie mira.
    if (location.hash === "#gps") await refresh();
    setTimeout(poll, 3000);
  }
  poll();
})();
