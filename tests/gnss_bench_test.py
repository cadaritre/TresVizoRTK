"""Pruebas de datos corruptos, vigencia temporal y sesiones de banco."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from gnss.nmea import Parser, checked
from gnss.sessions import Sessions


def sentence(body, include=False):
    crc = ord('$') if include else 0
    for c in body.encode(): crc ^= c
    return f'${body}*{crc:02X}'.encode()


def gga(clock='120000.00', quality='1', lat='0000.0000', hemi='N'):
    return sentence(f'GNGGA,{clock},{lat},{hemi},00000.0000,E,{quality},10,0.8,0,M,-20,M,,')


class NmeaTests(unittest.TestCase):
    def test_distinct_epochs_duplicates_and_stale(self):
        p = Parser()
        for i in range(11): p.feed(gga(f'12000{i//10}.{i%10}0'), 10+i/10)
        s = p.snapshot(11)
        self.assertAlmostEqual(s['measurement_hz'], 10)
        self.assertEqual(s['solution']['latitude_deg'], 0)
        p.feed(gga('120001.00'), 11.1)
        self.assertEqual(p.snapshot(11.1)['duplicates'], 1)
        self.assertEqual(p.snapshot(12)['solution'], {})
        self.assertEqual(p.snapshot(12)['signals'], [])

    def test_nofix_clears_and_bad_checksum_does_not_update(self):
        p = Parser(); p.feed(gga(), 1)
        p.feed(sentence('GNGGA,,,,,,0,,,,,,,,'), 1.1)
        self.assertIsNone(p.snapshot(1.1)['solution']['latitude_deg'])
        seq = p.sequence
        p.feed(gga()[:-2] + b'XX', 1.2)
        self.assertEqual(p.sequence, seq)
        self.assertEqual(p.rejected, 1)

    def test_invalid_coordinates_and_nonfinite(self):
        for lat, hemi in [('9060.00','N'), ('0100.00','X'), ('nan','N')]:
            p=Parser();p.feed(gga(lat=lat,hemi=hemi),1)
            self.assertFalse(p.solution)

    def test_gsv_only_complete_cycles_and_expiry(self):
        p = Parser();p.feed(gga(),1)
        p.feed(sentence('GPGSV,2,1,05,01,45,180,40,02,20,90,30,03,10,0,20,04,30,200,35,1'),1)
        self.assertFalse(p.snapshot(1)['signals'])
        p.feed(sentence('GPGSV,2,2,05,05,60,220,45,1'),1.01)
        self.assertEqual(len(p.snapshot(1.1)['signals']),5)
        p.feed(gga('120004.00'),5)
        self.assertFalse(p.snapshot(5)['signals'])

    def test_gst_requires_same_epoch(self):
        p=Parser();p.feed(gga(),1)
        p.feed(sentence('GNGST,120000.00,1,1,1,0,0.1,0.2,0.3'),1)
        self.assertEqual(p.snapshot(1)['solution']['sigma_lat_m'],.1)
        p.feed(gga('120000.10'),1.1)
        self.assertNotIn('sigma_lat_m',p.snapshot(1.1)['solution'])

    def test_ack_is_not_nmea_checksum(self):
        line=sentence('command,MODE,response: OK',True)
        self.assertTrue(checked(line,True).endswith('OK'))
        with self.assertRaises(ValueError):checked(line)

    def test_clock_reset_does_not_invent_rate(self):
        p=Parser();p.feed(gga('120001.00'),1);p.feed(gga('120000.00'),2)
        self.assertIsNone(p.snapshot(2)['measurement_hz'])
        self.assertEqual(p.discontinuities,1)


class SessionTests(unittest.TestCase):
    def test_close_hash_export_and_recovery(self):
        with tempfile.TemporaryDirectory() as root:
            s=Sessions(root);r=s.start('banco',{})
            with self.assertRaises(ValueError):s.export(r['id'],'stream.bin')
            s.append(b'abc\x00\xff');closed=s.stop()
            self.assertEqual(closed['state'],'closed')
            self.assertEqual(closed['sha256'],hashlib.sha256(b'abc\x00\xff').hexdigest())
            self.assertEqual(s.export(r['id'],'stream.bin').read_bytes(),b'abc\x00\xff')
            self.assertEqual(s.stop()['state'],'idle')
            with self.assertRaises(ValueError):s.export('../','stream.bin')
            manifest=Path(root)/r['id']/'manifest.json'
            saved=json.loads(manifest.read_text());saved['state']='recording';manifest.write_text(json.dumps(saved))
            self.assertEqual(Sessions(root).catalog()['sessions'][0]['state'],'interrupted')

    def test_reject_second_start(self):
        with tempfile.TemporaryDirectory() as root:
            s=Sessions(root);s.start('first',{})
            try:
                with self.assertRaises(ValueError):s.start('second',{})
            finally:s.stop()

class StreamTests(unittest.TestCase):
    def test_native_payload_with_fake_nmea_is_not_parsed(self):
        from gnss.stream import Stream, unicore_crc
        header=bytearray(24);header[:3]=b'\xaa\x44\xb5';header[4:6]=(12).to_bytes(2,'little')
        payload=gga()+b'\r\n';header[6:8]=len(payload).to_bytes(2,'little')
        native=bytes(header)+payload;native+=unicore_crc(native).to_bytes(4,'little')
        stream=Stream();rows=[]
        for byte in native+gga()+b'\r\n':rows+=stream.feed(bytes([byte]))
        self.assertEqual(len(rows),1)
        self.assertEqual(stream.native_counts,{12:1})
        self.assertEqual(stream.native_errors,0)

    def test_blank_gst_is_unavailable_not_corrupt(self):
        p=Parser();p.feed(gga(),1);p.feed(sentence('GPGST,120000.00,,,,,,,'),1)
        self.assertEqual(p.rejected,0)
        self.assertNotIn('sigma_lat_m',p.snapshot(1)['solution'])

class BaseAdapterTests(unittest.TestCase):
    def receiver(self):
        import threading
        from types import SimpleNamespace
        from gnss.receiver import Receiver
        r=Receiver.__new__(Receiver)
        r.operation=threading.Lock();r.sessions=SimpleNamespace(active=None)
        r.ntrip=SimpleNamespace(snapshot=lambda:{'state':'stopped'});r.caster=None
        r.mode='MODE BASE';r._command=lambda command,query_prefix=None:{'command':command,'ack':True}
        r.snapshot=lambda:{'solution':{'latitude_deg':0,'longitude_deg':0,'height_m':102}}
        return r

    def test_known_arp_verified_without_double_height(self):
        r=self.receiver()
        result=r.apply_base({'method':'known','station_id':1,'datum':'WGS84','latitude_deg':0,'longitude_deg':0,'arp_ellipsoid_height_m':102})
        self.assertTrue(result['coordinate_readback'])
        self.assertIn('102.0000',result['results'][1]['command'])

    def test_datum_not_silently_transformed(self):
        r=self.receiver()
        with self.assertRaises(ValueError):r.apply_base({'method':'known','station_id':1,'datum':'Other datum'})
        self.assertEqual(r.last_operation['state'],'partial_or_unknown')

    def test_average_is_not_announced_as_ready(self):
        r=self.receiver()
        result=r.apply_base({'method':'average','station_id':1,'average_seconds':300,'reuse_distance_m':0})
        self.assertEqual(result['state'],'averaging')
        self.assertFalse(result['coordinate_readback'])
        self.assertTrue(result['receiver_may_persist_average'])

if __name__=='__main__':unittest.main()
