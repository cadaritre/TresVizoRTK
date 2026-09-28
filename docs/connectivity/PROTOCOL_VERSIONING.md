# Versiones del protocolo y compatibilidad

## Cómo sabe la app qué soporta el equipo

1. **Propiedades GATT descubiertas** para lo que es de transporte (escritura sin respuesta del
   RTCM). Es lo único que la pila del teléfono deja usar de verdad: si la tabla en caché no trae
   la propiedad, la pila no deja escribir sin respuesta aunque el equipo sepa.
2. **`protocol_version`** del estado BLE (`GET /api/ble`) para el comportamiento: 2 hasta
   0.7.10, **3 desde 0.7.11** (salud a 1 Hz siempre, contadores RTCM en la salud).
3. **Banderas por paquete** para campos nuevos dentro de un paquete (byte 16 de la salud). Los
   paquetes siguen en versión 1 a propósito: subir la versión dejaría sin sigmas a una app que
   exige 1.
4. **Capacidades** de `/api/capabilities`/`CapabilityMatrix` en las apps para las rutas HTTP/BLE.
5. **`firmware_version`** solo para explicar al usuario y para los casos ya documentados por
   versión (tabla de satélites de `ble-protocol.md`). Nunca para decidir el transporte.

## Matriz

| Firmware | Protocolo BLE | App sin cambios de hoy (`main`) | Apps de `los-residentes` (entienden de la 2 a la 3; el aviso solo sale con un equipo más nuevo) |
| --- | --- | --- | --- |
| ≤ 0.7.10 | 2 | Funciona como hasta hoy (RTCM con respuesta sin ritmo en iOS: el defecto D1) | Detectan que no hay `writeWithoutResponse`: RTCM con respuesta, **una en vuelo**, órdenes primero. Latido v2 |
| 0.7.11 | 3 | Funciona igual que con 0.7.10 (escribe con respuesta, ignora los bytes 17–19). Recibe salud también sin fix, lo que antes no pasaba: inocuo. **Pero** Equipo › Bluetooth enseña en rojo «El equipo habla la versión 3 del protocolo Bluetooth y esta app la 2. Las tramas podrían leerse mal.» (iOS y Android de `main` comparan con `==`): es falso, v3 es aditiva. Conviene no dar 0.7.11 a quien use una app de `main` | RTCM sin respuesta con ritmo (si la tabla está al día), latido a 1 Hz, contadores RTCM |

## Regla para cambios futuros

- Aditivo primero: característica nueva, bit de bandera nuevo en bytes que estaban a 0, clave
  JSON nueva. Nunca cambiar el significado de un campo existente (ya pasó una vez con el byte 3
  de la solución, en 0.7.5, y los puntos se guardaron con los satélites equivocados).
- Si un cambio no puede ser aditivo: `protocol_version` nuevo, las apps lo leen **antes** de
  usar lo nuevo, y el equipo mantiene lo viejo mientras haya apps publicadas que lo usen.
- Una característica nueva **no** aparece en un cliente con la tabla en caché (ver
  KNOWN_LIMITATIONS.md): toda función nueva debe degradar bien si su característica falta.
