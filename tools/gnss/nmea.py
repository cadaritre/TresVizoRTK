"""NMEA de banco: checksum, épocas, GGA/GST/RMC y ciclos completos GSV."""
from collections import deque
from datetime import datetime, timezone
import copy
import math
import re
import time


def checked(line, include_start=False):
    if not line.startswith((b'$', b'#')) or len(line) > 8192:
        raise ValueError('invalid_sentence')
    body, checksum = line.rstrip(b'\r\n')[1:].rsplit(b'*', 1)
    value = line[0] if include_start else 0
    for byte in body:
        value ^= byte
    if not re.fullmatch(b'[0-9A-Fa-f]{2}', checksum) or value != int(checksum, 16):
        raise ValueError('checksum')
    return body.decode('ascii')


def number(value, low=-math.inf, high=math.inf):
    result = float(value)
    if not math.isfinite(result) or not low <= result <= high:
        raise ValueError('range')
    return result


def utc_ms(value):
    if not re.fullmatch(r'\d{6}(\.\d+)?', value):
        raise ValueError('utc')
    return round((int(number(value[:2], 0, 23)) * 3600 +
                  int(number(value[2:4], 0, 59)) * 60 + number(value[4:], 0, 59.999)) * 1000)


def coordinate(value, hemisphere, latitude):
    width = 2 if latitude else 3
    if not re.fullmatch(r'\d{' + str(width + 2) + r'}(\.\d+)?', value):
        raise ValueError('coordinate')
    if hemisphere not in ('NS' if latitude else 'EW'):
        raise ValueError('hemisphere')
    result = int(value[:width]) + number(value[width:], 0, 59.999999999) / 60
    number(str(result), 0, 90 if latitude else 180)
    return -result if hemisphere in 'SW' else result


class Parser:
    def __init__(self):
        self.solution = {}
        self.accepted = self.rejected = self.duplicates = self.discontinuities = 0
        self.epochs = deque(maxlen=101)
        self.last_epoch = None
        self.last_arrival = None
        self.gst = None
        self.rmc = None
        self.cycles = {}
        self.signals = {}
        self.sequence = 0
        self.history = deque(maxlen=200)

    def feed(self, line, now=None):
        now = time.monotonic() if now is None else now
        try:
            body = checked(line)
            f = body.split(',')
            kind = f[0][-3:]
            if len(f[0]) != 5 or kind not in ('GGA', 'GST', 'RMC', 'GSV'):
                return
            if kind == 'GGA':
                self._gga(f, now)
            elif kind == 'GST':
                if len(f) != 9:
                    raise ValueError('gst')
                if any(not f[i] for i in (1,6,7,8)):
                    self.gst = None
                    self.accepted += 1
                    return
                self.gst = {'epoch': utc_ms(f[1]), 'arrival': now,
                            'sigma_lat_m': number(f[6], 0), 'sigma_lon_m': number(f[7], 0),
                            'sigma_height_m': number(f[8], 0)}
            elif kind == 'RMC':
                if len(f) < 10 or f[2] != 'A':
                    self.rmc = None
                    return
                epoch = utc_ms(f[1])
                date = datetime.strptime(f[9], '%d%m%y').replace(tzinfo=timezone.utc)
                self.rmc = {'epoch': epoch, 'arrival': now, 'date': date.date().isoformat(),
                            'speed_mps': number(f[7], 0) * 0.514444 if f[7] else None,
                            'course_deg': number(f[8], 0, 360) if f[8] else None}
            else:
                self._gsv(f, now)
            self.accepted += 1
        except (ValueError, UnicodeError, IndexError, OverflowError):
            self.rejected += 1

    def _gga(self, f, now):
        if len(f) != 15 or not re.fullmatch('[0-8]', f[6]):
            raise ValueError('gga')
        quality = int(f[6])
        epoch = utc_ms(f[1]) if f[1] else None
        sats = int(number(f[7], 0, 255)) if f[7] else None
        solution = {'quality': quality, 'utc_time_of_day_ms': epoch,
                    'arrival_monotonic_us': round(now * 1e6), 'satellites_used': sats,
                    'latitude_deg': None, 'longitude_deg': None, 'height_m': None,
                    'height_reference': 'receiver_msl', 'hdop': number(f[8], 0) if f[8] else None,
                    'correction_age_s': number(f[13], 0) if f[13] else None,
                    'geoid_separation_m': number(f[11]) if f[11] else None}
        if quality:
            if epoch is None or f[10] != 'M' or (f[11] and f[12] != 'M'):
                raise ValueError('gga_units')
            solution.update(latitude_deg=coordinate(f[2], f[3], True),
                            longitude_deg=coordinate(f[4], f[5], False), height_m=number(f[9]))
        solution['fix'] = ['invalid', 'standalone', 'differential', 'pps', 'rtk_fixed',
                           'rtk_float', 'dead_reckoning', 'manual', 'simulated'][quality]
        self.sequence += 1
        solution['sequence'] = self.sequence
        self.solution = solution
        self.last_arrival = now
        if epoch is not None:
            if epoch == self.last_epoch:
                self.duplicates += 1
            else:
                delta = None if self.last_epoch is None else epoch - self.last_epoch
                if delta is not None and self.last_epoch > 86390000 and epoch < 10000:
                    delta += 86400000
                if delta is not None and (delta <= 0 or delta > 2000):
                    self.discontinuities += 1
                    self.epochs.clear()
                accumulated = self.epochs[-1][0] + delta if self.epochs and delta is not None else 0
                self.epochs.append((accumulated, now))
                self.last_epoch = epoch
        self.history.append(copy.deepcopy(solution))

    def _gsv(self, f, now):
        total, part, count = int(f[1]), int(f[2]), int(f[3])
        if not 1 <= part <= total <= 32 or not 0 <= count <= 128:
            raise ValueError('gsv_header')
        tail = f[4:]
        signal = tail[-1] if len(tail) % 4 == 1 else ''
        if signal:
            tail = tail[:-1]
        elif len(tail) % 4 == 1:
            tail = tail[:-1]
        if len(tail) % 4 or len(tail) > 16:
            raise ValueError('gsv_fields')
        key = (f[0][:2], signal)
        if part == 1:
            self.cycles[key] = {'next': 1, 'total': total, 'rows': [], 'time': now}
        cycle = self.cycles.get(key)
        if not cycle or cycle['next'] != part or cycle['total'] != total or now - cycle['time'] > 2:
            self.cycles.pop(key, None)
            return
        rows = []
        names = {'GP': 'GPS', 'GL': 'GLONASS', 'GA': 'Galileo', 'GB': 'BeiDou', 'BD': 'BeiDou', 'GQ': 'QZSS', 'GI': 'NavIC'}
        for i in range(0, len(tail), 4):
            prn, elevation, azimuth, cn0 = tail[i:i+4]
            if not prn:
                continue
            rows.append({'constellation': names.get(key[0], key[0]), 'prn': str(int(number(prn, 1, 999))),
                         'signal_id': signal, 'elevation_deg': number(elevation, -90, 90) if elevation else None,
                         'azimuth_deg': number(azimuth, 0, 360) if azimuth else None,
                         'cn0_dbhz': number(cn0, 0, 99) if cn0 else None})
        cycle['rows'].extend(rows)
        cycle['next'] += 1
        if part == total:
            self.signals[key] = (now, cycle['rows'])
            del self.cycles[key]
        # Receptor/entradas defectuosas no pueden crear un catálogo ilimitado.
        if len(self.signals) > 64:
            del self.signals[min(self.signals, key=lambda k: self.signals[k][0])]
        if len(self.cycles) > 64:
            self.cycles.clear()

    def snapshot(self, now=None, since=0):
        now = time.monotonic() if now is None else now
        age = None if self.last_arrival is None else max(0, now - self.last_arrival)
        fresh = age is not None and age <= .5
        solution = copy.deepcopy(self.solution) if fresh else {}
        for source in (self.gst, self.rmc):
            if fresh and source and now - source['arrival'] < 1.5 and source['epoch'] == solution.get('utc_time_of_day_ms'):
                solution.update({k: v for k, v in source.items() if k not in ('epoch', 'arrival')})
        epochs = list(self.epochs)
        hz = arrival_hz = None
        if fresh and len(epochs) > 1 and epochs[-1][0] > epochs[0][0]:
            hz = (len(epochs)-1) * 1000 / (epochs[-1][0]-epochs[0][0])
            arrival_hz = (len(epochs)-1) / (epochs[-1][1]-epochs[0][1]) if epochs[-1][1] > epochs[0][1] else None
        signals = [row for stamp, rows in self.signals.values() if fresh and now - stamp < 3 for row in rows]
        return {'source': 'mac_usb', 'state': 'receiving' if fresh else ('stale' if age is not None else 'waiting_data'),
                'age_ms': round(age*1000) if age is not None else None, 'solution': solution,
                'signals': signals, 'measurement_hz': hz, 'arrival_hz': arrival_hz,
                'accepted': self.accepted, 'rejected': self.rejected, 'duplicates': self.duplicates,
                'clock_discontinuities': self.discontinuities, 'sequence': self.sequence,
                'epochs': [s for s in self.history if s['sequence'] > since] if fresh else [],
                'history_lost': bool(since and self.history and since < self.history[0]['sequence'] - 1)}
