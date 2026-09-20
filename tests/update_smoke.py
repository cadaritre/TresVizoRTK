#!/usr/bin/env python3
"""Validación OTA en ESP32 real; --install realiza cambio de slot con la imagen local."""
import argparse
import base64
import hashlib
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from usb_console import Instrument, detect_port
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--install',action='store_true');args=parser.parse_args()
device=Instrument(detect_port());checks=0

def call(path, body=None, status=200, method='POST'):
    global checks
    result=device.request(method,path,body)
    assert result['status']==status,(path,result)
    checks+=1
    return result['body']

try:
    original=call('/api/config',method='GET')
    status=call('/api/update',method='GET')
    assert status['automatic_boot_rollback']
    assert status['hardware_id']=='tresvizo-esp32s3-4m-v1'
    image=(ROOT/'firmware/esp32/.pio/build/esp32s3_usb/firmware.bin').read_bytes()
    manifest={'hardware_id':status['hardware_id'],'size':len(image),'sha256':hashlib.sha256(image).hexdigest()}
    call('/api/update/begin',dict(manifest,hardware_id='different_board'),400)
    call('/api/update/begin',dict(manifest,size=0xffffffff),400)
    call('/api/update/begin',dict(manifest,sha256='x'*64),400)
    assert device._exchange('POST','/api/update/begin',manifest,'wrong-key')['status']==401
    start=call('/api/update/begin',manifest);session=start['session']
    call('/api/update/begin',manifest,409)
    call('/api/config',{'revision':original['revision']},409,method='PUT')
    call('/api/update/chunk',{'session':session,'offset':0,'data':base64.b64encode(b'x'*576).decode()},400)
    assert call('/api/update',method='GET')['state']=='invalid_image'
    start=call('/api/update/begin',manifest);session=start['session']
    chunk={'session':session,'offset':0,'data':base64.b64encode(image[:576]).decode()}
    assert call('/api/update/chunk',chunk)['received_bytes']==576
    assert call('/api/update/chunk',chunk)['duplicate']
    call('/api/update/chunk',dict(chunk,offset=100),409)
    call('/api/update/finish',{'session':session},409)
    call('/api/update/abort',{'session':session})
    assert call('/api/update',method='GET')['active_slot']==status['active_slot']
    for expected_hash, expected_state in [('0'*64,'hash_mismatch'),(hashlib.sha256(image[:1024]).hexdigest(),'invalid_image')]:
        start=call('/api/update/begin',dict(manifest,size=1024,sha256=expected_hash));session=start['session']
        for offset in (0,576):
            call('/api/update/chunk',{'session':session,'offset':offset,'data':base64.b64encode(image[offset:min(offset+576,1024)]).decode()})
        call('/api/update/finish',{'session':session},400)
        result=call('/api/update',method='GET')
        assert result['state']==expected_state
        assert not result['previous_image_present'],'Imagen fallida ofrecida como restauración'
    print(f'OTA rechazos, autenticación, duplicados, hash, imagen truncada y aborto: {checks} comprobaciones OK',flush=True)
    if args.install:
        start=call('/api/update/begin',manifest);session=start['session'];last=time.monotonic()
        for offset in range(0,len(image),576):
            result=call('/api/update/chunk',{'session':session,'offset':offset,'data':base64.b64encode(image[offset:offset+576]).decode()})
            assert result['received_bytes']==min(offset+576,len(image))
            if time.monotonic()-last>10:
                print(f'OTA transferencia {100*result["received_bytes"]/len(image):.0f}%',flush=True);last=time.monotonic()
        call('/api/update/finish',{'session':session},202)
        device.close();time.sleep(9)
        new=call('/api/update',method='GET')
        assert new['active_slot']!=status['active_slot'],new
        assert new['boot_confirmed'],new
        after=call('/api/config',method='GET')
        assert after==original,'La actualización cambió ajustes persistentes'
        print('OTA completa: nuevo slot, arranque confirmado y ajustes conservados.',flush=True)
finally:device.close()
