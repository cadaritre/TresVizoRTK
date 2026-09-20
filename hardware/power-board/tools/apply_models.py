from pathlib import Path
import pcbnew as k
B=Path(__file__).resolve().parents[1]/'rev-a';b=k.LoadBoard(str(B/'power-board.kicad_pcb'))
for fp in b.GetFootprints():
 for m in fp.Models():m.m_Filename=m.m_Filename.replace('${KICAD10_3DMODEL_DIR}','${KIPRJMOD}/lib/3dmodels')
 if fp.GetFPID().GetLibNickname()=='Power' and not list(fp.Models()):
  m=k.FP_3DMODEL();m.m_Filename='${KIPRJMOD}/lib/3dmodels/Power.3dshapes/'+str(fp.GetFPID().GetLibItemName())+'.step';fp.Add3DModel(m)
k.SaveBoard(str(B/'power-board.kicad_pcb'),b)
# Models() exposes copies through SWIG in KiCad 10; persist the path substitution explicitly.
p=B/'power-board.kicad_pcb';p.write_text(p.read_text().replace('${KICAD10_3DMODEL_DIR}','${KIPRJMOD}/lib/3dmodels'))
