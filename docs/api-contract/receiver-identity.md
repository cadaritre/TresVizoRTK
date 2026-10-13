# Identidad del receptor (MeridianV y MeridianVI)

Desde el MeridianVI hay dos modelos que hablan el mismo protocolo. Las apps tienen que saber
**qué modelo** y **qué unidad** se conecta, antes y después de conectarse, sin romper nada con
el firmware del MeridianV que ya está en campo. Todo lo de aquí es aditivo
([la API solo crece](README.md)).

## Qué manda el firmware

### `GET /api/status` (HTTP, BLE y USB)

Claves nuevas en la raíz, todas opcionales y anulables para las apps:

| Clave | Tipo | Valores | Nota |
| --- | --- | --- | --- |
| `model` | string | `"MeridianV"`, `"MeridianVI"` | `unknown_values_ok: true`. Sin la clave, la app supone `MeridianV` (todo el firmware anterior a esta entrega). |
| `serial` | string | 8 hex mayúsculas | Únicos por unidad: los 4 bytes bajos de la MAC base de fábrica (eFuse) del ESP32-S3. No cambia al reflashear ni al borrar la NVS. |
| `unit_name` | string | `"MeridianVI-F1A2"` | Modelo + guion + los 4 últimos hex de `serial`. En el MeridianVI es lo que anuncian el BLE, la red Wi-Fi propia y el mDNS, y lo que enseña la OLED. El MeridianV lo manda (`MeridianV-XXXX`) y lo enseña en la OLED, pero sigue anunciando `MeridianV` en BLE, SSID y mDNS. |
| `capabilities` | object | | Lo que tiene el equipo. La app oculta lo que no aplica; una clave que falta = no se sabe (se comporta como hoy). |
| `capabilities.gnss_module` | string | `"UM980"`, `"LG290P"` | `unknown_values_ok: true`. |
| `capabilities.lora_radio` | boolean | | Radio LoRa integrado (MeridianVI). `false` = el radio, si existe, es el aparato aparte de `firmware/radio`. |
| `capabilities.imu` | string | `"BMI088"`, … | Anulable. |
| `capabilities.battery_chemistry` | string | `"li-ion"`, `"lifepo4"` | `unknown_values_ok: true`. El porcentaje sigue viniendo del firmware: la app no calcula carga con el voltaje. |
| `capabilities.removable_storage` | boolean | | `false` en MeridianVI: la microSD es interna; la app no pide «saca la tarjeta». `true` en MeridianV. |
| `capabilities.ip_rating` | string | `"IP67"` | Anulable. Solo informativo. |

`device_name` sigue existiendo y vale lo mismo que `unit_name` en MeridianVI.
`hardware_id` sigue siendo el identificador de **placa** para las imágenes firmadas (no se usa para
saber el modelo).

### Anuncio BLE

- Servicio `a04c0001-…` sin cambios (las apps siguen filtrando por él).
- **Nombre local** (en la respuesta de escaneo): `unit_name`, p. ej. `MeridianVI-F1A2`. El MeridianV
  sigue anunciando `MeridianV`.
- **Datos de fabricante** en la respuesta de escaneo (MeridianVI y, desde esta entrega, también el
  MeridianV si se le actualiza el firmware):

  | Byte | Valor |
  | --- | --- |
  | 0–1 | `0xFFFF` (identificador de compañía de pruebas, little-endian; ver nota) |
  | 2–3 | `'T' 'V'` (0x54 0x56): marca |
  | 4 | versión de este bloque: `1` |
  | 5 | modelo: `5` = MeridianV, `6` = MeridianVI |
  | 6–9 | `serial` en binario, big-endian (los mismos 4 bytes que el texto) |

  Total: 10 bytes de dato, 12 con la cabecera AD. Una app que no encuentre el bloque usa el nombre:
  empieza por `MeridianVI` → MeridianVI; si no, MeridianV.

  **Nota:** `0xFFFF` es el identificador que el Bluetooth SIG reserva para pruebas. Sirve para el
  prototipo; un equipo a la venta necesita un identificador de compañía propio (de pago, del SIG).
  Si se cambia, el firmware lo anuncia con el nuevo y las apps aceptan los dos.

### Red Wi-Fi propia y mDNS

- SSID del MeridianVI: `unit_name` (`MeridianVI-F1A2`), para que base y rover no choquen.
  La contraseña de fábrica no cambia. El MeridianV conserva `MeridianV`.
- mDNS del MeridianVI: `meridianvi-f1a2.local` (en minúsculas) y servicio `_http._tcp` como hoy.
  El nombre de instancia del servicio es el mismo que el de máquina (`meridianv` o
  `meridianvi-f1a2`): las apps filtran por el prefijo `meridianv`.
- Las apps aceptan como red propia el SSID `MeridianV` y cualquier `MeridianVI-XXXX` (no comparan
  por igualdad con `MeridianV`).

## Qué hacen las apps

1. **Antes de conectar** (lista de equipos): enseñan modelo y unidad, p. ej.
   «MeridianVI · F1A2», a partir del bloque de fabricante o del nombre.
2. **Al conectar**: la verdad es `/api/status` (`model`, `serial`, `capabilities`). Si difiere de
   lo anunciado, gana `/api/status`.
3. **Recuerdan la unidad por `serial`** (no por la dirección BLE, que cambia con la generación de la
   tabla GATT): el último equipo usado, su papel base/rover y sus ajustes de app.
4. **Por capacidades**, no por modelo: si `capabilities.lora_radio` es `true`, la pantalla de radio
   habla con el radio integrado (rutas de `/api/radio`). Con `lora_radio: false` y
   `subsystems.radio.link == "usb"`, el radio externo va por el USB-C del receptor y la app lo
   configura por `/api/radio` del receptor ([USB_LINK.md](../radio/USB_LINK.md)); el emparejamiento
   BLE del «TresVizo Radio» queda solo para radios 0.1.x. `gnss_module` decide qué ajustes del GNSS
   se ofrecen.
5. Un `model` desconocido no rompe nada: se muestra el texto tal cual y se usan capacidades.
6. Las cadenas fijas «MeridianV» de la interfaz pasan a decir el modelo conectado (o «receptor»
   si no hay ninguno).
