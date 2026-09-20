"use strict";
(() => {
  let capability = null, running = false;
  async function refresh() {
    if (running) return;
    try {
      capability = await api("/api/update");
      text("update-version", `${capability.firmware_version} · ${capability.active_slot}`);
      text("update-recovery", capability.automatic_boot_rollback ? "Rollback de bootloader habilitado" : "Recuperación por USB");
      $("update-start").disabled = capability.state === "receiving";
      $("update-rollback").disabled = !capability.previous_image_present || capability.state === "receiving";
    } catch { text("update-version", "Sin comunicación o firmware anterior sin OTA"); }
  }
  $("update-form").addEventListener("submit", async event => {
    event.preventDefault();
    if (running || !capability) return;
    let session = null;
    try {
      const image = $("update-image").files[0], file = $("update-manifest").files[0];
      if (!image || !file || file.size > 8192) throw new Error("Selecciona imagen y manifiesto válidos.");
      const manifest = JSON.parse(await file.text());
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
