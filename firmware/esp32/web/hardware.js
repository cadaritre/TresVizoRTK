"use strict";

// El estado proviene del equipo. Un socket integrado no implica tarjeta montada.
function recordingView(sd) {
  const result = {label: "Sin comunicación", note: "Esperando el estado de la memoria interna del dispositivo.",
    canStart: false, canStop: false, canDownload: false};
  if (!sd) return result;
  if (sd.shutdown_pending) { result.label="Apagando"; result.note="Cerrando la memoria interna del dispositivo antes del corte."; return result; }
  const closing = sd.closing === true || sd.state === "closing";
  const busy = sd.active === true || sd.state === "recording" || closing;
  result.canStop = sd.active === true && !closing;
  result.canStart = sd.available === true && sd.card_present !== false && !busy && ["idle", "ready", "closed", "partial"].includes(sd.state);
  result.canDownload = result.canStart;
  if (closing) {
    result.label = "Cerrando grabación";
    result.note = sd.card_present === false
      ? "Se perdió acceso a la memoria interna durante el cierre. La sesión puede estar incompleta."
      : "Espera a que termine el cierre antes de desconectar la alimentación.";
  } else if (sd.card_present === false) {
    result.label = "Memoria interna no disponible";
    result.note = "El dispositivo no detecta su memoria interna. Revisa el almacenamiento del equipo antes de grabar.";
  } else if (sd.card_present === true && sd.available === false && ["card_missing", "closed", "partial", "idle", "ready"].includes(sd.state)) {
    result.label = "Memoria interna sin iniciar";
    result.note = "Reinicia el instrumento para intentar recuperar el acceso a la memoria interna.";
  } else {
    const states = {
      idle: ["Lista para grabar", "Memoria interna disponible. Prepara las observaciones antes de iniciar una sesión."],
      ready: ["Lista para grabar", "Memoria interna disponible. Prepara las observaciones antes de iniciar una sesión."],
      recording: ["Grabando", "No desconectes la alimentación durante la grabación."],
      closed: ["Grabación cerrada", "El archivo se cerró sin pérdidas registradas. Esto no valida sus observaciones para PPK."],
      partial: ["Grabación incompleta", "Se conserva el archivo parcial; revisa las pérdidas antes de utilizarlo."],
      card_unavailable: ["Memoria interna no disponible", "No se pudo abrir la memoria interna. Revisa el almacenamiento del equipo; no se borra ni formatea automáticamente."],
      directory_failed: ["Error de escritura", "No se pudo crear la carpeta de sesiones en la memoria interna."],
      pin_setup_failed: ["Error de almacenamiento", "No se pudo iniciar la memoria interna del dispositivo."],
      allocation_failed: ["RAM insuficiente", "No se pudo reservar memoria para grabar."],
      task_failed: ["Grabador no disponible", "No se pudo iniciar la tarea de grabación."],
      start_failed: ["Grabador no disponible", "No se pudo iniciar el servicio de memoria interna."],
      not_configured: ["No configurada", "Este firmware no tiene la memoria interna configurada."],
    };
    [result.label, result.note] = states[sd.state] || ["Estado no reconocido", "No se habilita la grabación sin confirmar el estado de la memoria interna."];
  }
  return result;
}

function renderRecording(sd, pending = false) {
  const view = recordingView(sd);
  const counts = sd && Number.isFinite(sd.bytes) && Number.isFinite(sd.dropped_bytes)
    ? ` · ${sd.bytes} bytes · ${sd.dropped_bytes} bytes perdidos` : "";
  text("sd-state", view.label + counts);
  text("sd-hint", view.note);
  $("sd-profile").disabled = $("sd-start").disabled = pending || !view.canStart;
  $("sd-stop").disabled = pending || !view.canStop;
  if (pending || !view.canDownload) $("sd-sessions").replaceChildren();
  return view;
}

function renderHardwareState(data) {
  const power=data?.subsystems?.power;
  const powerNode=document.getElementById("power-state");
  if(powerNode) powerNode.textContent=!power ? "Sin comunicación" : power.shutdown_pending
    ? (power.state==="power_still_present" ? "Corte solicitado: el equipo sigue alimentado. Desconecta las fuentes externas para apagarlo." : "Apagando: cerrando memoria interna…")
    : power.gauge_available ? `${power.percent.toFixed(0)} % · ${power.voltage_v.toFixed(2)} V${power.low_battery ? " · Batería baja" : ""} · Estado del cargador no disponible`
    : "Batería sin lectura · Estado del cargador no disponible";
  const offButton=document.getElementById("power-off");
  if(offButton) offButton.disabled=!power || power.shutdown_pending;
  text("diag-board", data?.board || (data ? "No informada por este firmware" : "—"));
  text("diag-hardware-id", data?.hardware_id || "—");
  const gnss = data?.subsystems?.gnss;
  const uart = gnss && [gnss.rx_gpio, gnss.tx_gpio, gnss.baud].every(Number.isInteger)
    ? `Unicore UM980 · RX${gnss.rx_gpio} / TX${gnss.tx_gpio} · ${gnss.baud} baud` : "Unicore UM980 · UART";
  text("component-gnss-detail", uart);
  text("component-gnss-state", !data ? "Sin comunicación" : ({receiving: "Recibiendo datos", waiting_data: "Esperando datos", stale: "Datos antiguos", start_failed: "Error de inicio"}[gnss?.state] || "No disponible"));
  const sd = data?.subsystems?.microsd;
  text("component-sd-detail", "Memoria interna del dispositivo");
  text("component-sd-state", recordingView(sd).label);
  const oled = data?.subsystems?.display;
  const oledStates = {not_started: "Sin iniciar", starting: "Iniciando", ready: "Disponible", not_detected: "No detectada", disconnected: "Desconectada", bus_failed: "Error I2C", allocation_failed: "Memoria insuficiente", task_failed: "Error de inicio"};
  text("component-display-state", !data ? "Sin comunicación" : !oled ? "No informada por este firmware" : oledStates[oled.state] || "Estado no reconocido");
  const address = Number.isInteger(oled?.i2c_address) ? `0x${oled.i2c_address.toString(16).toUpperCase()}` : "sin dirección detectada";
  text("component-display-detail", oled
    ? `${oled.driver?.toUpperCase() || "OLED"} · ${oled.width}×${oled.height} · ${address} · SDA${oled.sda_gpio} / SCL${oled.scl_gpio}`
    : "OLED · esperando información del equipo");
}
