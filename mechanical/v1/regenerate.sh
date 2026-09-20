#!/bin/zsh
set -eu
v1_dir="${0:A:h}"
freecad_python='/Users/cadaritre/Applications/FreeCAD-1.0.2.app/Contents/Resources/bin/python'
export PYTHONPATH='/Users/cadaritre/Applications/FreeCAD-1.0.2.app/Contents/Resources/lib'
"$freecad_python" "$v1_dir/../sources/panel/build_panel.py" --output-dir "$v1_dir/../../.cache/mechanical-v1/baseline"
"$freecad_python" "$v1_dir/build_v1.py"
"$freecad_python" "$v1_dir/export_v1.py"
"$freecad_python" "$v1_dir/validate_v1.py"
"$freecad_python" - "$v1_dir" <<'PY'
from pathlib import Path
import json,sys
p=Path(sys.argv[1])/'generated'
r=json.loads((p/'validation.json').read_text()); e=json.loads((p/'exports.json').read_text())
ready=r['scope_ready_for_first_full_prototype_print'] and e['all_pass']
print('READY FOR FIRST FULL PROTOTYPE PRINT:', 'YES' if ready else 'NO')
if not ready:sys.exit(1)
PY
