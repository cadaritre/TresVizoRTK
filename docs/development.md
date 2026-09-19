# Entorno de desarrollo

El desarrollo se realizará inicialmente desde macOS. Todavía no se han fijado framework, versiones, placa de compilación ni cadena de herramientas.

## Herramientas consideradas

- **Editor:** Visual Studio Code es una opción considerada.
- **Firmware:** PlatformIO es una opción considerada para gestionar compilación, carga y monitorización.
- **Control de versiones:** Git, preservando la identidad y las reglas definidas en [AGENTS.md](../AGENTS.md).
- **Documentación técnica:** manuales oficiales correspondientes a la revisión exacta de cada módulo o carrier.
- **Diseño electrónico, CAD y aplicación móvil:** herramientas pendientes de seleccionar cuando se conozcan requisitos y formatos reales.

La mención de VS Code y PlatformIO no fija una decisión. Antes de crear configuraciones debe confirmarse que la placa ESP32-S3 recibida, su memoria y el framework seleccionado son compatibles.

## Preparación pendiente

1. Identificar físicamente la placa ESP32-S3 y documentar su variante.
2. Verificar métodos de programación, consola y recuperación indicados por el fabricante.
3. Elegir framework y versiones con criterios reproducibles.
4. Crear la configuración mínima de compilación solo cuando una tarea futura lo autorice.
5. Registrar comandos de preparación y validación sin depender de ajustes globales no documentados.

## Prácticas de desarrollo

- Mantener pequeños y enfocados los cambios.
- Separar controladores de hardware, lógica del instrumento y protocolo de la app.
- Tratar las entradas externas y los mensajes GNSS como datos que pueden ser incompletos, tardíos o corruptos.
- Registrar unidades, marcos de coordenadas, referencias de altura y escalas temporales en interfaces y archivos.
- Diseñar pruebas de desconexión, pérdida de RTCM, reinicio, archivos incompletos y falta de espacio.
- Usar únicamente fixtures pequeños y anonimizados en `tests/fixtures/`.
- Guardar capturas de campo, logs voluminosos o datos sensibles en directorios locales ignorados, no en el historial.
- No almacenar credenciales NTRIP, redes Wi-Fi, tokens ni datos de clientes en el repositorio.

## Evidencia y validación

Cada cambio futuro debe indicar qué comprobaciones se realizaron y qué quedó pendiente. Una compilación no demuestra funcionamiento eléctrico; una comunicación no demuestra sincronización; una solución FIX no demuestra precisión. Los resultados de campo deberán incluir método, referencia, condiciones y datos suficientes para repetición.

