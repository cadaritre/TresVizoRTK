# Plan de endurecimiento (27-09-2026) y su estado

Orden seguido: auditar, medir, cambiar, validar. Cada paso con su dueño y su estado real.

| # | Paso | Parte | Estado |
| --- | --- | --- | --- |
| 1 | Localizar repos, ramas y trabajo en curso; rama `los-residentes` y un worktree por agente | Firmware | Hecho (`~/Documents/MeridianV_Bluetooth_Hardening/REPOSITORIES.md`) |
| 2 | Auditoría del firmware: tareas, colas, UART, BLE | Firmware | Hecho (CURRENT_ARCHITECTURE.md) |
| 3 | Auditoría del cliente iOS | App iOS | Hecho (IOS_BLE_ARCHITECTURE.md) |
| 4 | Auditoría del cliente Android | App Android | Ver ANDROID_BLE_ARCHITECTURE.md |
| 5 | Medir en el equipo real (Mac como central): MTU, latencia de órdenes, caudal RTCM con respuesta, hueco del bucle | Firmware | Hecho, ver ACCEPTANCE_TESTS.md |
| 6 | Firmware 0.7.11: RTCM sin respuesta (aditivo), cola por bytes hacia el UM980, salud siempre a 1 Hz con contadores RTCM, telemetría con hueco y detrás de las respuestas, intervalo 15–30 ms, métricas | Firmware | Hecho, 12 pruebas C++ en verde, cargado y probado en el equipo |
| 7 | Contrato v3 acordado con las dos apps | Firmware y apps | Hecho (BLE_CONTRACT.md) |
| 8 | iOS: una escritura RTCM en vuelo, órdenes primero, cola por bytes y edad, máquina de estados, identidad de sesión, latido, reconexión con backoff, tabla GATT vieja | App iOS | Ver IOS_BLE_ARCHITECTURE.md e informe |
| 9 | Android: cola GATT serializada, camino aparte para RTCM, sesión por generación, `close()` siempre, latido, reconexión, multimarca intacta | App Android | Ver ANDROID_BLE_ARCHITECTURE.md e informe |
| 10 | Banco de pruebas en la Mac (decodificador, RTCM, escenarios, grabación y reproducción) | Herramientas | Ver `tools/ble_bench/` y ACCEPTANCE_TESTS.md |
| 11 | Pruebas con el equipo en campo (fix, NTRIP real, sesión larga, fuera de alcance, teléfonos reales) | Propietario, mañana | Pendiente |
| 12 | «Servicios cambiados» tras la suscripción del cliente o caché robusta | — | Pendiente (KNOWN_LIMITATIONS.md) |
| 13 | Velocidad de la UART al UM980 por encima de 115200 | — | Pendiente de verificar el UM980 y el cableado |
