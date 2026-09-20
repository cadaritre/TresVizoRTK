# Rediseño para imprimir y ensamblar — criterio A4

Estado original: revisión de arquitectura. **Ya existe un [CAD A4 de revisión](../cad/README-A4.md)** construido a partir de este criterio, con limitaciones explícitas; este documento conserva el razonamiento previo. Responde al requisito de conservar la estética tipo RX y simplificar de raíz base, soporte interior y montaje. El CAD A3 se conserva como antecedente; no satisface este nuevo criterio.

## Diagnóstico comprobado

Se abrió `cad/TresVizo-case-A3.FCStd` mediante FreeCAD y se contaron **13 piezas impresas** y 21 referencias de tornillería. A3 quitó el metal a medida, pero conserva la arquitectura interior anterior. El generador de origen define cuatro postes Ø5 con 123 mm de tramo longitudinal: relación longitud/diámetro 24.6. El bastidor completo ocupa 57 × 57 × 126 mm. No se ha calculado ni ensayado su resistencia: el problema identificado es la esbeltez, el montaje y la proliferación de soportes independientes, no una demostración de que sea imposible imprimirlo.

La base A3 incorpora todavía tapa y calce separados. Hay soportes independientes para GNSS, SD, ESP y USB. El soporte de antena y su hombro también son piezas separadas. No se debe confundir una auditoría de sólidos/interferencias con una validación de fabricación, acceso de herramientas o funcionamiento.

## Arquitectura elegida para desarrollar

Objetivo: **7 piezas impresas principales**, sujeto a resolver las retenciones de las placas reales. Toda pieza adicional de cierre o sujeción que resulte necesaria deberá contarse; no ocultarla bajo el nombre de accesorio.

| Pieza | Funciones integradas | Orientación prevista de impresión |
| --- | --- | --- |
| 1. Base | Apoyo del jalón, asiento del inserto comercial, unión al cuerpo y asiento del módulo interior | Cara inferior sobre cama; pasos y alojamientos accesibles |
| 2. Cuerpo exterior | Estética, protección y guías/llaves del módulo interior | Eje vertical; revisar las aberturas en laminador |
| 3. Tapa superior / asiento de antena | Fusionar hombro y soporte; centrado, fijación real de antena y paso coaxial | Elegir cara de apoyo y nervios que eviten columnas suspendidas; verificar laminado |
| 4. Bandeja electrónica | Espina ancha, nervios cortos, apoyos para GNSS/SD/ESP/USB y paso de cables | Espalda plana sobre cama; apoyos crecen hacia arriba |
| 5. Cuna de batería | Contención y retención sin cargar la celda con tornillos; acceso a cable y conector | Acostada, abierta hacia arriba |
| 6. Soporte IMU | Plano rígido y referencia de posición/orientación reproducible | Plano, como pieza pequeña; unión por asiento con llave y tornillos |
| 7. Portillo de servicio | Acceso a conectores y mantenimiento | Cara apoyada; revisar curvatura y soportes locales |

Las dos bandejas se montan entre sí mediante apoyos amplios que encajan, y entran como módulo al cuerpo. Las llaves geométricas absorben desplazamiento y giro; los tornillos proporcionan apriete. El módulo se apoya en la base, sin que cuatro postes largos constituyan toda la estructura. Se debe poder atornillar las placas sobre la mesa antes de cerrar la carcasa.

La espina de la bandeja partirá de una sección de diseño de alrededor de **4 mm**, con rebordes/nervios cortos de 5–6 mm donde quepan. Son puntos de partida, no espesores certificados. Más plástico no corrige una mala orientación de capas. [Prusa explica la importancia de orientar piezas, dividirlas cuando mejora la impresión y prever holguras](https://help.prusa3d.com/article/modeling-with-3d-printing-in-mind_164135).

No se promete todavía que este reparto conserve exactamente todas las posiciones A3: la batería y las placas deberán redistribuirse dentro de la envolvente, verificando conectores, radio del coaxial y extracción del módulo. La silueta exterior se conserva como referencia, pero no se fuerza el empaquetado a costa de una colisión.

## Base de una sola pieza e inserto comprado

El montaje del [Reach RX está especificado como **5/8″-11 UNC**](https://emlid.com/es/reachrx/). No debe confundirse con 3/8″-16. Lo normalizado es la rosca de conexión; el exterior del buje o inserto y su retención dependen del diseño del receptor. No hay evidencia de una única pieza interna universal para todos los equipos topográficos.

La familia que simplifica esta base es **inserto/tuerca con brida para atornillar**, comercialmente `screw-mount nut`, con rosca interior 5/8-11 UNC. Sigue siendo una tuerca en la nomenclatura del catálogo, pero la brida y sus agujeros eliminan el cartucho que requería la tuerca hexagonal suelta.

Referencia encontrada: **McMaster-Carr 90611A121, estilo A, acero**, documentada en el [catálogo de insertos atornillables](https://www.mcmaster.com/products/inserts/nut-type~screw-mount/). [Enlace por número de pieza](https://www.mcmaster.com/90611A121/). El catálogo publica:

- Rosca interior 5/8-11.
- Brida Ø1 7/16″ = 36.5125 mm; espesor 3/32″ = 2.38125 mm.
- Barril Ø23/32″ = 18.25625 mm; altura de barril indicada 3/8″ = 9.525 mm.
- Tres agujeros de montaje Ø5/32″ = 3.96875 mm.

Es una **referencia comercial candidata**, no una certificación de carga GNSS ni una compra realizada. No se comprobó entrega a México, disponibilidad local ni el círculo de centros de esos tres agujeros. No asumir por simetría una separación no acotada. Los M4 no son una elección automática para agujeros nominales de 3.96875 mm: estudiar M3 con arandelas y retención comercial, según el plano y la pieza final. No confundir este estilo con la variante para soldar o con una tuerca de garras para madera.

Montaje previsto: el barril entra en el alojamiento de la base, con la brida por el interior descansando sobre un asiento impreso amplio. La brida soporta la extracción hacia el jalón; los tornillos la retienen y limitan el giro. La base ya incorpora ese asiento y sus nervios. No hay tapa de tuerca, calce ni placas a medida. El cuerpo se fija a esa misma base con tornillos accesibles. El número final de tornillos del cuerpo depende de apoyos y carga; no se quitarán únicamente para mejorar una cifra.

El inserto se compra terminado. No requiere torno, soldadura, taladrar metal ni fabricar una rosca impresa de servicio. La cavidad debe permitir que el hombro del jalón apoye antes de que su punta haga fondo. Un prisionero lateral contra la rosca no sustituye el apoyo ni el bloqueo geométrico.

## Ajuste de placas

Lo adecuado son **ranuras oblongas**, de extremos redondeados; un avellanado sólo aloja una cabeza y no da ajuste de posición.

- Integrar apoyos aislantes en la bandeja y dejar zonas libres bajo soldaduras y componentes.
- Usar pocas ranuras cortas y zonas de fijación repetidas, con topes contra giro. Una retícula muy perforada debilita la bandeja y puede dejar tornillos o arandelas bajo pistas.
- Definir explícitamente el recorrido permitido. Una ranura recta ajusta un eje; para ajustar ambos ejes hacen falta posiciones alternativas o una retención que lo permita. No afirmar compatibilidad con cualquier PCB.
- El tornillo se elige por el agujero de la PCB. No agrandar la placa ni pasar M3 a la fuerza por un agujero M2. La arandela debe apoyar fuera del área eléctrica y no puentear pistas.
- El ESP32 Tiny y el biestable no tienen taladros de montaje dedicados. Sus contactos no son agujeros mecánicos. Necesitan apoyo por bordes y retención compatible con los componentes reales; no una ranura debajo que se presente como fijación resuelta.
- Batería: cuna con volumen libre para envoltura/cables y retención que no concentre presión en la celda. La batería final sigue sin seleccionarse.

No crear una placa adaptadora completa para cada módulo si puede fijarse a la misma bandeja. Una pieza pequeña adicional sólo se justifica si permite impresión plana, mantenimiento o evita forzar el hardware.

## IMU y antena: referencias controladas

**IMU:** asiento rígido, llave o topes de posicionamiento y patrón real. Sin correderas como ajuste permanente, ni espuma que permita que cambie de orientación. La placa debe apoyar sin doblarse al apretar. La posición del chip respecto del soporte y su orientación deben quedar documentadas, y la calibración hacerse con el conjunto montado. [Bosch advierte en la guía BMI08x que la flexión del PCB durante el ensamblaje puede cambiar los offsets](https://community.bosch-sensortec.com/knowledge-base-pg631enp/post/bmi08x-design-guide-ZWU1wwmHYnSw68r). El patrón del breakout azul sigue sin plano legible; no inventarlo a partir de las medidas del chip.

**SMA / coaxial:** distinguir dos funciones antes de fijar la cota final:

- Si el conector SMA se sujeta al panel, el recorte debe seguir el plano de ese conector, con espesor de panel permitido y forma antigiro cuando corresponda.
- Si sólo pasa un pigtail que conecta directamente a la antena, se necesita paso con holgura, protección del borde, alivio de tensión y sellado. Ese agujero no debe posicionar la antena ni soportarla a través del SMA.

El Ø16 de A2/A3 era una **reserva de diseño**, no el barreno validado del conector comprado. Hay que reemplazarlo por la solución definida; tampoco adoptar un diámetro genérico de SMA como si todos los montajes fueran iguales. [Ejemplo de plano de fabricante Amphenol con recorte específico de panel](https://www.amphenolrf.com/en-us/assets/file/4074576920/) — es una referencia de método, no el conector seleccionado.

## Criterios para que el siguiente CAD sea útil

1. Dibujar cada pieza junto con su orientación de impresión y comprobar su laminado; no resolver paredes/postes frágiles aumentando sólo el relleno.
2. Modelar la secuencia de montaje, herramientas y acceso. El desmontaje no debe exigir retirar toda la electrónica para alcanzar un tornillo de la base.
3. Comprobar holguras de impresión con probetas del inserto, uniones de bandejas y guía del cuerpo antes de imprimir el conjunto.
4. Comprobar envolventes y conectores reales, espacio para carga/protección/regulación y recorrido del cable. El encendido exterior continúa siendo una función necesaria.
5. Ensayar base y estructura con masa de prueba antes de montar electrónica. No asignar precisión, resistencia o IP a partir del CAD.

No se sustituyen los archivos A3 por una nueva revisión con agujeros ficticios. Este documento registra la arquitectura y las referencias comerciales que deben gobernar la reconstrucción. La lámina `redesign-concept.png` es un esquema funcional sin escala, no un plano de fabricación.
