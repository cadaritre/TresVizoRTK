"""Referencia exclusiva de Power Board. No abre, guarda ni modifica el case."""
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent


def load_interface(path=None):
    data = json.loads(Path(path or HERE / 'power_board_interface.json').read_text())
    if data.get('schema_version') != 1 or data.get('units') != 'mm':
        raise ValueError('Se requiere interfaz v1 en mm')
    return data


def _numbers(values, count, positive=False):
    return (isinstance(values, (list, tuple)) and len(values) == count
            and all(isinstance(v, (int, float)) and not isinstance(v, bool)
                    and math.isfinite(v) and (not positive or v > 0) for v in values))


def build_geometry(data=None, root=None):
    """Devuelve solids, keepouts, missing y mode en coordenadas locales."""
    import FreeCAD as App
    import Part
    data = load_interface() if data is None else data
    if data.get('schema_version') != 1 or data.get('units') != 'mm':
        raise ValueError('Se requiere interfaz v1 en mm')
    result = {'solids': [], 'keepouts': [], 'missing': [], 'mode': 'TBD'}
    missing = result['missing']
    step = data['step']
    path = Path(root or ROOT) / step['path']
    use_step = path.is_file()
    if use_step:
        if not step.get('local_frame_confirmed'):
            raise ValueError('STEP presente, pero marco local no confirmado')
        shape = Part.read(str(path))
        if shape.isNull() or not shape.isValid() or not shape.Solids:
            raise ValueError('STEP sin sólidos válidos')
        result['solids'].append(('POWER_BOARD_STEP', shape))
        result['mode'] = 'STEP'
    else:
        board = data['board']
        thickness = board.get('thickness_mm')
        outline = board.get('outline_xy_mm')
        if not _numbers([thickness], 1, True):
            missing.append('board.thickness_mm')
        elif outline is not None:
            if len(outline) < 3 or not all(_numbers(p, 2) for p in outline):
                raise ValueError('Outline inválido')
            points = [App.Vector(x, y, 0) for x, y in outline]
            shape = Part.Face(Part.makePolygon(points + [points[0]])).extrude(App.Vector(0, 0, thickness))
        elif _numbers([board.get('width_mm'), board.get('length_mm')], 2, True):
            width, length = board['width_mm'], board['length_mm']
            shape = Part.makeBox(width, length, thickness, App.Vector(-width/2, -length/2, 0))
        else:
            missing.append('board.outline_xy_mm o width_mm/length_mm')
        if not missing:
            for hole in data['mounting_holes']:
                if not _numbers(hole.get('center_xy_mm'), 2) or not _numbers([hole.get('diameter_mm')], 1, True):
                    raise ValueError('Taladro inválido')
                x, y = hole['center_xy_mm']
                shape = shape.cut(Part.makeCylinder(hole['diameter_mm']/2, thickness+2, App.Vector(x, y, -1)))
            if not shape.isValid() or not shape.Solids:
                raise ValueError('PCB simplificada inválida')
            result['solids'].append(('PCB', shape))
            result['mode'] = 'SIMPLIFIED'
    for section in ('connectors', 'external_features', 'component_envelopes', 'keepouts'):
        for entry in data[section]:
            name = entry['name']
            pos, size, rotation = (entry.get(k) for k in ('position_mm', 'size_mm', 'rotation_xyzw'))
            if not (_numbers(pos, 3) and _numbers(size, 3, True) and _numbers(rotation, 4)):
                missing.append(section + '.' + name)
                continue
            if not math.isclose(sum(v*v for v in rotation), 1.0, abs_tol=1e-6):
                raise ValueError('Quaternion no unitario: ' + name)
            for field in ('insertion_direction', 'press_direction', 'emission_direction'):
                if field in entry and (not _numbers(entry[field], 3) or
                                       not math.isclose(sum(v*v for v in entry[field]), 1.0, abs_tol=1e-6)):
                    missing.append(name + '.' + field)
            if use_step and section != 'keepouts':
                continue
            box = Part.makeBox(*size)
            box.Placement = App.Placement(App.Vector(*pos), App.Rotation(*rotation))
            result['keepouts' if section == 'keepouts' else 'solids'].append((name, box))
    for key, reviewed in data['completeness'].items():
        if reviewed is not True:
            missing.append('completeness.' + key)
    return result


def add_reference(doc, placement=None, data=None):
    """Agrega sólo objetos nuevos al documento proporcionado; no lo guarda."""
    model = build_geometry(data)
    group = doc.addObject('App::Part', 'PowerBoardReference')
    group.Label = 'POWER & INTERFACE PCB / ' + model['mode']
    group.addProperty('App::PropertyString', 'GeometryStatus')
    group.GeometryStatus = 'TBD: ' + ', '.join(model['missing']) if model['missing'] else model['mode']
    for category in ('solids', 'keepouts'):
        for name, shape in model[category]:
            obj = doc.addObject('Part::Feature', 'PowerBoard_' + name)
            obj.Label = name + (' / KEEPOUT' if category == 'keepouts' else '')
            obj.Shape = shape
            group.addObject(obj)
    if placement is not None:
        group.Placement = placement
    doc.recompute()
    return group


def check_fit(model, obstacles, placement=None, clearance_mm=None):
    """Obstáculos: dict nombre→Shape global. Sólo informa; nunca los mueve."""
    report = {'status': 'PENDING', 'missing': list(model['missing']), 'conflicts': [],
              'checked_pairs': 0, 'access_validation': 'PENDING'}
    if placement is None or clearance_mm is None or not obstacles or not model['solids']:
        report['missing'].append('placement, clearance, obstacles o solids pendientes')
        return report
    if not _numbers([clearance_mm], 1) or clearance_mm < 0:
        raise ValueError('Holgura inválida')
    for kind in ('solids', 'keepouts'):
        for name, original in model[kind]:
            shape = original.copy()
            shape.Placement = placement.multiply(shape.Placement)
            for obstacle_name, obstacle in obstacles.items():
                if obstacle.isNull() or not obstacle.isValid() or not obstacle.Solids:
                    raise ValueError('Obstáculo inválido: ' + obstacle_name)
                overlap = shape.common(obstacle).Volume
                distance = shape.distToShape(obstacle)[0]
                report['checked_pairs'] += 1
                if overlap > 1e-7 or distance < clearance_mm:
                    report['conflicts'].append({'feature': name, 'kind': kind, 'obstacle': obstacle_name,
                                                'overlap_mm3': overlap, 'distance_mm': distance})
    if report['conflicts']:
        report['status'] = 'CONFLICT'
    elif not report['missing']:
        report['status'] = 'NO_COLLISIONS_IN_SUPPLIED_GEOMETRY'
    return report
