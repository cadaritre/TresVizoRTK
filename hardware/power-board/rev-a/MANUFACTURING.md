# Fabricación y montaje — Rev A de prototipo

Paquete digital exportado desde `power-board.kicad_pcb`. No es una orden de compra ni una liberación de producción. Revisar J5, BOM/abastecimiento, DFM y BRINGUP.md antes del montaje de prototipos con módulos reales.

| Propiedad | Requisito de diseño |
| --- | --- |
| Contorno / espesor | 45 × 40 mm, 1.6 mm nominal |
| Capas | F.Cu señal/potencia; In1.Cu GND continuo; In2.Cu señales; B.Cu señales/potencia |
| Material | FR-4; confirmar stackup del fabricante para 4 capas/1.6 mm |
| Cobre objetivo | Externo 35 µm, interno ~15–18 µm |
| Acabado | ENIG; máscara en ambas caras, preferentemente verde |
| Clearance | 0.127 mm mínimo configurado; borde cobre 0.25 mm |
| Pistas | Señal general 0.2 mm, USB 0.18 mm; potencia local 0.5/0.6 mm y conexiones principales 0.3 mm |
| Vías | Pasantes; mínimo utilizado taladro 0.20 mm; algunas pastillas 0.40 mm |
| Agujeros de fijación | 2 × 2.2 mm NPTH, centros KiCad (2.5,2.5) y (2.5,37.5) mm |
| Montaje | SMD ambas caras; U8 DSBGA necesita capacidad real del ensamblador |

El [stackup público de JLCPCB](https://jlcpcb.com/impedance) es referencia para cotización, no confirmación de material contratado. El proyecto no declara impedancia USB certificada: full-speed 12 Mbit/s, par corto y plano de referencia; medir canal PCB–FPC. No fabricar con el orden de capas cambiado.

El stackup está guardado explícitamente en KiCad: máscara 0.010 / F.Cu 0.035 / prepreg 0.2104 / In1.Cu 0.0152 / core 1.0588 / In2.Cu 0.0152 / prepreg 0.2104 / B.Cu 0.035 / máscara 0.010 mm, suma 1.600 mm. Es un modelo normalizado de la familia 7628: el core público de referencia de JLCPCB es 1.065 mm, diferencia total de 0.0062 mm respecto al modelo. El fabricante debe confirmar espesores/material/tolerancias reales; no se afirma haber contratado ese stackup exacto.

Hay vías en pads, especialmente disipación del BQ24074 y zona USB. **Requieren relleno y tapado/capado compatible con soldadura en pad**, acordado con el fabricante; tenting por máscara no equivale a relleno. Revisar stencil del EP, bolas del DSBGA, bridges de máscara y retrabajo mediante DFM. No se ha obtenido cotización ni inspección de ensamblador. Esta selección y montaje en ambas caras pueden encarecer el prototipo.

`manufacturing/rev-a/gerbers/` contiene cuatro cobres, máscaras, serigrafías, pastas, Edge.Cuts, job file y taladros PTH/NPTH separados, además de mapas. `assembly/bom.csv` incluye MPN/fabricante/huella/DNP y datos comerciales con su fuente; `bom-jlcpcb.csv` es formato de importación, no promete tener todos los códigos. `cpl-jlcpcb.csv` deriva de posiciones KiCad y contiene sólo los 135 componentes que se montan. J5, testpoints y puentes de cobre no se compran/montan.

CPL usa origen global KiCad: X positivo a la derecha, Y exportado negativo hacia abajo del dibujo. No refleja X de la cara inferior. Las rotaciones pertenecen a KiCad: validar pin 1 y orientación en la vista de montaje del proveedor, particularmente USB-C, JST, U8, Q2/Q3, LEDs y U10. No aplicar un offset universal de rotación a todas las piezas.

Los mapas `review/assembly-top.svg` y `assembly-bottom.svg` muestran referencias, lado y orientación de inspección; el inferior está reflejado para verlo desde abajo. Las envolventes son courtyards, no geometría de pads; KiCad/Gerbers siguen siendo la fuente geométrica.

## Reexportación sin perder ruteo

Desde `hardware/power-board/`:

```sh
python3 tools/export_rev_a.py --cli /ruta/a/kicad-cli --render
# Con Python que tenga pcbnew de KiCad:
/ruta/a/python-kicad tools/check_rev_a.py
python3 tools/bom_rev_a.py
# Con Python que tenga FreeCAD y Part:
/ruta/a/python-freecad tools/mechanical_rev_a.py
python3 tools/package_rev_a.py
```

Usar KiCad 10.0.6 o una versión compatible comprobada. `export_rev_a.py` detiene exportaciones si ERC/DRC falla y conserva logs. Las dependencias locales de símbolos/huellas/3D están en `rev-a/`. Los scripts históricos layout/route/import crean o sustituyen ruteo y **no son un comando de rebuild del PCB terminado**.

STEP canónico para la carcasa: `manufacturing/power-board.step`. El original KiCad en `manufacturing/rev-a/` usa el marco del dieléctrico; el canónico conserva XY/taladros, reserva el espesor nominal completo 1.6 mm y desplaza componentes Z +0.045 mm. Incluye el FPC candidato como reserva, aunque no se monta. Modelos exactos de biblioteca y envolventes conservadoras se distinguen en `rev-a/lib/3dmodels/MODEL_SOURCES.md`.
