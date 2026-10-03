# Panel: reorganización para uso en campo

## Adaptación a Thing Plus — 0.8.0, 02/10/2026

**Nombre en el producto:** por decisión del propietario, el almacenamiento se
presenta como **Memoria interna del dispositivo**, tanto en Registro como en
Diagnóstico y los mensajes de error. La OLED abrevia **MEM INT.** por su ancho.
La implementación física sigue siendo el socket microSD integrado, descrito en
la documentación de montaje; no se confunde con la RAM del controlador.

La primera grabación se habilita con el estado `idle` que publica el firmware.
Se corrigió una incompatibilidad del panel que esperaba `ready` y dejaba el botón
deshabilitado al arrancar con almacenamiento disponible. Las pruebas del panel
ahora recorren inicio, parada, espera de cierre, catálogo y descarga por bloques
con contenido binario, además de desconexiones y sesiones parciales. Son pruebas
locales del flujo con API de prueba; la escritura física sigue pendiente.

Diagnóstico muestra la placa y su identidad, el UART comunicado por el firmware,
la OLED (estado, dirección I2C y pines) y la microSD integrada por SDIO. No se
declara una pantalla detectada o una tarjeta montada a partir de la lista de
materiales: se usa `/api/status` y se limpia la información al perder el enlace.

Registro / PPK usa el socket integrado. Distingue tarjeta ausente, tarjeta que
requiere reinicio para montar, error, grabación, cierre y archivo incompleto.
Mientras `closing` sea verdadero, incluso con `state: partial`, no permite
iniciar otra sesión ni descargar. Ante un error de comunicación deshabilita los
controles y retira el catálogo anterior. Una descarga completa lleva `.bin`; una
interrumpida conserva `.part`. El Soft Power Switch sigue pendiente.

El puente USB sirve los mismos scripts del panel, incluidos `hardware.js` y
`gps.js`. El cargador identifica visualmente «MeridianV · Thing Plus ESP32-S3»;
el diagnóstico BLE toma el GPIO RX informado por el equipo, sin recomendar el
GPIO18 histórico cuando la placa es desconocida.

Verificación local: `node tests/hardware_panel_test.js`, regresiones GNSS y OTA,
14 pruebas de análisis BLE, 21 de escenarios/regresión BLE y 12 del cargador. Inspección de Diagnóstico y Registro
en navegador con respuestas de prueba, sin puerto serie ni datos de un receptor.
La compilación incorpora el panel a la imagen firmada; la prueba física de la
Thing Plus sigue pendiente.

## Criterio original de 0.6.0

Versión 0.6.0. Describe el criterio de diseño del panel y qué cambió respecto de
0.5.0.

## Criterio

El usuario final opera **un instrumento**, no un conjunto de módulos. Que la
solución llegue por UART desde un UM980, que la PSRAM esté probada o que el heap
tenga tantos kilobytes son detalles de construcción: no ayudan a decidir nada
parado en el terreno y compiten por la atención con lo que sí importa.

De ahí tres reglas:

1. **Coordenadas y calidad juntas y grandes.** Son lo primero que se lee y viven en
   el mismo bloque: una coordenada sin su calidad induce a error.
2. **Nada vigente, nada mostrado.** Si la solución deja de estar vigente, los
   valores se reemplazan por `—`. En campo una coordenada vieja es peor que
   ninguna, porque parece buena.
3. **La plomería interna va a Diagnóstico.** UART, memoria, versiones y estado de
   integración de componentes siguen accesibles, pero fuera del camino.

## Estructura

| Apartado | Contenido |
| --- | --- |
| Campo | Calidad de solución, latitud, longitud, altura con su referencia; satélites, HDOP, edad de la última época y tramas RTCM entregadas al receptor; accesos directos. |
| Base / rover | Sin cambios de alcance. |
| Correcciones | Sin cambios de alcance. |
| Registro / PPK | Sin cambios de alcance. |
| GPS avanzado | Máscara de elevación, constelaciones, salidas NMEA, perfil RTCM, edad de correcciones, lectura y persistencia. Ver [configuración avanzada](gps-advanced.md). |
| Conexiones | Sin cambios de alcance. |
| Configuración | Sin cambios de alcance. |
| Diagnóstico | Detalle extendido de la solución, recursos del controlador y estado de integración de componentes. |

La sección «Resumen» desaparece: su tarjeta decorativa del instrumento no aportaba
información y su tarjeta de solución se convirtió en la vista de Campo. El detalle
textual del enlace GNSS se conservó íntegro en Diagnóstico.

## Qué muestra la vista de Campo

- **Solución:** el estado informado por el receptor, en texto (`RTK fijo`,
  `Autónoma`, `Sin solución`…). Se acompaña siempre de la advertencia de que la
  calidad informada no es una garantía de exactitud.
- **Latitud, longitud, altura:** con cifras tabulares para que no bailen al
  refrescar. La altura lleva su referencia debajo, sin abreviar: «MSL del
  receptor», «Elipsoidal configurada» o «Referencia no confirmada».
- **Satélites y HDOP:** desde 0.7.5, satélites **rastreados** (GSV), sin GSV
  reciente un guion; y HDOP con la aclaración de que es geometría, no metros.
- **Precisión H:** desde 0.7.5, la sigma del **peor eje** (norte o este), la
  escala en la que otros equipos dan su RMS; la combinada sale √2 mayor con la
  misma solución. Es lo mismo que va por la telemetría.
- **Edad:** segundos desde la última época aceptada.
- **RTCM al GPS:** tramas de corrección efectivamente entregadas al receptor por la
  UART. Es el último salto de la cadena RTK y hasta 0.6.0 no se publicaba en
  ninguna parte de la API, de modo que no había forma de distinguir «el caster no
  manda» de «el router descarta» de «no llega al receptor».

## Accesibilidad y formato

- El bloque principal reordena a una columna por debajo de 760 px de ancho, que es
  el caso del teléfono en campo.
- Los botones de acción tienen 52 px de alto mínimo para usarse con guantes.
- Se conserva el enlace de salto al contenido y los `aria-labelledby` por sección.
- El título de la vista de Campo existe para lectores de pantalla pero no ocupa
  espacio visual.

## Límites

- **No se ha probado con luz solar directa ni con guantes.** El contraste y los
  tamaños son un punto de partida razonado, no un ensayo de campo.
- Tampoco se ha medido el consumo del refresco del panel sobre la autonomía.
- La página de GPS avanzado solo consulta cuando está visible, para no gastar
  enlace ni CPU en una pantalla que nadie mira; el resto del panel mantiene su
  intervalo configurable de 1, 2 o 5 s.
- El panel sigue sirviéndose por HTTP y depende de la confianza de la red Wi-Fi.
