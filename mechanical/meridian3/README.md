# Meridian3 — carcasa del receptor sencillo

**Nada de esto se ha impreso ni montado.** La geometría es coherente en CAD y
pasa las comprobaciones automáticas de `regenerate.py`. Eso no es validación.

## Veredicto

**A Ø54 cabe todo, pero no en los 106.9 mm de V2.** Con un latiguillo coaxial
entre la antena y el carrier, el equipo mide **150.6 mm**, 43.7 mm más. El
diámetro no cambia: crecer en diámetro costaría más y no resolvería el
coaxial (ver [por qué](#por-qué-no-cabe-en-1069)).

Hay una salida que sí cabe en la altura de V2, **unos 105.6 mm según la
estimación**: enroscar la antena directamente en el SMA del carrier, sin
latiguillo. Solo es posible si la HA-901A trae **SMA macho** en la base. La
Harxon HX-CH7609A, de la que es copia, declara «SMA-J», que en nomenclatura
china es macho. Además obliga a que el carrier vaya colgado de la tapa y no
del trineo de la base. **No está modelada.**

**Antes de imprimir, mirar el conector de la antena.** Macho: tiene pin
central y tuerca. Hembra: rosca por fuera y agujero.

## Qué lleva

| Lleva | No lleva |
| --- | --- |
| ESP32-S3-Tiny (ESP32-S3FH4R2) y su Tiny-Adapter | Batería, cargador, interruptor |
| Carrier BDLX RTK_UM98 con UM980 | IMU |
| Hélice HA-901A por fuera, sobre la tapa | microSD, radio |
| Latiguillo SMA antena → carrier | Panel auxiliar, botón, LEDs, barrenos de accesorios |

Se alimenta con un **power bank externo** enchufado al USB-C de la
**Tiny-Adapter**, que asoma por la única abertura de la tapa del panel.

> **El USB-C no está en la ESP32-S3-Tiny.** Según los esquemas de Waveshare de
> [`hardware/references/waveshare/`](../../hardware/references/waveshare/), la
> Tiny solo tiene un conector FPC de 0.5 mm y 8 vías (L1), por el que llegan
> USB y VBUS. El USB-C está en la Tiny-Adapter, que se une a la Tiny con ese
> FPC. La placa que se alinea con la abertura es, por tanto, la Tiny-Adapter.

## Cotas principales

| | Meridian3 | V2 | V2.1 |
| --- | ---: | ---: | ---: |
| Diámetro exterior | **54** | 54 | 69 |
| Altura total (cara de montaje de la antena) | **150.6** | 106.9 | 136.9 |
| Borde superior del tubo | 145.6 | 101.9 | 131.9 |
| Pared del tubo | 2.5 | 2.5 | 2.5 |
| Collar de bayoneta (espesor × alto) | 3.5 × 13 | 3.5 × 13 | 3.5 × 13 |
| Paso libre del collar (radio) | 21.0 | 21.0 | 28.5 |
| Taladro del cuello de la tapa (radio) | 18.15 | — | 25.65 |
| Placa de la tapa | 5 | 5 | 5 |
| Suelo de la base sobre la brida del inserto | 7.7 | 4.0 | 4.0 |
| Trineo: placa / alas / pie / anillo | 4 / 2.5 × 5 / 3 / 3 | 3 / — / — / — | 4 / 2.5 × 6 / 3 / 3 |
| Tapa del panel / repisa de la Tiny-Adapter | 2.5 / 2.5 | 2.5 / — | 2.5 / — |
| Material | 135.9 cm³ | 101 cm³ | 187 cm³ |

Todas las cifras salen de [`generated/model-index.json`](generated/model-index.json)
y [`generated/capacity.json`](generated/capacity.json).

## Por qué no cabe en 106.9

El carrier del UM980 mide 52 mm de largo y tiene que ir de pie. En planta
mide 32 × 11, y en un collar de Ø42 no cabe de otra forma. La antena queda en
el eje, encima. Todo el enlace de RF va, por tanto, en vertical sobre el
carrier. La pila, de abajo arriba, es esta (`stack.py`):

| Tramo | mm | De dónde sale |
| --- | ---: | --- |
| Inserto 5/8 + suelo de la base | 19.6 | 3.7 más que V2: a Ø54 los pilotos del pie no caben junto a la brida y van encima |
| Pie del trineo | 3 | V2.1 |
| Clavija del conector inferior del carrier + carrera de ajuste | 8 + 3 | estimación; ver dudas |
| Carrier | 52 | tabla BDLX |
| SMA del carrier fuera del canto | 11 | estimación sobre la foto de BDLX |
| Clavija recta inferior del latiguillo | 16 | estimación de clavija de crimpar |
| Tramo libre de cable | 12 | curva en S de 6.8 mm más ±3 de ajuste |
| Clavija recta superior | 16 | ídem |
| SMA de la antena bajo la tapa | 5 | estimación |
| Placa de la tapa | 5 | V2.1 |
| **Total** | **150.6** | |

**Por qué rectas y no acodadas.** Una clavija SMA acodada en el eje ocupa unos
12 mm hasta donde el cable puede empezar a curvar. Con RG174 y un radio de 6 ×
diámetro (16.8 mm), la curva llega a unos 30 mm del eje. Dentro del cuello de
la tapa hay 18.15 mm y en el cuerpo del tubo 24.5. Para que quepa una clavija
acodada hace falta un cuello de 30 mm de radio, es decir, un tubo de Ø78.
Crecer en altura sale más barato que eso.

**Lo que bajaría la altura, con su cifra:**

| Cambio | Altura |
| --- | ---: |
| Antena con SMA macho enroscada directa al carrier (carrier colgado de la tapa; sin modelar) | ~105.6 |
| El ESP32 va por el conector lateral de 8 vías y no se usa el inferior: sobran sus 8 mm | 142.6 |
| Clavijas, SMA o salida del SMA de la antena más cortos que lo estimado | 1 mm menos por cada mm |

El conector lateral no se puede quitar de la cuenta en diámetro. Si el ESP32
va por el inferior, el lateral no hace falta y el carrier puede centrarse,
pero la altura no baja.

## Alimentación: una sola entrada USB-C

**Hoy cada placa tiene su propio USB.** Lo dicen `docs/gnss-bringup.md` y
`firmware/esp32/README.md`: el TTL2 del UM980 va a GPIO18 y GPIO17 con GND
común y sin unir la alimentación. En el Meridian3, en cambio, el único USB-C
tiene que alimentar las dos placas.

Lo documentado:

- **Tiny-Adapter**: el VBUS del USB-C va directo a VSYS, sin diodo, y sale
  por el pin 3 del FPC. Lleva 5.1 k en CC1 y en CC2, así que un power bank
  USB-C le da 5 V.
- **Tiny**: VBUS pasa por el diodo **D1 (B5819WS)** y queda como **VCC_5V**,
  que sale por el pad **P1-1**; P1-2 es GND. El regulador ME6217 saca 3V3.
- **Carrier UM980**: **DC 4.0–5.5 V, 5.0 V típico, 160 mA a 5 V**, según la
  tabla de BDLX.

**Cableado que propongo. Por confirmar:** llevar P1-1 (VCC_5V) y P1-2 (GND) de
la Tiny a los pines de alimentación y masa del conector del carrier que se use
para el TTL2. **El pinout de los conectores de 8 y 5 vías del carrier no está
en el repositorio**; hay que sacarlo de la serigrafía o de BDLX antes de
soldar.

- Tensión en el carrier: 5 V menos la caída de D1, unos 4.6 V. Está dentro de
  4.0–5.5. Hay que medirla con carga.
- D1 pasa a llevar ESP32 + UM980 + LNA de la antena. La Harxon original
  declara ≤ 55 mA de LNA; la de la HA-901A no está documentada. Sobre el papel
  son unos 0.5–0.7 A de pico contra 1 A nominal del B5819WS, pero su
  temperatura en SOD-323 **no está comprobada**.
- Variante sin la caída de D1: tomar los 5 V de VSYS en la Tiny-Adapter (pin 3
  del FPC o los condensadores C1/C2). Obliga a soldar en esa placa.
- Si se enchufa la Mac a ese mismo USB-C, la Mac alimenta todo. Un puerto USB 2
  de 500 mA puede quedarse corto.
- Muchos power bank se apagan solos con poco consumo. Solo el UM980 ya pide
  160 mA, pero **hay que probarlo con el power bank del propietario**.

**Alternativa (no elegida): USB-C de panel con prolongador.** Un USB-C
pasamuros con pads de VBUS y GND reparte los 5 V sin tocar las placas de
Waveshare, y un prolongador corto lleva los datos hasta la Tiny-Adapter.

- A favor: no se suelda en placas ajenas y la Tiny-Adapter puede ir en
  cualquier sitio.
- En contra: dentro hace falta sitio para la clavija del prolongador (hasta
  12.35 × 6.5 × ~20) y para la curva de su cable. A Ø54 eso choca, a la
  altura de la ventana, con el latiguillo, que va por el eje. Pediría su
  propia franja de altura, unos 15 mm más.

## El USB-C

- **Abertura:** rectángulo de 13.4 × 8.2 con esquinas de r=1.5, centrado en el
  eje del receptáculo a z=98.6. Cabe el sobremolde máximo de la especificación
  USB Type-C (12.35 × 6.5), aunque tenga esquinas de solo r=1. Queda un margen
  de **0.53 mm por lado en ancho y 0.85 en alto**, medido sobre el modelo.
- **El receptáculo queda 3.2 mm por debajo de la superficie.** El sobremolde
  entra ese tanto. Un cable acodado necesita al menos 3.2 mm rectos antes del
  codo; comprobarlo con el del power bank.
- **La Tiny-Adapter va atornillada a la tapa del panel** con 4 M2×6 en las
  torres de su repisa. Usa los agujeros de su plano oficial (patrón 14 × 14).
  Como receptáculo y abertura están en la misma pieza, quedan alineados por
  construcción. Es la única placa atornillada; carrier y Tiny van con bridas,
  como en V2.1.
- La salida del receptáculo respecto al canto del PCB no está acotada. Si
  asoma hasta ~3 mm, entra en la abertura, que es mayor. Si está metido, el
  sobremolde entra más.
- BOOT y RESET de la Tiny-Adapter quedan dentro. Para usarlos hay que quitar
  la tapa del panel.

## Piezas a imprimir

STL en [`generated/stl`](generated/stl/), en posición de montaje (hay que
orientarlos en el laminador). STEP por pieza en [`generated/step`](generated/step/).

| Archivo | Pieza | Orientación | Soportes |
| --- | --- | --- | --- |
| `01-threaded-base.stl` | Base con rosca 5/8 | De pie, cara del jalón en la cama | Solo dentro del alojamiento de la brida del inserto: no se ve |
| `02-logo-tube.stl` | Tubo con logo grabado | De pie, como en el modelo | Ninguno. El collar superior y el engrosamiento del panel llevan chaflán a 45°; las ranuras de bayoneta vuelan 2.5 mm |
| `03-antenna-cap.stl` | Tapa de antena | Boca abajo: cara de la antena en la cama, cuello hacia arriba | Ninguno. Los dientes vuelan 2.5 mm hacia fuera |
| `04-sled.stl` | Trineo | De pie, pie abajo | Bajo el pie, entre las pestañas, y bajo el anillo. Es pieza interior, no se ve |
| `05-usb-panel-cover.stl` | Tapa del panel USB-C | De pie sobre su canto inferior | Solo bajo la repisa de la Tiny-Adapter, que da hacia dentro. La cara curva exterior sale limpia |

Las caras visibles son el exterior del tubo, la cara superior de la tapa y la
cara exterior de la tapa del panel. Ninguna lleva soportes.

## Montaje

1. Inserto del jalón en la base. **Sigue sin poder hacerse**: ver pendientes.
2. Trineo sobre la base: cuatro pestañas en sus ranuras (dos bajo la placa y
   dos bajo las alas; girado 180° no entra) y **dos M3×8** por el pie.
3. **Tiny** en la cara trasera, entre las alas, con el extremo de la antena
   de chip hacia arriba y bridas por las filas de 86.6 y 106.6. Soldar a P1
   los cables de 5 V, GND y TTL. Conectar el FFC a la Tiny y pasarlo hacia
   delante por la ranura de z=91.6.
4. **Carrier** en la cara delantera, con lámina aislante, SMA arriba y
   conector de 8 vías hacia −X. Bridas a lo largo por las filas de 26.6
   (debajo) y 86.6 (encima). **Dejar la de arriba sin apretar.**
5. Tubo desde arriba: dientes por las entradas, **girar en sentido horario
   visto desde arriba** hasta el tope, y **M3×14** del seguro de la base.
6. Antena:
   1. Enroscar una clavija del latiguillo al SMA de la antena.
   2. Pasar el latiguillo por el agujero central de la tapa.
   3. Atornillar la antena con **3 M2.5×10** desde dentro.
7. Tapa:
   1. Bajarla guiando la clavija libre por el agujero del anillo del trineo
      (tiene embudo). El cuello recoge el anillo.
   2. Girar en sentido horario hasta el tope.
   3. **M3×12** del seguro de la tapa.
8. Con la tapa del panel quitada, **por la ventana**:
   1. Enroscar la clavija inferior al SMA del carrier, subiendo o bajando el
      carrier (±3 mm) hasta que el cable quede recto.
   2. Apretar la brida de arriba del carrier.
9. Tapa del panel:
   1. Atornillar la Tiny-Adapter a sus torres con **4 M2×6**.
   2. Conectar el FFC.
   3. Meter la tapa por la ventana (la placa pasa, está comprobado) y poner
      **dos M3×6**.

Tornillería completa en [SCREW-BOM.md](SCREW-BOM.md): 13 tornillos, ninguna
tuerca. **No poner en el panel un tornillo más largo que M3×6.**

**Latiguillo:** SMA macho–macho, clavijas rectas, RG174 o RG316. Entre las
puntas de los dos SMA hembra hay **44 mm (41 a 47 con el ajuste del
carrier)**; hay que comprarlo o crimparlo para esa distancia. Si la antena
resulta ser macho, hace falta uno hembra–macho y conviene replantear (ver el
veredicto).

**FFC:** entre los conectores hay unos 30 mm de recorrido. Para conectarlo con
la tapa del panel fuera hacen falta unos 40 más. Si el FPC original de
Waveshare no llega, usar un FFC de 0.5 mm y 8 vías de unos 100 mm, del mismo
tipo de contactos que el original.

## Qué comprueba `regenerate.py`

Todo sobre el modelo cerrado. Resultados en [`generated/capacity.json`](generated/capacity.json).

| Comprobación | Resultado |
| --- | --- |
| Un sólido válido por pieza, mallas cerradas, sin interferencias entre piezas | sí |
| Trineo por el collar (r=21) | radio máximo 20.4: **0.6 mm** |
| Carrier / Tiny por el collar | r=19.51 / 17.24 |
| Carrier contra piezas | 0.5 a la placa (lámina aislante), 5.0 al tubo, 5.4 a la tapa del panel |
| Tiny-Adapter contra piezas y componentes | 0.56 al tubo; 1.05 a la clavija inferior |
| Clavija del conector lateral del carrier | hay **6.99** hasta el collar; hacen falta ~6 (estimación) |
| Clavija del conector inferior | 8 mm libres con el carrier en su punto más bajo |
| Coaxial | curva en S de 6.8 mm en un tramo de 9–15; la clavija (r 5.45) pasa por el anillo (r 7); su tuerca queda entre z=87.6 y 102.6, dentro de la ventana (66.6–106.6) y bajo el cuello (113.6) |
| USB-C | sobremolde máximo centrado; márgenes 0.53 / 0.85 |
| Tapa del panel con la Tiny-Adapter puesta | la caja de repisa y placa, barrida hacia fuera, no toca el tubo |
| Centrado | el anillo entra en el cuello con 0.3 de holgura radial y 360° de contacto |
| Bayoneta: sentido | dientes de la base a +28.74° de su canal y de la tapa a −28.66°: **las dos uniones cierran en sentido horario visto desde arriba** |
| Bayoneta: recorrido | el diente entra por su canal y gira hasta 0.1° del tope sin tocar el tubo, arriba y abajo |
| Seguros | tornillo recto por tubo y base, y por tubo y tapa, sin tocar; 20.8 y 16.0 mm³ de plástico para la rosca |
| Paredes entre tornillos de la base | mínimo **1.4** (seguro a brida del inserto); mínimo pedido 1.2 |
| Cabezas de los M2.5 de la antena | 2.6 al cuello. Con el patrón de V2.1 (90°) el de 210° **se metía 0.52 mm³ en el refuerzo del seguro**: por eso el patrón gira a 120° |
| Tornillos del panel | la punta queda a 1.5 de lo más cercano |
| Rigidez del trineo frente a V2 | sección 7.6–22×; punta en voladizo 3.5–10×. Menos que V2.1 (6.7–18.7×): la placa es más estrecha y más larga. Son cuentas, no ensayo |

**Lo que NO se comprobó:** nada impreso, nada montado, nada medido. En
particular:

- el ajuste real de bayoneta, anillo y pestañas;
- el roscado en plástico;
- la captura del inserto;
- las cotas estimadas del carrier (SMA, conectores con clavija);
- el latiguillo y el conector de la antena;
- el paso real del FFC;
- la temperatura de D1;
- el alcance Wi-Fi/BLE con la antena de chip de la Tiny dentro del tubo y a
  unos 6.5 mm de la clavija metálica;
- la estanqueidad: la abertura del USB-C queda abierta.

## Dudas abiertas para el propietario

1. **¿La HA-901A trae SMA macho o hembra?** Decide entre 150.6 mm con
   latiguillo y ~105.6 mm enroscándola al carrier (con otra arquitectura).
2. **¿Por qué conector del carrier va el TTL2 y dónde están sus 5 V y GND?**
   Si es el lateral de 8 vías, sobran 8 mm de altura.
3. **Medir en la pieza real:**
   - cuánto sale el SMA del carrier (estimado 11);
   - la clavija de 1.25 mm enchufada con sus cables (estimados 6 de lado y 8
     abajo);
   - cuánto asoma el SMA de la antena bajo su base;
   - las clavijas del latiguillo.
   Cada milímetro de menos en la pila es un milímetro menos de equipo.
4. **Cableado de 5 V** desde P1-1 de la Tiny: por confirmar con el pinout del
   carrier y midiendo tensión y temperatura de D1 con carga.
5. **Inserto del jalón:** sigue sin poder meterse en su alojamiento. Es
   heredado de V2 y V2.1 y no se tocó. Hay que decidirlo antes de imprimir la
   base.
6. **Para V2.1 (MeridianV), sin cambiarla:**
   - la misma cuenta dice que un SMA acodado bajo su tapa pide unos 30 mm
     desde el eje con RG174, y su cuello da 25.65;
   - su comprobación de «18.4 mm sobre el IMU» mide solo la altura.

## Regenerar

```sh
python3 mechanical/meridian3/regenerate.py
```

Localiza FreeCAD (probado con FreeCAD 1.1.3 en macOS). Hace, en este orden:

1. Pila de alturas (`stack.py`).
2. Logo (`layout_check.py`).
3. Tornillería (`bom.py`).
4. Piezas (`build_meridian3.py`).
5. STL y STEP con mallas e interferencias (`export_meridian3.py`).
6. Comprobaciones (`capacity_check.py`).
7. Cortes en PNG ([`generated/cortes`](generated/cortes/)).

Si algo falla, sale con código distinto de cero.

Para verlo con colores y las envolventes de referencia (`ref_*`, que no se
imprimen), abrir `view_meridian3.py` desde FreeCAD.

La carcasa lleva el logo grabado de V2.1; **no lleva el texto «Meridian3»**,
porque el generador de V2.1 no grababa nombre. El nombre sí está en el
documento FreeCAD (`Meridian3.FCStd`) y en las etiquetas de las piezas.
