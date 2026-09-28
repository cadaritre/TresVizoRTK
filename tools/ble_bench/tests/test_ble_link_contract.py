"""`BleakLink` contra un `bleak` falso: comprueba cómo usa el banco la API de bleak.

No prueba bleak ni la radio (bleak no está instalado hoy). Prueba que el
adaptador llama a lo que la documentación de bleak dice que existe, que no
confunde una desconexión pedida con una inesperada y que lee las propiedades
descubiertas de verdad (no la versión del firmware).
"""
import asyncio
import sys
import types
import unittest

from bench import protocol as p
from bench.link import LinkError


class FakeCharacteristic:
    def __init__(self, properties):
        self.properties = list(properties)


class FakeServices:
    def __init__(self, table):
        self.table = table

    def get_service(self, uuid):
        return object() if uuid == p.SERVICE_UUID else None

    def get_characteristic(self, uuid):
        props = self.table.get(uuid)
        return FakeCharacteristic(props) if props is not None else None


class FakeDevice:
    name = "MeridianV-TEST"
    address = "00000000-0000-0000-0000-000000000000"


class FakeAdvertisement:
    local_name = "MeridianV-TEST"
    service_uuids = [p.SERVICE_UUID.upper()]


TABLE_V3 = {p.COMMAND_UUID: ["write"], p.RESPONSE_UUID: ["notify"], p.SOLUTION_UUID: ["notify"],
            p.CORRECTION_UUID: ["write", "write-without-response"], p.HEALTH_UUID: ["notify"]}


class FakeClient:
    table = TABLE_V3
    instances = []

    def __init__(self, device, disconnected_callback=None, timeout=10.0):
        self.device = device
        self.disconnected_callback = disconnected_callback
        self.is_connected = False
        self.mtu_size = 247
        self.services = FakeServices(self.table)
        self.writes = []
        self.notify = {}
        FakeClient.instances.append(self)

    async def connect(self):
        self.is_connected = True

    async def disconnect(self):
        self.is_connected = False
        if self.disconnected_callback:
            self.disconnected_callback(self)

    async def start_notify(self, uuid, callback):
        self.notify[uuid] = callback

    async def write_gatt_char(self, uuid, data, response=None):
        self.writes.append((uuid, bytes(data), response))

    def drop(self):
        self.is_connected = False
        self.disconnected_callback(self)


class FakeScanner:
    @staticmethod
    async def find_device_by_filter(filterfunc, timeout=10.0):
        return FakeDevice() if filterfunc(FakeDevice(), FakeAdvertisement()) else None

    @staticmethod
    async def find_device_by_address(address, timeout=10.0):
        return FakeDevice() if address == FakeDevice.address else None


def install_fake_bleak():
    module = types.ModuleType("bleak")
    module.BleakClient = FakeClient
    module.BleakScanner = FakeScanner
    sys.modules["bleak"] = module


class BleakLinkContract(unittest.TestCase):
    def setUp(self):
        self.saved = sys.modules.get("bleak")
        install_fake_bleak()
        FakeClient.table = TABLE_V3
        FakeClient.instances = []

    def tearDown(self):
        if self.saved is None:
            sys.modules.pop("bleak", None)
        else:
            sys.modules["bleak"] = self.saved

    def test_connect_properties_write_and_requested_disconnect(self):
        from bench.ble_link import BleakLink
        unexpected = []

        async def scenario():
            link = BleakLink()
            link.on_unexpected_disconnect = lambda: unexpected.append(1)
            await link.connect()
            self.assertTrue(link.is_connected)
            self.assertEqual(link.negotiated_mtu, 247)
            self.assertIn("write-without-response", link.properties(p.CORRECTION_UUID))
            received = []
            await link.start_notify(p.HEALTH_UUID, received.append)
            FakeClient.instances[-1].notify[p.HEALTH_UUID](None, bytearray(b"\x01" * 20))
            self.assertEqual(received, [b"\x01" * 20])
            await link.write(p.CORRECTION_UUID, b"\xd3\x00", with_response=False)
            self.assertEqual(FakeClient.instances[-1].writes, [(p.CORRECTION_UUID, b"\xd3\x00", False)])
            await link.disconnect()
            self.assertFalse(link.is_connected)
        asyncio.run(scenario())
        self.assertEqual(unexpected, [], "una desconexión pedida no es inesperada")

    def test_unexpected_drop_is_reported(self):
        from bench.ble_link import BleakLink
        unexpected = []

        async def scenario():
            link = BleakLink(address=FakeDevice.address)
            link.on_unexpected_disconnect = lambda: unexpected.append(1)
            await link.connect()
            FakeClient.instances[-1].drop()
            await asyncio.sleep(0)  # el aviso llega por el bucle de eventos
            with self.assertRaises(LinkError):
                await link.write(p.COMMAND_UUID, b"{}\n", with_response=True)
        asyncio.run(scenario())
        self.assertEqual(unexpected, [1])

    def test_stale_table_is_seen_as_is(self):
        from bench.ble_link import BleakLink
        FakeClient.table = {p.COMMAND_UUID: ["write"], p.RESPONSE_UUID: ["notify"], p.SOLUTION_UUID: ["notify"],
                            p.CORRECTION_UUID: ["write"]}

        async def scenario():
            link = BleakLink()
            await link.connect()
            self.assertEqual(link.properties(p.HEALTH_UUID), set())
            self.assertEqual(link.properties(p.CORRECTION_UUID), {"write"})
            await link.disconnect()
        asyncio.run(scenario())

    def test_missing_bleak_says_how_to_install(self):
        sys.modules["bleak"] = None  # import bleak → ImportError
        from bench.ble_link import BleakLink

        async def scenario():
            with self.assertRaises(LinkError) as caught:
                await BleakLink().connect()
            self.assertIn("pip install", str(caught.exception))
        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()
