> D0, 20-09-2026: por instrucción del propietario se diseña primero una placa compacta y otro agente adaptará la mecánica después. Contorno provisional 35 × 30 × 1.6 mm, sin placement ni STEP poblado; no tratarlo como entrega final. Las medidas A4 siguientes son antecedentes.

# Power Board en el assembly existente

**La Power Board es un nuevo componente del assembly existente.** KiCad será fuente de su geometría; JSON es interfaz local y Python adaptador. La carcasa gobierna espacio disponible. No se reconstruyen otros módulos.

## Cambio externo durante la investigación

Se inspeccionó A4 correctamente antes de que una operación externa eliminara gran parte de `mechanical/` durante esta tarea. Git muestra esas eliminaciones; no fueron realizadas ni restauradas por este trabajo. Las siguientes medidas son **evidencia histórica de la copia A4 leída**, no confirmación de que ahora exista un modelo vigente en esa ruta. Confirmar con el propietario la referencia mecánica actual antes de avanzar.

## Evidencia A4 leída mediante FreeCAD

Documento entonces disponible: `mechanical/cad/TresVizo-case-A4.FCStd`. Todos los objetos de la tabla tenían sólidos válidos. Cotas globales en mm, no medidas de Power Board:

| Objeto | X min…max | Y min…max | Z min…max |
| --- | --- | --- | --- |
| USBReference | −9…9 | 10.5…28.5 | 129…134 |
| LatchReserve | −9…9 | 16…28 | 109.3…123.3 |
| ESPReference | −9…9 | 12.5…14.95 | 139…162.5 |
| GNSSReserve | −18…18 | 12.5…24.5 | 43…107 |
| BatteryReserve | −28…28 | −7.5…4.5 | 38…107 |
| IMUReserve | −14…14 | −15…9 | 123…131 |
| ServiceCover | −14.191…14.191 | 31.515…37.577 | 89…142 |
| ElectronicsTray | −26…26 | 5.3…28.6 | 28…165 |

La reserva biestable 18×12×14 puede investigarse al reemplazarlo. USB 18×18×5 sigue ocupado mientras no se decida expresamente sustituir el adaptador y verificar el enlace a Tiny. Ninguna es volumen libre certificado. No se eliminaron esas reservas del assembly.

El generador A4 contenía repisa USB de 20.4×19.2×2.6 desde (−10.2,9.3,124.4), apoyos y travesaño. Está entre ambas reservas: no sumarlas como caja continua ni atravesarla con PCB. No se encontró volumen libre parametrizado de Power Board. No está demostrado que la propuesta eléctrica completa quepa.

El portillo mira a +Y. `build_case.py` heredado define abertura redondeada de diseño 22×29, Z108…137, bajo el portillo; no es recorte final USB-C. Faltan plano del conector, orientación y cable. README-A4 declaraba pendientes pulsador exterior y ventana LED. No usar el centro del portillo como centro de botón inventado.

**POWER_BOARD_MAX_WIDTH / LENGTH / HEIGHT: TBD. Outline, espesor, montaje: TBD.** La envolvente del case o bandeja no equivale a espacio disponible.

## Información que falta

Modelo vigente; cavidad continua con tolerancias y obstáculos; fijación; USB respecto del portillo; botón y salida de luz; conectores enchufados, curvatura de cables y secuencia de extracción. Confirmar si se reemplaza el adaptador USB además del biestable. Mantener posiciones de ESP32, UM980, batería, IMU, antena y eje del jalón. Si no cabe o no es accesible, reportar conflicto sin modificar carcasa.

## Contrato JSON

Sólo datos de esta PCB. Centro geométrico XY=(0,0), cara inferior Z=0, mm, marco derecho. El responsable del case proporciona placement global explícito. `null` = desconocido; listas vacías no certifican ausencia de objetos. Las banderas `completeness` deben revisarse, no cambiarse sólo para obtener un resultado verde.

Rectángulo: width/length/thickness. Contorno real: `outline_xy_mm` polígono simple en marco local, tiene prioridad. Agujeros: `center_xy_mm` y `diameter_mm`, pasantes cilíndricos; ranuras/contornos complejos mediante STEP.

Envolventes: `position_mm` esquina mínima de caja antes de rotación, `size_mm` positiva, `rotation_xyzw` quaternion unitario. Rotar alrededor del origen de esa caja y luego trasladar. `mating_center_mm`, `actuation_center_mm`, `optical_center_mm` son centros físicos independientes, no esquinas de caja. Direcciones de inserción/pulsación/emisión son vectores unitarios en marco PCB.

Keepouts incluyen plug y recorrido de inserción, accionamiento del botón, trayectoria óptica y flexión/salida del cable; usar varias cajas conservadoras cuando haga falta. Component envelopes incluyen inductores, capacitores altos y componentes en cara inferior.

## API de FreeCAD

```python
from mechanical.integration.power_board_reference import build_geometry, add_reference, check_fit
model = build_geometry()
# Tras definir cotas y placement autorizado por responsable mecánico:
# group = add_reference(doc, placement=placement)
# report = check_fit(model, obstacles, placement=placement, clearance_mm=holgura)
```

JSON actual devuelve `mode=TBD`, sin PCB ficticia. `add_reference` sólo agrega grupo rotulado y formas disponibles al documento suministrado; no abre/genera case, no mueve objetos previos, no guarda.

Cuando exista `hardware/power-board/manufacturing/power-board.step`, lo prioriza. Confirmar exportación en marco local y establecer `step.local_frame_confirmed=true`. Un STEP sin marco confirmado o inválido provoca error, no fallback silencioso. No se recentra arbitrariamente. STEP reemplaza sólidos simplificados pero conserva keepouts; no contiene módulos externos.

## Fit check

`obstacles` es diccionario nombre→Shape global: paredes, bandeja, fijaciones, batería, ESP, UM980, IMU, SD y cables. `check_fit` calcula intersección y distancia contra sólidos y keepouts sin mover obstáculos. Exige placement y holgura; devuelve PENDING si faltan datos. No usa el origen local como posición final por defecto.

`NO_COLLISIONS_IN_SUPPLIED_GEOMETRY` sólo significa ausencia de colisiones en formas suministradas. No certifica completitud de obstáculos, accesibilidad, tolerancias ni montaje físico. `access_validation` permanece PENDING para revisión por responsable mecánico. Los contactos de apoyo intencionales requieren tratamiento explícito; no ignorar bandeja entera.

**Fit check real PENDING**, por falta de geometría/placement y cambio externo de la fuente mecánica. Las pruebas sintéticas del adaptador no dimensionan esta PCB.

## Actualización P1: función Tiny-Adapter

El propietario pide evaluar como preferido que Power Board sustituya Tiny-Adapter. Queda aceptado en el alcance funcional de P1, sin quitar su reserva ni alterar el CAD. Se incorpora conector ESP_NATIVE_FPC con todos los datos físicos/pinout TBD y conector auxiliar para sensing/HOLD/señales que no necesariamente caben en FPC. Confirmar orientación, radio de flexión, extracción, longitud y contactos físicos antes de marcar volumen disponible. Serigrafía trasera informada: ESP32-S3-TINY; N8R8 declarada, revisión aún pendiente. Ver USB_NATIVE_REVIEW.md. Las referencias A4 anteriores son históricas; no se modificó el modelo A5 que aparece actualmente en el repositorio.
