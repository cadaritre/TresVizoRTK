# Fuentes y trazabilidad

Consultadas el 19 de septiembre de 2026. Se conservan enlaces oficiales; P1 añade copias de los dos PDF Waveshare en `waveshare/`, con hash abajo. Lectura de ficha/datasheet para selección conceptual no equivale a revisión de cada pin, tolerancia, layout o certificación. Antes de esquema, guardar revisión exacta y hash de los documentos de los MPN aprobados.

| Fuente primaria | Uso / estado |
| --- | --- |
| [TI BQ24074 datasheet Rev. N](https://www.ti.com/lit/ds/symlink/bq24074.pdf) | Power-path, modos de entrada, carga, térmica, OUT y operación sin batería |
| [TI BQ25606 datasheet Rev. C](https://www.ti.com/lit/ds/symlink/bq25606.pdf) | NVDC, batería ausente, DPDM y OTG; revisar 9.3 y 12 para implementación |
| [TI TPS61023](https://www.ti.com/product/TPS61023) | Boost, desconexión, corriente de switch y referencias de layout/UVLO |
| [TI TPS63070](https://www.ti.com/product/TPS63070) | Alternativa buck-boost |
| [ADI LTC2954 datasheet Rev. B](https://www.analog.com/media/en/technical-documentation/data-sheets/2954fb.pdf) | INT/KILL/EN, tabla temporal, PDT, grados C/I |
| [ADI LTC2950](https://www.analog.com/en/products/ltc2950.html) | Alternativa; no sustituir sin verificar temporización completa |
| [TI TPS22919](https://www.ti.com/product/TPS22919) | Load switch, no controlador de botón |
| [ADI MAX17048/49 datasheet Rev. 7](https://www.analog.com/media/en/technical-documentation/data-sheets/MAX17048-MAX17049.pdf) | Modelo de SOC, I2C, alimentación y alertas; usar 17048 para 1S |
| [TI BQ27441-G1](https://www.ti.com/product/BQ27441-G1) | Alternativa con shunt; configuración y química |
| [Silicon Labs CP2102N datasheet](https://www.silabs.com/documents/public/data-sheets/cp2102n-datasheet.pdf) | USB/UART, diagramas de alimentación, DTR/RTS y suspensión |
| [Silicon Labs VCP](https://www.silabs.com/software-and-tools/usb-to-uart-bridge-vcp-drivers) | Descargas oficiales macOS; compatibilidad de la Mac concreta no ensayada |
| [WCH driver macOS](https://github.com/WCHSoftGroup/ch34xser_macos) | Fuente del fabricante, familias CH34x |
| [WCH CH343](https://www.wch-ic.com/downloads/CH343DS1_PDF.html), [CH340](https://www.wch-ic.com/downloads/CH340DS1_PDF.html) | Portales oficiales devuelven contenido vacío al extractor; lectura completa pendiente |
| [TI TUSB320LAI](https://www.ti.com/product/TUSB320LAI) | Detección CC/corriente y rol sink, no PD |
| [TI BQ2970](https://www.ti.com/product/BQ2970) | Protección independiente de celda; escoger variante por umbrales |
| [USB-IF Type-C Release 2.5](https://www.usb.org/document-library/usb-type-cr-cable-and-connector-specification-release-25) | Revisión vigente localizada; texto normativo completo no recuperado |
| [USB-IF Type-C R2.0](https://www.usb.org/sites/default/files/USB%20Type-C%20Spec%20R2.0%20-%20August%202019.pdf) | Referencia anterior localizada; recuperación completa falló. No basta para certificar V1 |
| [Waveshare Tiny](https://docs.waveshare.com/ESP32-S3-Tiny) | P1: esquemas genéricos Tiny/Adapter recuperados y revisados visualmente; no certifican revisión física N8R8 |
| [BDLX UM980](https://www.bdlxgnss.com/?list_22/101.html=) | Enlace conservado del repositorio; no resolvió pinout/tensiones de header |
| [atopile](https://docs.atopile.io/) | Flujo textual propuesto, versión local no instalada en PATH |

Las fuentes de stock/precio se enlazan por fila en `../bom.md`. Revalidar todas antes de compra. Consultas no recuperables se indican como pendientes, sin rellenarlas desde resúmenes de terceros.

## Fuentes P1

Ver [USB_NATIVE_REVIEW.md](../USB_NATIVE_REVIEW.md) para fuentes Espressif, alcance por controlador y discrepancia FPC. Documentos Waveshare descargados desde los enlaces oficiales del informe; no se encontró revisión N8R8 diferenciada en el índice consultado.

- `ESP32-S3-Tiny-Sch.pdf` SHA256: `7a1069dc3c1f966f6bcea56c25272cb8ad3a7f992c46a194e6a1fdfe5b503b14`.
- `Tiny-Adapter.pdf` SHA256: `05bab7dddf85759c838841c4a9cee4942cbe7509d431ba85e4119d06a05aa96c`.
