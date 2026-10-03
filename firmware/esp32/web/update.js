"use strict";
(() => {
  // Firmware firmado (desde 0.7.13): firmware.bin + "TVZSIG01" + firma de 64 bytes.
  // Contrato en lib/protocol/src/signed_firmware.h; el equipo lo comprueba igual.
  const SIGNATURE_MAGIC = "TVZSIG01", SIGNATURE_TRAILER_BYTES = 72;
  const UNSIGNED_MESSAGE = "El firmware no trae la firma del propietario. Usa el archivo firmware-signed.bin.";
  let capability = null, running = false;
  async function signed(image) {
    if (image.size < SIGNATURE_TRAILER_BYTES) return false;
    const tail = new Uint8Array(await image.slice(image.size - SIGNATURE_TRAILER_BYTES, image.size - SIGNATURE_TRAILER_BYTES + SIGNATURE_MAGIC.length).arrayBuffer());
    return String.fromCharCode(...tail) === SIGNATURE_MAGIC;
  }
  async function refresh() {
    if (running) return;
    try {
      capability = await api("/api/update");
      text("update-version", `${capability.firmware_version} · ${capability.active_slot}`);
      text("update-recovery", capability.automatic_boot_rollback ? "Rollback de bootloader habilitado" : "Recuperación por USB");
      $("update-start").disabled = capability.state === "receiving";
      // La imagen anterior debe exigir firma y corresponder a esta placa.
      const unsafePrevious = capability.previous_image_signature_required === false;
      $("update-rollback").disabled = !capability.previous_image_present || unsafePrevious || capability.state === "receiving";
      $("update-rollback").title = unsafePrevious && capability.previous_image_present ? "La imagen anterior no exige firma o corresponde a otra placa." : "";
      if (capability.signature_required && !$("update-message").textContent)
        text("update-message", "Este equipo solo instala firmware firmado: elige firmware-signed.bin y su manifest.json.");
    } catch { text("update-version", "Sin comunicación o firmware anterior sin OTA"); }
  }
  $("update-form").addEventListener("submit", async event => {
    event.preventDefault();
    if (running || !capability) return;
    let session = null;
    try {
      const image = $("update-image").files[0], file = $("update-manifest").files[0];
      if (!image || !file || file.size > 8192) throw new Error("Selecciona imagen y manifiesto válidos.");
      if (capability.signature_required && !(await signed(image))) throw new Error(UNSIGNED_MESSAGE);
      const manifest = JSON.parse(await file.text());
      const identity = new Uint8Array(await image.slice(288,368).arrayBuffer());
      const boardBytes = identity.slice(32);
      const end = boardBytes.indexOf(0);
      const imageBoard = end < 0 ? null : String.fromCharCode(...boardBytes.slice(0,end));
      if (String.fromCharCode(...identity.slice(0,8)) !== "TVZFWID1" || imageBoard !== capability.hardware_id)
        throw new Error("El firmware corresponde a otra placa. Selecciona la imagen de Thing Plus ESP32-S3.");
      if (manifest.hardware_id !== capability.hardware_id || manifest.size !== image.size || image.size > capability.max_image_bytes || !/^[0-9a-f]{64}$/.test(manifest.sha256))
        throw new Error("El manifiesto, la imagen o el modelo de equipo no coinciden.");
      running = true; window.firmwareUpdating = true;
      $("update-start").disabled = $("update-rollback").disabled = true;
      text("update-message", "Preparando la partición inactiva…");
      const start = await api("/api/update/begin", "POST", {hardware_id:manifest.hardware_id,size:image.size,sha256:manifest.sha256});
      session = start.session;
      for (let offset = 0; offset < image.size; offset += start.chunk_bytes) {
        const bytes = new Uint8Array(await image.slice(offset,offset + start.chunk_bytes).arrayBuffer());
        const data = btoa(String.fromCharCode(...bytes));
        const body = {session,offset,data};
        let response;
        for (let attempt = 0; attempt < 3; ++attempt) {
          try { response = await api("/api/update/chunk","POST",body); break; }
          catch (error) { if (attempt === 2) throw error; }
        }
        if (response.received_bytes !== offset + bytes.length) throw new Error("El progreso confirmado no coincide.");
        $("update-progress").value = 100 * response.received_bytes / image.size;
        text("update-message", `Instalando: ${Math.floor($("update-progress").value)} %`);
      }
      text("update-message", "Validando imagen completa…");
      await api("/api/update/finish","POST",{session});
      session = null;
      text("update-message", "Imagen validada. Reiniciando; espera la confirmación de versión.");
      await new Promise(resolve => setTimeout(resolve,8000));
    } catch (error) {
      if (session) { try { await api("/api/update/abort","POST",{session}); } catch {} }
      text("update-message", error.message + " Consulta el estado del equipo antes de repetir.");
    } finally {
      running = false; window.firmwareUpdating = false; refresh();
    }
  });
  $("update-rollback").addEventListener("click", async () => {
    if (running) return;
    running = true; $("update-rollback").disabled = true;
    try { await api("/api/update/rollback","POST",{}); text("update-message","Reiniciando con la imagen anterior…"); }
    catch (error) { text("update-message",error.message); }
    finally { running = false; setTimeout(refresh,8000); }
  });
  window.addEventListener("beforeunload", event => {
    if (running) { event.preventDefault(); event.returnValue = ""; }
  });
  window.addEventListener("hashchange", () => { if (location.hash === "#settings") refresh(); });
  refresh();
})();
