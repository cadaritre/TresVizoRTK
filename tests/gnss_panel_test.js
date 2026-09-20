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
const context = vm.createContext({ text: (id, value) => { values[id] = value; } });
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
context.renderGnss(null);
assert.equal(values["gnss-state"], "Sin comunicación");
console.log("Panel GNSS: cero válido, referencias, pérdida de fix y datos antiguos OK");
