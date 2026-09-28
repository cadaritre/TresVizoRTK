#pragma once
#include <ArduinoJson.h>

// Satélites VISIBLES, calculados en el ESP32: los que la geometría pone sobre la
// máscara del receptor, se oigan o no (la cifra comparable a la del Emlid).
// No son los rastreados (GSV) ni los usados (GGA).
//
// El UM980 no expone su almanaque, así que una tarea propia baja cada día los
// TLE GNSS públicos de CelesTrak (HTTP, cuando la red tiene internet) y cada
// 5 s cuenta los satélites sobre la máscara con la posición de la GGA. El
// cálculo está en `lib/gnss/src/orbit_visibility.h`.
namespace gnss_visible {
void begin();
// Visibles ahora mismo. false si no se sabe: sin órbitas descargadas, sin
// posición vigente o sin un cálculo reciente. Un cero diría «ninguno».
bool visible(unsigned& count);
// Estado para `/api/gnss/sky`: órbitas, antigüedad, último error y el conteo.
void status(JsonObject out);
}
