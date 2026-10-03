"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const web = path.join(__dirname, "../firmware/esp32/web");
const html = fs.readFileSync(path.join(web, "index.html"), "utf8");
const elements = new Map([...html.matchAll(/\bid="([^"]+)"/g)].map((m) => [m[1], {
  textContent: "", disabled: false, children: [], handlers: {},
  replaceChildren(...children) { this.children = children; },
  append(child) { this.children.push(child); },
  addEventListener(event, handler) { this.handlers[event] = handler; },
}]));
function $(id) { assert(elements.has(id), `Falta ${id} en el HTML`); return elements.get(id); }
let current, fail = false;
const downloads = [], calls = [], blobs = [];
const originalBytes = Buffer.from([0, 255, 36, 65, 13, 10, 0, 128]);
const context = vm.createContext({ $, text: (id, value) => { $(id).textContent = value; },
  confirm: () => true, Number, Blob, Uint8Array, atob, location: {hash: "#recording"}, setTimeout: () => {}, run: async () => {},
  URL: {createObjectURL: (blob) => {blobs.push(blob); return "blob:test";}, revokeObjectURL: () => {}},
  document: {getElementById: (id) => elements.get(id), createElement: () => ({children: [], append(child) {this.children.push(child);},
    addEventListener(event, handler) {this[event] = handler;}, click() {downloads.push(this.download);}})},
  api: async (route, method, body) => {
    calls.push([route, method]);
    if(fail)throw new Error("Enlace perdido");
    if(route === "/api/power/shutdown"){ assert.equal(method,"POST"); return {}; }
    if(route === "/api/recording")return current;
    if(route === "/api/recording/start"){
      assert.equal(current.state, "idle");
      current = {...current, state: "recording", active: true};return {};
    }
    if(route === "/api/recording/stop"){
      assert.equal(current.active, true);
      current = {...current, state: "closing", active: false, closing: true};return {};
    }
    if(route === "/api/recording/sessions")return {sessions: [
      {session_id: "a".repeat(24), state: "closed", bytes: 0},
      {session_id: "b".repeat(24), state: "interrupted", bytes: 0},
    ]};
    if(route === "/api/recording/read"){
      const chunk = originalBytes.subarray(body.offset, body.offset + 3);
      return {size: originalBytes.length, next_offset: body.offset + chunk.length, data: chunk.toString("base64")};
    }
    throw new Error(`API inesperada: ${route}`);
  },
});
vm.runInContext(fs.readFileSync(path.join(web, "hardware.js"), "utf8"), context);
const ready = {state: "idle", available: true, card_present: true, active: false, closing: false, bytes: 0, dropped_bytes: 0};
context.renderRecording(ready);
assert.equal($("sd-start").disabled, false);
assert.equal($("sd-stop").disabled, true);
for(const sd of [null, {...ready, card_present: false, available: false, state: "card_missing"},
  {...ready, available: false, state: "card_unavailable"}, {...ready, state: "unexpected"},
  {...ready, card_present: false}]) {
  context.renderRecording(sd);
  assert.equal($("sd-start").disabled, true);
  assert.equal($("sd-profile").disabled, true);
  assert.equal($("sd-sessions").children.length, 0);
}
context.renderRecording({...ready, state: "partial", closing: true, dropped_bytes: 256});
assert.match($("sd-state").textContent, /Cerrando.*256 bytes perdidos/);
assert.equal($("sd-start").disabled, true);
assert.equal($("sd-stop").disabled, true);
context.renderRecording({...ready, state: "recording", active: true});
assert.equal($("sd-start").disabled, true);
assert.equal($("sd-stop").disabled, false);
context.renderRecording({...ready, state: "closed", available: false});
assert.match($("sd-state").textContent, /Memoria interna sin iniciar/);
context.renderRecording(ready, true);
assert.equal($("sd-start").disabled, true);
const status = {board: "SparkFun Thing Plus ESP32-S3 WRL-24408", hardware_id: "tresvizo-thingplus-s3-4m-v1",
  subsystems: {gnss: {state: "receiving", rx_gpio: 44, tx_gpio: 43, baud: 115200},
    microsd: {...ready, interface: "sdmmc_4bit"},
    display: {state: "ready", driver: "ssd1306", width: 128, height: 64, sda_gpio: 8, scl_gpio: 9, i2c_address: 0x3c}}};
context.renderHardwareState(status);
assert.match($("diag-board").textContent, /Thing Plus/);
assert.match($("component-gnss-detail").textContent, /RX44 \/ TX43/);
assert.match($("component-sd-detail").textContent, /Memoria interna del dispositivo/);
assert.match($("component-display-detail").textContent, /0x3C.*SDA8 \/ SCL9/);
context.renderHardwareState({...status, subsystems: {...status.subsystems, display: {...status.subsystems.display, state: "not_detected", i2c_address: null}}});
assert.equal($("component-display-state").textContent, "No detectada");
assert.doesNotMatch($("component-display-detail").textContent, /0x3C/);
context.renderHardwareState({subsystems: {}});
assert.equal($("component-display-state").textContent, "No informada por este firmware");
context.renderHardwareState(null);
assert.equal($("diag-board").textContent, "—");
assert.equal($("component-display-state").textContent, "Sin comunicación");
// Ejecuta el flujo real de catálogo y descarga, con respuestas de API de prueba.
const device = fs.readFileSync(path.join(web, "device.js"), "utf8");
const start = device.indexOf("  let sdPending=");
const end = device.indexOf("  async function poll(){", start);
assert(start > 0 && end > start);
vm.runInContext(device.slice(start, end), context);
(async () => {
  current = ready;
  await context.pollRecording();
  // Arranque real del contrato del firmware: idle, no ready. La primera sesión
  // debe poder iniciarse; al detenerla, esperar el cierre antes de otra acción.
  assert.equal($("sd-start").disabled, false);
  await $("sd-start").handlers.click();
  assert.equal($("sd-start").disabled, true);
  assert.equal($("sd-stop").disabled, false);
  await $("sd-stop").handlers.click();
  assert.equal($("sd-start").disabled, true);
  assert.equal($("sd-stop").disabled, true);
  current = {...ready, state: "closed"};
  await context.pollRecording();
  const rows = $("sd-sessions").children;
  assert.equal(rows.length, 2);
  await rows[0].children[0].click();
  await rows[1].children[0].click();
  assert.deepEqual(downloads, ["a".repeat(24) + ".bin", "b".repeat(24) + ".part"]);
  for(const blob of blobs)assert.deepEqual(Buffer.from(await blob.arrayBuffer()), originalBytes);
  fail = true;
  await context.pollRecording();
  assert.equal($("sd-sessions").children.length, 0);
  assert.equal($("sd-start").disabled, true);
  assert.equal($("sd-stop").disabled, true);
  assert.equal($("sd-state").textContent, "Sin comunicación");
  fail = false;
  current = {...ready, state: "partial", closing: true};
  calls.length = 0;
  await context.pollRecording();
  assert.equal(calls.some(([route]) => route.endsWith("/sessions")), false);
  assert.equal($("sd-start").disabled, true);
  console.log("Panel Thing Plus: OLED, tarjeta ausente, cierre, pérdida de enlace y descargas .bin/.part OK");
})().catch((error) => {console.error(error); process.exitCode = 1;});

context.renderHardwareState({subsystems:{power:{gauge_available:true,percent:72.3,voltage_v:3.91}}});
assert.match($("power-state").textContent,/72 %.*3.91 V/);
assert.match($("power-state").textContent,/cargador no disponible/);
context.renderHardwareState({subsystems:{power:{shutdown_pending:true,state:"power_still_present"}}});
assert.match($("power-state").textContent,/sigue alimentado/);
assert.equal($("power-off").disabled,true);
context.renderRecording({...ready,shutdown_pending:true});
assert.equal($("sd-start").disabled,true);
context.renderHardwareState(null);
assert.equal($("power-off").disabled,true);

const shutdownScript=fs.readFileSync(path.join(web,"device.js"),"utf8");
vm.runInContext(shutdownScript.slice(shutdownScript.indexOf('$("power-off").addEventListener')),context);
$("power-off").handlers.click().then(()=>{
  assert(calls.some(([route,method])=>route==="/api/power/shutdown" && method==="POST"));
});
