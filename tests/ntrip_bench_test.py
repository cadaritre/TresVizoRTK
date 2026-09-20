"""Caster real de loopback, publicación, autenticación y RTCM fragmentado/corrupto."""
import socket
import sys
import time
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from gnss.rtcm import Framer, crc24q
from gnss.ntrip import LocalCaster, Transport, credentials, read_header


def frame():
    data=b'\xd3\x00\x04\x3e\xd0\x00\x00'
    return data+crc24q(data).to_bytes(3,'big')


class Tests(unittest.TestCase):
    def test_framer(self):
        f=Framer();packet=frame()
        self.assertFalse(f.feed(packet[:4]))
        self.assertEqual(f.feed(packet[4:]),[packet])
        self.assertFalse(f.feed(packet[:-1]+bytes([packet[-1]^1])))
        self.assertEqual(f.feed(packet),[packet])
        self.assertEqual(f.rejected,1)

    def test_caster_source_two_clients_and_auth(self):
        caster=LocalCaster('127.0.0.1',0,'TEST','rover','test-password','source-secret')
        sockets=[]
        try:
            port=caster.server.server_address[1]
            def connect(request):
                s=socket.create_connection(('127.0.0.1',port),timeout=2);sockets.append(s);s.sendall(request);return s,read_header(s)
            _,header=connect(b'GET /TEST HTTP/1.0\r\n\r\n')
            self.assertIn(b'401',header)
            request=('GET /TEST HTTP/1.0\r\nAuthorization: '+credentials('rover','test-password')+'\r\n\r\n').encode()
            a,ha=connect(request);b,hb=connect(request)
            self.assertIn(b'200',ha);self.assertIn(b'200',hb)
            _,hc=connect(request);self.assertIn(b'503',hc)
            source,hs=connect(b'SOURCE source-secret /TEST\r\nSource-Agent: NTRIP Test\r\n\r\n')
            self.assertIn(b'200',hs)
            source.sendall(frame())
            self.assertEqual(a.recv(100),frame());self.assertEqual(b.recv(100),frame())
        finally:
            for s in sockets:s.close()
            caster.close()

    def test_client_publisher_integration(self):
        caster=LocalCaster('127.0.0.1',0,'TEST','rover','test-password','source-secret')
        received=[];client=Transport(received.append);publisher=Transport(lambda _:None)
        try:
            config={'host':'127.0.0.1','port':caster.server.server_address[1],'mountpoint':'TEST', 'username':'rover','password':'test-password','tls':False,'role':'input'}
            client.start(config);publisher.start(dict(config,role='publisher',password='source-secret'))
            end=time.monotonic()+3
            while time.monotonic()<end and (client.snapshot()['state']!='streaming' or publisher.snapshot()['state']!='streaming'):time.sleep(.01)
            publisher.publish(frame())
            end=time.monotonic()+2
            while time.monotonic()<end and not received:time.sleep(.01)
            self.assertEqual(received,[frame()])
        finally:client.stop();publisher.stop();caster.close()

if __name__=='__main__':unittest.main()
