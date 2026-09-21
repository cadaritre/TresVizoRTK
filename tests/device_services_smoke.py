#!/usr/bin/env python3
"""Prueba física UART/PSRAM. Puente cerrado; restaura GGA a 10 Hz. No inyecta RTCM."""
import sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from usb_console import Instrument,detect_port
x=Instrument(detect_port());checks=0
def call(path,method='GET',body=None,expected=200):
 global checks
 r=x.request(method,path,body);assert r['status']==expected,(path,r);checks+=1;return r['body']
def job(body):
 call('/api/gnss/control','POST',body,202)
 until=time.monotonic()+12
 while time.monotonic()<until:
  r=call('/api/gnss/control')
  if r['state']!='running':
   assert r['state']=='confirmed',r
   return r
  time.sleep(.15)
 raise AssertionError('GNSS command timeout')
try:
 s=call('/api/status');print('Memory:',s['memory'],flush=True)
 assert 2000000 <= s['memory']['psram_total_bytes'] <= 2097152 and s['memory']['psram_test']=='passed'
 r=job({'action':'query'});print('GNSS query:',r,flush=True)
 for bad in [{'action':'arbitrary'},{'action':'telemetry','hz':0},{'action':'telemetry','hz':True},{'action':'query','extra':1},
             {'action':'telemetry','hz':3},{'action':'telemetry','hz':50},
             {'action':'mask'},{'action':'mask','elevation_deg':91},{'action':'mask','elevation_deg':-91},
             {'action':'constellations'},
             {'action':'constellations','gps':False,'bds':False,'glo':False,'gal':False,'qzss':False},
             {'action':'constellations','gps':'si'},{'action':'constellations','unknown':True},
             {'action':'dgps_timeout','seconds':1801},{'action':'dgps_timeout','seconds':-1},
             {'action':'outputs','messages':[]},
             {'action':'outputs','messages':[{'name':'GPXXX','hz':1}]},
             {'action':'outputs','messages':[{'name':'GPGGA','hz':3}]},
             {'action':'outputs','messages':[{'name':'RTCM1005','hz':1}]},
             {'action':'rtcm_base','messages':[{'name':'GPGGA','hz':1}]},
             {'action':'rtcm_base','messages':[{'name':'RTCM1006','hz':1},{'name':'RTCM1005','hz':1},{'name':'RTCM1033','hz':1},
                                               {'name':'RTCM1074','hz':1},{'name':'RTCM1084','hz':1},{'name':'RTCM1094','hz':1},
                                               {'name':'RTCM1114','hz':1},{'name':'RTCM1124','hz':1},{'name':'RTCM1005','hz':5}]},
             {'action':'save'},{'action':'save','confirm':False}]:
  call('/api/gnss/control','POST',bad,400)
 # El perfil avanzado debe exponer valores conocidos sin haber aplicado nada.
 p=call('/api/gnss/profile');print('GNSS profile:',p,flush=True)
 assert p['available'] and p['elevation_mask_applied'] is False and p['persisted_to_receiver'] is False, p
 assert set(p['constellations'])=={'gps','bds','glo','gal','qzss'}, p
 call('/api/gnss/profile','POST',{},404)
 # Contadores del ultimo salto RTCM y del binario nativo presentes en el estado.
 for field in ('correction_frames_sent','correction_frames_dropped','native_frames_valid','native_frames_invalid'):
  assert isinstance(s['subsystems']['gnss'][field],int),(field,s['subsystems']['gnss'])
 # Mascara y constelaciones reales: valores conservadores, sin apagar nada.
 job({'action':'mask','elevation_deg':5})
 job({'action':'constellations','gps':True,'bds':True,'glo':True,'gal':True,'qzss':True})
 p=call('/api/gnss/profile')
 assert p['elevation_mask_applied'] and p['constellations_applied'],p
 assert p['persisted_to_receiver'] is False,'no debe guardarse sin SAVECONFIG explicito'
 job({'action':'telemetry','hz':5})
 time.sleep(1);a=call('/api/status');time.sleep(5);b=call('/api/status')
 delta=b['subsystems']['gnss']['accepted_gga']-a['subsystems']['gnss']['accepted_gga'];rate=delta/((b['uptime_ms']-a['uptime_ms'])/1000);print('5 Hz measured:',rate,flush=True);assert 4.5<=rate<=5.5,rate
 job({'action':'telemetry','hz':10})
 time.sleep(1);a=call('/api/status');time.sleep(5);b=call('/api/status')
 delta=b['subsystems']['gnss']['accepted_gga']-a['subsystems']['gnss']['accepted_gga'];rate=delta/((b['uptime_ms']-a['uptime_ms'])/1000);print('10 Hz measured:',rate,flush=True);assert 9<=rate<=11,rate
 assert b['subsystems']['gnss']['uart_errors']==a['subsystems']['gnss']['uart_errors']
 for bad in [{'action':'start'},{'action':'start','host':'bad\r\nhost','port':2101,'mountpoint':'test','username':'','password':''}]:
  call('/api/ntrip/input','POST',bad,400)
 if r['mode']=='MODE ROVER SURVEY' and b['wifi']['station_state']!='connected':
  call('/api/ntrip/input','POST',{'action':'start','host':'127.0.0.1','port':2101,'mountpoint':'test','username':'','password':''},202)
  time.sleep(.3);assert call('/api/ntrip/input')['state']=='waiting_network'
  call('/api/gnss/control','POST',{'action':'query'},409)
  call('/api/ntrip/input','POST',{'action':'stop'})
 print('PASSED:',checks,'API checks; physical 5/10 Hz rate change, PSRAM pattern test, NTRIP validation,',
       'advanced GPS validation and profile readback',flush=True)
finally:
 try:
  x.request('POST','/api/ntrip/input',{'action':'stop'})
  if not x.request('GET','/api/gnss/control')['body'].get('state')=='running':x.request('POST','/api/gnss/control',{'action':'telemetry','hz':10})
 except Exception:pass
 x.close()
