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
 for bad in [{'action':'arbitrary'},{'action':'telemetry','hz':0},{'action':'telemetry','hz':True},{'action':'query','extra':1}]:
  call('/api/gnss/control','POST',bad,400)
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
 print('PASSED:',checks,'API checks; physical 5/10 Hz rate change, PSRAM pattern test, NTRIP validation',flush=True)
finally:
 try:
  x.request('POST','/api/ntrip/input',{'action':'stop'})
  if not x.request('GET','/api/gnss/control')['body'].get('state')=='running':x.request('POST','/api/gnss/control',{'action':'telemetry','hz':10})
 except Exception:pass
 x.close()
