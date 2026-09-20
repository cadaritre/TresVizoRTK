"""Demultiplexor de NMEA/control ASCII, binario Unicore y RTCM3."""
import binascii
from .rtcm import crc24q


def unicore_crc(data):
    return (binascii.crc32(data, 0xffffffff) ^ 0xffffffff) & 0xffffffff


class Stream:
    def __init__(self):
        self.buffer = bytearray()
        self.native_counts = {}
        self.native_errors = 0
        self.rtcm_errors = 0
        self.overflow = 0

    def feed(self, data):
        self.buffer.extend(data)
        result = []
        while self.buffer:
            first = self.buffer[0]
            if first == 0xaa:
                if len(self.buffer) < 8: break
                if self.buffer[:3] != b'\xaa\x44\xb5':
                    del self.buffer[0]; continue
                total = int.from_bytes(self.buffer[6:8], 'little') + 28
                if total > 16384:
                    self.native_errors += 1;del self.buffer[0];continue
                if len(self.buffer) < total: break
                frame = bytes(self.buffer[:total])
                if unicore_crc(frame[:-4]) != int.from_bytes(frame[-4:], 'little'):
                    self.native_errors += 1;del self.buffer[0];continue
                identity = int.from_bytes(frame[4:6], 'little')
                self.native_counts[identity] = self.native_counts.get(identity,0) + 1
                del self.buffer[:total]
            elif first == 0xd3:
                if len(self.buffer) < 3:break
                if self.buffer[1] & 0xfc:del self.buffer[0];continue
                total = (((self.buffer[1] & 3) << 8) | self.buffer[2]) + 6
                if len(self.buffer) < total:break
                frame=bytes(self.buffer[:total])
                if crc24q(frame[:-3]) != int.from_bytes(frame[-3:],'big'):
                    self.rtcm_errors += 1;del self.buffer[0];continue
                result.append(('rtcm',frame));del self.buffer[:total]
            elif first in (ord('$'),ord('#')):
                end=self.buffer.find(b'\n')
                if end < 0:
                    if len(self.buffer)>8192: self.overflow += 1;del self.buffer[0];continue
                    break
                line=bytes(self.buffer[:end]).rstrip(b'\r');del self.buffer[:end+1]
                if len(line)<=8192:result.append(('ascii',line))
                else:self.overflow += 1
            else:del self.buffer[0]
        return result
