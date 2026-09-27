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
// Satélites: solo los rastreados, de GSV. Los usados no se enseñan aunque
// lleguen; sin GSV no se inventa la cifra, y con datos antiguos no hay ninguna.
context.renderGnss({ ...live, solution: { ...live.solution, satellites_used: 17, satellites_tracked: 32 } });
assert.equal(values["field-satellites"], "32");
assert.equal(values["field-satellites-note"], "Rastreados");
context.renderGnss({ ...live, solution: { ...live.solution, satellites_used: 17 } });
assert.equal(values["field-satellites"], "—");
assert.equal(values["field-satellites-note"], "Sin GSV del receptor");
context.renderGnss({ ...live, subsystems: { gnss: { state: "stale" } },
  solution: { ...live.solution, satellites_used: 17, satellites_tracked: 32 } });
assert.equal(values["field-satellites"], "—");
assert.equal(values["field-satellites-note"], "—");
// Precisión horizontal por eje: la peor de norte y este, no la combinada.
context.renderGnss({ ...live, solution: { ...live.solution,
  horizontal_sigma_m: 0.025, north_sigma_m: 0.0176, east_sigma_m: 0.0181 } });
assert.equal(values["field-sigma-h"], "0.018 m");
// Un firmware que solo da la combinada sigue mostrándola.
context.renderGnss({ ...live, solution: { ...live.solution, horizontal_sigma_m: 0.025 } });
assert.equal(values["field-sigma-h"], "0.025 m");
context.renderGnss(null);
assert.equal(values["gnss-state"], "Sin comunicación");
console.log("Panel GNSS: cero válido, referencias, satélites, pérdida de fix y datos antiguos OK");
