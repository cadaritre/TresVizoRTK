#!/usr/bin/env python3
"""Prueba física OTA: iniciar al arrancar, cruzar 5 s, repetir bloque y abortar.

Escribe y borra la partición INACTIVA (pierde su imagen anterior); no activa
la imagen de prueba ni modifica ajustes. Ejecutar con el equipo disponible
para banco y sin otro monitor USB. Requiere pyserial y firmware-signed.bin.
No imprime ni guarda sesiones, credenciales ni coordenadas.
"""
import sys,json,time,hashlib,base64
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from usb_console import Instrument,detect_port
image=(ROOT/'firmware/esp32/.pio/build/esp32s3_usb/firmware-signed.bin').read_bytes()
u=Instrument(detect_port());session=None;result={}
def call(method,path,body=None,expected=200):
 r=u.request(method,path,body)
 assert r['status']==expected,(path,r['status'],r.get('body',{}).get('error'))
 return r['body']
try:
 original=call('GET','/api/config')
 s=call('GET','/api/status');result['started_uptime_ms']=s['uptime_ms'];result['firmware']=s['firmware_version']
 update=call('GET','/api/update')
 result['original_slot']=update['active_slot']
 manifest={'hardware_id':update['hardware_id'],'size':len(image),'sha256':hashlib.sha256(image).hexdigest()}
 start=call('POST','/api/update/begin',manifest);session=start['session']
 # Mantener sesión abierta al cruzar el instante del arranque GNSS (5 s).
 while True:
  s=call('GET','/api/status')
  if s['uptime_ms']>=8000:break
  time.sleep(.4)
 g=call('GET','/api/gnss/control');assert g['state']=='idle',g['state']
 assert call('GET','/api/update')['state']=='receiving'
 result['gnss_during_update']=g['state'];result['crossed_boot_deadline_ms']=s['uptime_ms']
 chunk={'session':session,'offset':0,'data':base64.b64encode(image[:576]).decode()}
 assert call('POST','/api/update/chunk',chunk)['received_bytes']==576
 assert call('POST','/api/update/chunk',chunk)['duplicate']
 call('POST','/api/update/chunk',dict(chunk,offset=100),409)
 call('POST','/api/update/finish',{'session':session},409)
 assert call('POST','/api/update/abort',{'session':session})['state']=='aborted';session=None
 result['chunk_duplicate_offset_abort']='passed'
 time.sleep(.2)
 g=call('GET','/api/gnss/control');assert g['job_id']>0
 result['gnss_resumed']=g['state'];result['gnss_action']=g['action']
 err=call('POST','/api/update/abort',{'session':'invalid'},409)
 assert err['error']=='update_error';result['abort_routes_while_gnss_busy']='passed'
 assert call('GET','/api/update')['active_slot']==update['active_slot']
 result['slot_unchanged']=True
 # Dar tiempo al STA para unirse a una red guardada; nunca cambiar Wi-Fi.
 time.sleep(4)
 s=call('GET','/api/status');w=s['wifi']
 result['wifi_station_state']=w['station_state']
 result['wifi_has_address']=bool(w.get('station_ip'))
 result['display_state']=s['subsystems']['display']['state']
 assert call('GET','/api/config')==original
 result['config_unchanged']=True
 print(json.dumps(result,indent=2))
finally:
 if session:
  try:u.request('POST','/api/update/abort',{'session':session})
  except Exception:pass
 u.close()
