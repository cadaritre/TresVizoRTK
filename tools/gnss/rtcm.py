"""Framing RTCM3; CRC24Q y tamaño máximo del protocolo."""

def crc24q(data):
    crc = 0
    for value in data:
        crc ^= value << 16
        for _ in range(8):
            crc <<= 1
            if crc & 0x1000000: crc ^= 0x1864CFB
    return crc & 0xffffff


class Framer:
    def __init__(self):
        self.buffer = bytearray()
        self.accepted = self.rejected = 0

    def feed(self, data):
        self.buffer.extend(data)
        frames = []
        while self.buffer:
            if self.buffer[0] != 0xd3:
                del self.buffer[0]; continue
            if len(self.buffer) < 3: break
            if self.buffer[1] & 0xfc:
                del self.buffer[0];self.rejected += 1;continue
            length = ((self.buffer[1] & 3) << 8) | self.buffer[2]
            total = length + 6
            if len(self.buffer) < total: break
            frame = bytes(self.buffer[:total])
            if crc24q(frame[:-3]) != int.from_bytes(frame[-3:], 'big'):
                self.rejected += 1;del self.buffer[0];continue
            del self.buffer[:total]
            self.accepted += 1
            frames.append(frame)
        return frames
