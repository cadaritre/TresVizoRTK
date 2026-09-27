#!/usr/bin/env python3
"""Prueba BLE real. Requiere bleak; muestra PIN temporal, nunca la clave del equipo."""
import asyncio,json
from bleak import BleakScanner,BleakClient
from bleak.exc import BleakGATTProtocolError
from usb_console import Instrument,detect_port
SERVICE='a04c0001-8f24-4adb-a350-77ef6339c320'
COMMAND='a04c0002-8f24-4adb-a350-77ef6339c320'
RESPONSE='a04c0003-8f24-4adb-a350-77ef6339c320'
async def main():
 device=Instrument(detect_port())
 try:
  # Desde 0.6.2 no hay PIN de emparejamiento ni clave: BLE es abierto.
  access=device.request('GET','/api/access')['body']
  print('Red del equipo:',access.get('ap_ssid'),flush=True)
  found=await BleakScanner.find_device_by_filter(lambda d,a:SERVICE in a.service_uuids,timeout=10)
  if not found:raise RuntimeError('No se detectó el servicio TresVizo')
  result=asyncio.Queue();buffer=bytearray();message=None
  def notify(_,data):
   nonlocal buffer,message
   if len(data)<5:return
   identity=int.from_bytes(data[:2],'little');offset=int.from_bytes(data[2:4],'little');flags=data[4]
   if flags&1:buffer=bytearray();message=identity
   if identity!=message or offset!=len(buffer):buffer=bytearray();message=None;return
   buffer.extend(data[5:])
   if len(buffer)>4096:buffer=bytearray();message=None;return
   if flags&2:
    try:result.put_nowait(json.loads(buffer))
    except ValueError:pass
  async with BleakClient(found,timeout=30) as client:
   await client.start_notify(RESPONSE,notify)
   async def call(identity,path,method='GET',body=None):
    payload={'id':identity,'method':method,'path':path}
    if body is not None:payload['body']=body
    raw=json.dumps(payload,separators=(',',':')).encode()+b'\n'
    for offset in range(0,len(raw),20):
     for attempt in range(5):
      try:
       await asyncio.wait_for(client.write_gatt_char(COMMAND,raw[offset:offset+20],response=True),120);break
      except BleakGATTProtocolError:
       if attempt==4:raise
       await asyncio.sleep(1)
    answer=await asyncio.wait_for(result.get(),15);assert answer.get('id')==identity;return answer
   good=await call(2,'/api/status');assert good['status']==200
   print('BLE autenticado:',good['body']['subsystems']['ble'],flush=True)
   # La recuperacion de credenciales sigue siendo exclusiva del USB fisico.
   blocked=await call(3,'/api/access');assert blocked['status']==400
   gps=await call(4,'/api/gnss/control','POST',{'action':'query'});assert gps['status']==202
   for identity in range(5,25):
    await asyncio.sleep(.25);gps=await call(identity,'/api/gnss/control')
    if gps['body']['state']!='running':break
   assert gps['body']['state']=='confirmed' and 'UM980' in gps['body']['version'],gps
   print('GPS consultado por BLE → ESP32 → UART: confirmado',flush=True)
   print('PASSED: BLE sin emparejamiento, notificaciones fragmentadas, credenciales solo por USB, consulta de estado GNSS',flush=True)
 finally:
  try:print('Estado BLE final:',device.request('GET','/api/status')['body']['subsystems']['ble'],flush=True)
  finally:device.close()
if __name__=='__main__':asyncio.run(main())
