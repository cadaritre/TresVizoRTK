#pragma once
#include <ArduinoJson.h>
namespace power_manager {
void begin();
void tick(); // Bajo el mutex del instrumento.
void sampleGauge(); // Exclusivamente desde la tarea dueña de Wire.
void status(JsonObject out);
bool pending();
bool requestShutdown();
// Radio LoRa externo enlazado por el USB-C (docs/radio/USB_LINK.md §9): mientras dure,
// la v0.3 pone su cargador en HIZ para no tomar corriente de VBUS (si un radio o un
// cable la dieran) y al desenlazar lo devuelve. La Thing Plus carga sola (MCP73831,
// sin I2C): no puede hacer nada. Lo aplica la tarea dueña de Wire, en un segundo.
void blockUsbInput(bool block);
// Estado para /api/radio: -1 = esta placa no puede saberlo o hacerlo; 0 o 1.
int usbInputBlocked();
int usbPowerPresent();
}
