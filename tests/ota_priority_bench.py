#!/usr/bin/env python3
"""OTA durante consulta GNSS: acepta, cancela consulta, recibe un bloque y aborta.

Escribe/borra exclusivamente el slot INACTIVO y elimina su imagen anterior.
No activa imágenes ni cambia ajustes. Requiere equipo de banco y pyserial.
No registra sesiones, credenciales ni coordenadas.
"""
import base64
import hashlib
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from usb_console import Instrument,detect_port
u=Instrument(detect_port());session=None
image=(ROOT/'firmware/esp32/.pio/build/esp32s3_usb/firmware-signed.bin').read_bytes()
def call(method,path,body=None,expected=200):
 r=u.request(method,path,body)
 assert r['status']==expected,(path,r['status'],r.get('body',{}).get('error'))
 return r['body']
try:
 original=call('GET','/api/config');update=call('GET','/api/update')
 query=call('POST','/api/gnss/control',{'action':'query'},202)
 began=time.monotonic()
 manifest={'hardware_id':update['hardware_id'],'size':len(image),'sha256':hashlib.sha256(image).hexdigest()}
 session=call('POST','/api/update/begin',manifest)['session'];accepted_ms=(time.monotonic()-began)*1000
 control=call('GET','/api/gnss/control')
 assert control['job_id']==query['job_id'] and control['state']=='partial_or_unknown'
 chunk={'session':session,'offset':0,'data':base64.b64encode(image[:576]).decode()}
 assert call('POST','/api/update/chunk',chunk)['received_bytes']==576
 assert call('POST','/api/update/chunk',chunk)['duplicate']
 call('POST','/api/update/chunk',dict(chunk,offset=100),409)
 assert call('POST','/api/update/abort',{'session':session})['state']=='aborted';session=None
 assert call('GET','/api/update')['active_slot']==update['active_slot']
 assert call('GET','/api/config')==original
 print(json.dumps({'firmware':call('GET','/api/status')['firmware_version'],'ota_accept_ms':round(accepted_ms,1),'gnss_superseded':True,'chunk_duplicate_bad_offset_abort':'passed','active_slot_unchanged':True,'config_unchanged':True},indent=2))
finally:
 if session:
  try:u.request('POST','/api/update/abort',{'session':session})
  except Exception:pass
 u.close()
