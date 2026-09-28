"""Tornilleria del Meridian3, calculada con la geometria del modelo.

Derivado del bom.py de V2.1 y con su misma regla: un tornillo que rosca en un
piloto ciego es el MAS LARGO comercial que no pasa del fondo del piloto (con
0.5 de margen); V2 elegia uno mas largo que el piloto y se atoraba.

Salida: SCREW-BOM.md y generated/screws.json (lo usa capacity_check.py).
Sin FreeCAD.
"""
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import stack as S  # noqa: E402

P, C = S.P, S.C
RO, RI, R_SPIGOT = S.RO, S.RI, S.R_SPIGOT

# Medidas que se consiguen sin buscar. Se omiten 5, 7, 9 y 11.
COMERCIALES = [4, 6, 8, 10, 12, 14, 16, 20, 25, 30]


def comercial_que_cabe(util, agarre_minimo):
    validos = [m for m in COMERCIALES if agarre_minimo <= m <= util - 0.5]
    if not validos:
        raise SystemExit(f'Ningun tornillo comercial cabe en {util:.1f} mm con '
                         f'{agarre_minimo:.1f} de agarre: revisar el piloto.')
    return max(validos)


filas, notas, largos = [], [], {}

# --- Seguros de bayoneta -----------------------------------------------------------
seg = P['seguro']
cabeza = RO - seg['cabeza_profundidad']
sin_rosca = cabeza - R_SPIGOT                 # cruza tubo y collar sin roscar
for clave, prof, donde in (('seguro_base', seg['profundidad_base'],
                            'Seguro de la base. Rosca en el macizo de la base, sobre la brida del inserto.'),
                           ('seguro_tapa', seg['profundidad_tapa'],
                            'Seguro de la tapa. Rosca en el refuerzo del cuello.')):
    util = cabeza - ((RO + 2) - prof)
    largos[clave] = comercial_que_cabe(util, sin_rosca + 6)
    filas.append(('M3 cabeza botón ISO 7380', largos[clave], 1, donde,
                  f'piloto útil {util:.1f}; rosca {largos[clave] - sin_rosca:.1f}'))

# --- Pie del trineo -------------------------------------------------------------------
pie = P['trineo']['pie']
util = pie['espesor'] + pie['tornillo_profundidad']
largos['pie'] = comercial_que_cabe(util, pie['espesor'] + 4.5)
filas.append(('M3 cabeza botón ISO 7380', largos['pie'], len(pie['tornillos']),
              'Pie del trineo contra el suelo de la base.',
              f'pie {pie["espesor"]:.0f} + piloto {pie["tornillo_profundidad"]}; '
              f'rosca {largos["pie"] - pie["espesor"]:.0f}'))
notas.append('Los dos tornillos del pie van ANTES que el carrier: quedan debajo de él.')

# --- Tapa del panel -------------------------------------------------------------------
pan = P['panel']
r_pad = RI - pan['engrosamiento']
asiento = RO - pan['cabeza_profundidad']
# El cuello de la tapa baja por dentro y gira al cerrar. Solo limita el largo si
# el tornillo de arriba cae a su altura; aqui queda `bajo_cuello` por debajo.
z_sup = S.PANEL_Z + pan['tornillo_separacion_z'] / 2
cuello_detras = z_sup + 1.5 > S.Z_NECK_BOTTOM - 0.5
util = asiento - (R_SPIGOT + 0.5) if cuello_detras else asiento - (S.CAR_Y1 + 0.5)
enteros = [m for m in COMERCIALES if asiento - r_pad <= m <= util]
largos['panel'] = min(enteros) if enteros else comercial_que_cabe(util + 0.5, asiento - RI + 1.5)
filas.append(('M3 cabeza botón ISO 7380', largos['panel'], 2,
              'Tapa del panel USB-C. Rosca en el engrosamiento del tubo.',
              f'rosca {min(largos["panel"], asiento - r_pad) - (asiento - RI):.1f}; nunca más largo'))

# --- Antena ---------------------------------------------------------------------------
ant = P['antena']
largos['antena'] = comercial_que_cabe(ant['espesor_tapa'] + ant['rosca_profundidad'],
                                      ant['espesor_tapa'] + 3)
filas.append((f'{ant["metrica"]} cilíndrica ISO 4762', largos['antena'], ant['numero_pernos'],
              'Antena. Sube desde dentro de la tapa y rosca en la antena.',
              f'tapa {ant["espesor_tapa"]:.0f} + {largos["antena"] - ant["espesor_tapa"]:.0f} '
              f'de {ant["rosca_profundidad"]:.0f} de rosca en la antena'))
notas.append(f'La rosca de la antena se supone de {ant["rosca_profundidad"]:.0f} mm '
             '(referencia 3-M2.5x6). Medirla: un tornillo largo de más toca fondo y no aprieta.')

# --- Tiny-Adapter ---------------------------------------------------------------------
adp, rep = C['tiny_adapter'], pan['repisa']
util = adp['pcb'][0] + rep['torre_alto'] + rep['espesor']
largos['tiny_adapter'] = comercial_que_cabe(util + 0.5, adp['pcb'][0] + 2.5)
filas.append((f'{adp["metrica"]} cilíndrica ISO 4762 (o de cabeza plana)', largos['tiny_adapter'], 4,
              'Tiny-Adapter sobre las torres de la repisa de la tapa del panel.',
              f'PCB {adp["pcb"][0]} + torre {rep["torre_alto"]} + repisa {rep["espesor"]}; '
              f'rosca {largos["tiny_adapter"] - adp["pcb"][0]:.1f} en piloto de {rep["piloto"]}'))
notas.append('Los agujeros de la Tiny-Adapter (patrón 14 x 14) son los de su plano oficial: es la única '
             'placa que se atornilla. El carrier y la Tiny van con bridas, como en V2.1.')

filas.append(('McMaster 90611A121', None, 1, 'Rosca 5/8-11 UNC hembra del jalón.',
              'capturado entre base y tubo; sin tornillos'))

tornillos = sum(c for _, l, c, _, _ in filas if l)
lineas = ['# Tornillería del Meridian3', '',
          'Generado por `bom.py` (lo ejecuta `regenerate.py`). Los largos salen de la',
          'geometría: desde el asiento de la cabeza hasta el fondo de cada piloto, y el',
          'tornillo es el más largo comercial que no pasa de ese fondo.', '',
          '**Nada de esto se ha montado ni ensayado.**', '',
          '| Pieza | Largo | Cant. | Dónde | Cálculo |', '| --- | ---: | ---: | --- | --- |']
for nombre, largo, cant, donde, calculo in filas:
    lineas.append(f'| {nombre} | {f"{largo} mm" if largo else "—"} | **{cant}** | {donde} | {calculo} |')
lineas += ['', f'**{tornillos} tornillos con largo definido y ninguna tuerca.** Frente a V2.1 '
           'desaparecen el IMU (con sus tuercas), el panel auxiliar y los barrenos de accesorios, '
           'y aparecen los cuatro M2 de la Tiny-Adapter.', '',
           '## Advertencias', ''] + [f'- {n}' for n in notas] + [
           '- Tornillos del panel: el de arriba queda 3 mm por debajo del cuello de la tapa, que '
           'baja por dentro y gira al cerrar. **No poner uno más largo que el de la lista.**', '',
           '## Consumibles', '',
           '| Consumible | Cantidad | Uso |', '| --- | ---: | --- |',
           '| Brida de 2.5 mm, 100-150 mm | 4 | Carrier (dos, a lo largo) y Tiny (dos) |',
           '| Lámina aislante fina | 1 | Entre el carrier y la placa del trineo |',
           '| Latiguillo SMA macho–macho, clavijas rectas, RG174 o RG316 | 1 | Antena a carrier; largo en el README |',
           '| FFC de 0.5 mm, 8 vías | 1 | Tiny a Tiny-Adapter, si el FPC original no llega; largo en el README |',
           '| Llave Allen 2 mm | 1 | M3 cabeza botón y M2.5 cilíndrica |',
           '| Llave Allen 1.5 mm | 1 | M2 cilíndrica |', '']

(ROOT / 'generated').mkdir(exist_ok=True)
(ROOT / 'generated' / 'screws.json').write_text(json.dumps(largos, indent=1), encoding='utf-8')
(ROOT / 'SCREW-BOM.md').write_text('\n'.join(lineas), encoding='utf-8')
print(json.dumps(largos, indent=1))
