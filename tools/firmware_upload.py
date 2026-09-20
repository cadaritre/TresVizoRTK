#!/usr/bin/env python3
"""Carga OTA por consola USB, conserva NVS y verifica el arranque en el otro slot."""
import argparse
import base64
import hashlib
from pathlib import Path
import time
from usb_console import Instrument, detect_port


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image',type=Path)
    parser.add_argument('--port')
    args=parser.parse_args()
    image=args.image.read_bytes()
    device=Instrument(args.port or detect_port())
    session=None
    def call(path,body=None,method='POST'):
        result=device.request(method,path,body)
        if result['status'] not in (200,202):raise RuntimeError(str(result['body']))
        return result['body']
    try:
        original=call('/api/update',method='GET')
        settings=call('/api/config',method='GET')
        start=call('/api/update/begin',{'hardware_id':original['hardware_id'],'size':len(image),'sha256':hashlib.sha256(image).hexdigest()})
        session=start['session'];chunk_size=start['chunk_bytes'];last=time.monotonic()
        for offset in range(0,len(image),chunk_size):
            chunk=image[offset:offset+chunk_size]
            body={'session':session,'offset':offset,'data':base64.b64encode(chunk).decode()}
            for attempt in range(3):
                try:
                    result=call('/api/update/chunk',body)
                    break
                except (TimeoutError,OSError):
                    if attempt == 2: raise
                    print('Reintentando el mismo bloque tras perder la respuesta.',flush=True)
            if result['received_bytes']!=offset+len(chunk):raise RuntimeError('Progreso de escritura inconsistente')
            if time.monotonic()-last>10:
                print(f'OTA {100*result["received_bytes"]/len(image):.0f}%',flush=True);last=time.monotonic()
        call('/api/update/finish',{'session':session});session=None
        device.close();time.sleep(9)
        current=call('/api/update',method='GET')
        if current['active_slot']==original['active_slot'] or not current['boot_confirmed']:
            raise RuntimeError('Arranque nuevo sin confirmar; consultar recuperación')
        if call('/api/config',method='GET')!=settings:raise RuntimeError('Los ajustes cambiaron durante la actualización')
        print(f'OTA verificada: {current["active_slot"]}, firmware {current["firmware_version"]}, arranque confirmado y ajustes conservados.',flush=True)
    except Exception:
        if device.boot_diagnostics: print('Diagnóstico de arranque durante la transferencia:', list(device.boot_diagnostics),flush=True)
        raise
    finally:
        if session:
            try:call('/api/update/abort',{'session':session})
            except Exception:pass
        device.close()

if __name__=='__main__':main()
