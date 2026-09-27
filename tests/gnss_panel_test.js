"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const source = fs.readFileSync(path.join(__dirname, "../firmware/esp32/web/app.js"), "utf8");
const start = source.indexOf("function renderGnss(data) {");
const end = source.indexOf("function renderStatus(data) {", start);
assert(start >= 0 && end > start);
const values = {};
// `renderGnss` lee el último estado y pinta el indicador de fix de la cabecera;
// sin cabecera, `$` no encuentra nada y el indicador no se toca.
const context = vm.createContext({ text: (id, value) => { values[id] = value; }, $: () => null, latestStatus: null });
vm.runInContext(source.slice(start, end), context);
const live = {
  subsystems: { gnss: { state: "receiving" } },
  solution: { latitude_deg: 0, longitude_deg: 0, height_m: 0, height_reference: "receiver_msl", fix: "standalone" },
};
context.renderGnss(live);
assert.equal(values["gnss-latitude"], "0.00000000°");
assert.equal(values["gnss-quality"], "Autónoma");
assert.match(values["gnss-height"], /MSL del receptor/);
context.renderGnss({ ...live, subsystems: { gnss: { state: "stale" } } });
assert.equal(values["gnss-latitude"], "—");
assert.equal(values["gnss-height"], "—");
assert.equal(values["gnss-quality"], "Sin datos vigentes");
context.renderGnss({ ...live, solution: { latitude_deg: null, longitude_deg: null, fix: "invalid" } });
assert.equal(values["gnss-latitude"], "—");
assert.equal(values["gnss-quality"], "Sin solución");
// Satélites: usados de GGA y, si hay GSV, rastreados. Sin GSV no se inventa la
// segunda cifra, y con datos antiguos no se enseña ninguna.
context.renderGnss({ ...live, solution: { ...live.solution, satellites_used: 17, satellites_tracked: 32 } });
assert.equal(values["field-satellites"], "17 / 32");
assert.equal(values["field-satellites-note"], "Usados / rastreados");
context.renderGnss({ ...live, solution: { ...live.solution, satellites_used: 0 } });
assert.equal(values["field-satellites"], "0");
assert.equal(values["field-satellites-note"], "Usados");
context.renderGnss({ ...live, subsystems: { gnss: { state: "stale" } },
  solution: { ...live.solution, satellites_used: 17, satellites_tracked: 32 } });
assert.equal(values["field-satellites"], "—");
assert.equal(values["field-satellites-note"], "—");
context.renderGnss(null);
assert.equal(values["gnss-state"], "Sin comunicación");
console.log("Panel GNSS: cero válido, referencias, satélites, pérdida de fix y datos antiguos OK");
