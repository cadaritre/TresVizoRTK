> HISTÓRICO. Estado anterior al diseño Rev A; consultar README.md para la entrega vigente.

# Validación D0 — 20 de septiembre de 2026

- KiCad CLI 10.0.6 abre y exporta ambos `.kicad_sch` a SVG y netlist XML.
- Comparación de los 33 componentes y sus terminales conectados contra las netlists exportadas: correcta. Se comprobó separación de entrada USB respecto a salida 5 V y correspondencia de polaridad host/Tiny en U5. Esto verifica conectividad dibujada, no comportamiento eléctrico ni exactitud integral del diseño.
- Inspección visual de ambos esquemas exportados: símbolos, referencias y anotaciones presentes, sin solapamientos principales.
- ERC alimentación: **4 errores y 7 avisos**. ERC USB: **2 errores y 5 avisos**. Son entradas/alimentaciones externas sin terminar y etiquetas de interfaces abiertas. No se excluyeron para aparentar un diseño cerrado. Los pull-downs pueden evitar avisos de ERC sin implementar una función: consultar también pendientes funcionales D0.
- El parser/DRC acepta el PCB de contorno: 0 incidencias en una placa **sin componentes ni pistas**. No es validación de layout, fabricación o mecánica.
- `git diff --check` correcto. No se hicieron pruebas físicas, simulación de transitorios, ensayos de carga/backfeed/ESD ni validación térmica.

Ver [diseño D0](DESIGN_D0.md) y los informes actuales en `kicad/review/`. Ninguna comprobación anterior autoriza fabricar D0.

---

Antecedentes P1 (las afirmaciones «sin esquemático» siguientes describen la fase anterior):

# Validación de esta etapa

19 de septiembre de 2026. Sin circuito construido ni esquemático.

- Lectura de AGENTS.md e inventario eléctrico/mecánico existente.
- Apertura de A4 con FreeCAD Python antes del cambio externo y extracción de ocho bounding boxes de sólidos válidos; ver informe mecánico. No se guardó el CAD.
- Ensayo del adaptador con FreeCAD Python: JSON TBD sin placa ficticia, agujero pasante y volumen esperado, colisión, transformación de placement, colisión de keepout, preservación geométrica de objeto previo, rechazo de STEP sin marco confirmado y carga de STEP válido. Resultado final: PASS en los ocho escenarios. Las cotas sintéticas sólo existieron en memoria/directorio temporal.
- Durante la comprobación se corrigió el criterio de prueba: `App::Part` crea objetos de origen auxiliares y recompute puede cambiar la serialización BREP. Se comparó geometría mediante diferencias de sólidos en vez de contar objetos o comparar cadenas BREP. No se ocultó una colisión real.
- `git diff --check`: sin errores en la comprobación final.

Pendientes: instalación/versionado de atopile/KiCad, compilación, ERC/DRC, presupuesto medido, revisión normativa USB completa, térmica/RF, señales OFF, ensayos de potencia A–F, programación/reset y fit real. Se requieren geometría/placement y confirmar el modelo mecánico vigente después de la eliminación externa. No se ejecutaron commits, push, pedidos ni exportaciones de fabricación en esta tarea.

## Revisión P1 USB nativo

Se descargaron los esquemas oficiales Tiny y Tiny-Adapter desde el índice Waveshare, se renderizaron con Poppler y se inspeccionaron visualmente las tres páginas. Se guardaron PDF y SHA256. El aviso local de Fontconfig no impidió leer las páginas renderizadas. Se documentaron la variante FH4R2 del esquema genérico y la ambigüedad 8 contactos frente a numeración 1–10 del adaptador, sin seleccionar pinout.

Se consultó documentación Espressif de USB Serial/JTAG y de self-powered USB Device Stack v5.4, distinguiendo APIs TinyUSB de controlador hardware. Se revisaron requisitos, arquitectura, BOM, presupuesto, inventario e interfaz mecánica para retirar bridge como preferido. Serigrafía física comunicada por el propietario: ESP32-S3-TINY; sin inspección física independiente ni medición de contactos/continuidad. No se leyó/programó dispositivo, se alteró firmware ni se quemaron eFuses.

JSON mecánico parseado y cargado por adaptador: conserva TBD sin sólidos. FPC sin MPN, pinout ni cantidad de contactos. `git diff --check` sin errores. Sin nuevas pruebas eléctricas/USB ni ERC; siguen pendientes los ensayos del informe USB_NATIVE_REVIEW.md. No se editó CAD A5 ni se ejecutaron commits.
