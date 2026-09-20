# Montaje ajustable del BMI088 — A5

> Referencia heredada de A5. Para fabricar y montar usar [V1](../../v1/README.md); sus cambios y estado sustituyen los pendientes históricos de este documento.

Actualizado: 20 de septiembre de 2026. **Implementado en `TresVizo-A5.FCStd`; prototipo pendiente de prueba física.** La placa se ajusta sobre el asiento existente y después se bloquea. No queda flotante durante uso.

## Fijación simplificada

El asiento está integrado en `BatteryIMUCarrier`; desaparecen sus dos M3 independientes. La PCB se fija con **dos M2.5×12 y dos tuercas M2.5 comunes** alojadas en `IMUNutBar`, una sola prensa impresa de 30×10×4 mm. **No hay arandelas.** La cabeza Ø4.5 apoya sobre la zona de fijación de la PCB; revisar que la placa recibida no tenga componentes o pistas expuestas en ese apoyo y evitar su flexión.

La cuna se referencia al chasis mediante dos guías inferiores y dos M3×20 superiores. Tiene contacto nominal en Y=5.4; las tolerancias reales de guía e impresión forman parte del error de montaje. La plantilla alinea el encapsulado con el datum nominal del conjunto, no garantiza error físico cero. La referencia final debe verificarse después de fijar toda la cuna.

La plantilla reutilizable se retira después de alinear. Consultar las piezas y el montaje vigentes en [V1](../../v1/README.md).

## Plano identificado y datos que sí están publicados

Breakout azul **BMI088V1.0**, selector IIC/SPI, nueve contactos y dos agujeros, coincidente con la captura del propietario. [Anuncio con plano](https://www.ebay.com/itm/206558450820), [imagen original](https://i.ebayimg.com/images/g/pIEAAeSw-1lqoAi0/s-l1600.webp), [copia local](sources/BMI088-V1-dimensions.webp).

Mirando la cara de componentes con contactos abajo: PCB **23.5 × 18 mm**, agujeros **Ø3 mm**, centros **(2.5,15.5)** y **(21,15.5)** desde la esquina inferior izquierda. Separación **18.5 mm**. El plano no acota posición del chip, espesor de PCB ni alturas de componentes. Se buscaron archivos PCB/Gerber/STEP de esa revisión; los diseños localizados de AeroStrike, vseasky y Boardoza corresponden a placas distintas y no se utilizaron como cotas de la comprada.

El [BMI088 de Bosch](https://www.bosch-sensortec.com/en/products/motion-sensors/imus/bmi088) tiene encapsulado **3 × 4.5 × 0.95 mm**, acelerómetro y giróscopo de tres ejes cada uno; no magnetómetro. [Hoja de datos Bosch](https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bmi088-ds001.pdf). El contorno del encapsulado sirve como referencia visual de montaje; no acredita la posición exacta de los elementos sensibles internos.

## Cómo se centra

1. Introducir las dos tuercas M2.5 en la prensa impresa, con sus caras de apoyo hacia el techo de los alojamientos.
2. Apoyar la PCB en sus resaltes integrados. Presentar prensa por debajo y dos M2.5×12 desde arriba; dejarlos ligeramente flojos.
3. Insertar la plantilla en sus dos alojamientos. La ventana de **3.6×5.1 mm** está centrada nominalmente en X=Y=0, con cuatro marcas. Mirar perpendicularmente y alinear el encapsulado de 3×4.5 con margen uniforme. Rango comprobado: **±0.75 mm XY** alrededor de la posición inicial; no se conocen coordenadas publicadas del chip del breakout.
4. Apretar alternando los tornillos, sin doblar el PCB; revisar alineación y retirar plantilla. La placa debe quedar rígida, sin juego durante uso.
5. Colocar batería, insertar cuna en chasis y bloquear los dos M3×20. Comprobar el conjunto final y registrar sus referencias para calibración. Si el recorrido no alcanza para centrar el chip real, corregir los alojamientos del CAD; no forzar una posición supuesta.

## Coordenadas del maestro, mm

- Eje receptor/jalón: X=Y=0, Z vertical, origen inferior de base.
- PCB inicial `IMUReserve`: X±11.75, Y−10…8, Z123.8…125.4. Espesor **1.6 supuesto**, agujeros Ø3 en X±9.25/Y5.5, contactos hacia −Y.
- Asiento integrado en `BatteryIMUCarrier`: apoyos a Z123.8, pasos Ø5 para ajuste. Guía en (±15.5,−13.5), sin desplazar su datum.
- `IMUNutBar`: X±15, Y0.5…10.5, Z115…119. Dos bolsillos AF5.2, techo 1.8 mm. Tuercas Z115.2…117.2; tornillos Z113.4…125.4 bajo cabeza. La cara superior de la prensa toca el asiento en Z119.
- `IMUTarget`: X±1.5, Y±2.25, Z125.4…126.35. Es objetivo de alineación, **no posición medida del chip**.
- Plantilla: ventana X±1.8/Y±2.55, cara inferior Z126.9, puente Z140…142. Se retira verticalmente antes de cerrar.
- Pines, selector, soldaduras y posición exacta de chip no están acotados por el plano del vendedor. Comprobar alturas antes del montaje; no atribuir al centro de la PCB el centro del sensor.

## Validación y precisión

Se comprobaron sólidos, contacto de apriete y nueve posiciones XY sin intersecciones de las piezas representadas. Se comprobó la inserción de la cuna y se prepararon mallas cerradas. No se ensayó el conjunto impreso ni su rigidez/repetibilidad. Consultar las comprobaciones del montaje vigente en [V1](../../v1/README.md).

Centrar nominalmente XY no elimina el brazo de palanca en Z ni la calibración de orientación. El [manual de diseño BMI08x de Bosch](https://community.bosch-sensortec.com/knowledge-base-pg631enp/post/bmi08x-design-guide-ZWU1wwmHYnSw68r) advierte que la flexión de PCB durante ensamble puede alterar offsets y recomienda calibrar después de montar en la carcasa. Registrar los desplazamientos reales entre IMU, referencia de antena y punta del jalón; [referencia GNSS/INS de NovAtel](https://docs.novatel.com/OEM7/Content/SPAN_Install/Mount_the_IMU.htm).
