#pragma once
#include <Arduino.h>

// La configuración que un UM980 de MeridianV **debe** tener.
//
// Existe por un motivo concreto: montar un receptor nuevo. Un UM980 de fábrica,
// o uno que alguien tocó, no sabe nada de este producto. Sin esta tabla, poner
// en marcha una unidad nueva es acordarse de memoria de quince comandos y
// escribirlos a mano, y la primera vez que falte uno el equipo funcionará **casi
// bien**, que es la peor clase de avería.
//
// Los valores salen de la lectura de un equipo en funcionamiento el 24-09-2026,
// con dos correcciones deliberadas que van explicadas abajo. Lo que no se
// entienda no se pone: una tabla con valores copiados sin saber por qué son esos
// no se puede mantener.
namespace receiver_baseline {

struct Expectation {
    // Clave tal como la devuelve `CONFIG`: `$CONFIG,<clave>,<valor completo>`.
    const char* key;
    // Valor completo esperado, tal como lo imprime el receptor.
    const char* expected;
    // El comando que lo corrige.
    const char* command;
    // Por qué este valor y no otro. Va al informe: quien vea que su equipo
    // difiere tiene que poder decidir si acepta el cambio.
    const char* reason;
};

// **La corrección que motivó todo esto.** El receptor venía con `UNDULATION
// AUTO`, que le hace aplicar su propio modelo geoidal —no documentado, de
// resolución desconocida— y entregar altura sobre el nivel del mar. Para trabajo
// topográfico la app necesita altura **elipsoidal** y aplica su propio geoide,
// declarado y versionado. Con AUTO, la cota lleva una corrección de veintitantos
// metros de procedencia desconocida y la app no puede deshacerla.
//
// Ojo: el propio firmware ponía AUTO al entrar en modo móvil. Eso se corrige
// aparte, en `gnss_control`.
constexpr Expectation kExpected[] = {
    {"UNDULATION", "CONFIG UNDULATION 0.0000", "CONFIG UNDULATION 0.0000",
     "Altura elipsoidal. Con AUTO el receptor resta su geoide interno, que no está "
     "documentado, y la app no puede deshacer esa corrección ni declarar qué modelo se usó."},

    {"ANTENNA", "CONFIG ANTENNA POWERON", "CONFIG ANTENNA POWERON",
     "Alimentación del amplificador de la antena. Sin ella, las señales llegan débiles "
     "y el equipo parece tener mala vista del cielo cuando lo que falta es corriente."},

    {"ANTENNADELTAHEN", "CONFIG ANTENNADELTAHEN 0.0000 0.0000 0.0000",
     "CONFIG ANTENNADELTAHEN 0.0000 0.0000 0.0000",
     "Sin desplazamiento de antena en el receptor: la altura del jalón y el offset del "
     "case los suma la app. Ponerlo en los dos sitios lo cuenta dos veces."},

    {"NMEAVERSION", "CONFIG NMEAVERSION V410", "CONFIG NMEAVERSION V410",
     "Versión de NMEA que espera el analizador de GGA del firmware."},

    {"RTK", "CONFIG RTK TIMEOUT 120", "CONFIG RTK TIMEOUT 120",
     "Cuánto aguanta la solución fija sin correcciones nuevas."},

    {"DGPS", "CONFIG DGPS TIMEOUT 300", "CONFIG DGPS TIMEOUT 300",
     "Cuánto aguanta en diferencial antes de soltar."},

    {"RTCMB1CB2A", "CONFIG RTCMB1CB2A ENABLE", "CONFIG RTCMB1CB2A ENABLE",
     "Señales B1C y B2a de BeiDou en el RTCM: son las modernas y sin ellas se pierde "
     "buena parte de la constelación que mejor se ve en México."},

    {"ANTIJAM", "CONFIG ANTIJAM AUTO", "CONFIG ANTIJAM AUTO",
     "Filtro de interferencias en automático."},

    {"AGNSS", "CONFIG AGNSS DISABLE", "CONFIG AGNSS DISABLE",
     "Sin asistencia por red: el equipo no tiene salida a internet propia."},

    {"BASEOBSFILTER", "CONFIG BASEOBSFILTER DISABLE", "CONFIG BASEOBSFILTER DISABLE",
     "Sin filtrar las observaciones de la base: filtrarlas descarta datos que el motor "
     "RTK puede aprovechar."},
};

constexpr size_t kExpectedCount = sizeof(kExpected) / sizeof(kExpected[0]);

// Máscara de elevación, que se lee con su propio comando y no con `CONFIG`.
constexpr double kElevationMaskDegrees = 5.0;
constexpr const char* kElevationMaskCommand = "MASK 5.00";
constexpr const char* kElevationMaskReason =
    "Cinco grados. Más alto descarta satélites bajos que en terreno abierto son buenos; "
    "más bajo mete señales que llegan rebotadas.";

// Constelaciones. Se habilitan todas: el UM980 es de cuatro sistemas y apagar
// una solo tiene sentido para depurar.
constexpr const char* kConstellations[] = {"GPS", "BDS", "GLO", "GAL", "QZSS"};
constexpr size_t kConstellationCount = 5;

}  // namespace receiver_baseline
