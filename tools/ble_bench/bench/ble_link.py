"""Enlace por Bluetooth real con `bleak`. Es lo único del banco que toca la radio.

`bleak` no viene con Python. Instalarlo una vez, en un entorno propio del banco:

    python3 -m venv ~/.venvs/meridian-bench
    ~/.venvs/meridian-bench/bin/python -m pip install "bleak>=0.22"

y correr el banco con ese intérprete (`~/.venvs/meridian-bench/bin/python tools/ble_bench …`).
Si pip no encuentra ruedas de pyobjc para el Python por defecto, crear el entorno con
`/usr/bin/python3` (3.9): el banco corre desde 3.9.
La primera vez, macOS pide permiso de Bluetooth para la Terminal.

Lo que dice aquí de la pila de macOS está tomado de la documentación de bleak y
**no se ha comprobado contra el Meridian V**: el MTU que informa `mtu_size` y si
la escritura sin respuesta espera hueco en la pila son cosas a medir mañana.
"""
from __future__ import annotations

import asyncio

from . import protocol as p
from .link import Link, LinkError, NotifyCallback

INSTALL_HINT = ("falta bleak. Instalar una vez:\n"
                "  python3 -m venv ~/.venvs/meridian-bench\n"
                "  ~/.venvs/meridian-bench/bin/python -m pip install \"bleak>=0.22\"\n"
                "y correr el banco con ~/.venvs/meridian-bench/bin/python")
SCAN_TIMEOUT_S = 15.0
CONNECT_TIMEOUT_S = 20.0


def _bleak():
    try:
        import bleak  # noqa: F401
        from bleak import BleakClient, BleakScanner
    except ImportError as error:
        raise LinkError(INSTALL_HINT) from error
    return BleakClient, BleakScanner


class BleakLink(Link):
    """Una conexión al Meridian V. Se crea una nueva para cada intento."""

    def __init__(self, address: str | None = None, name: str | None = None):
        self.address = address
        self.name = name
        self._client = None
        self._device = None
        self._requested_disconnect = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self.on_unexpected_disconnect = None

    @property
    def description(self) -> str:
        if self._device is None:
            return "Meridian V por Bluetooth (sin conectar)"
        return f"{self._device.name or 'sin nombre'} [{self._device.address}] por Bluetooth"

    @property
    def is_connected(self) -> bool:
        return self._client is not None and self._client.is_connected

    @property
    def negotiated_mtu(self) -> int | None:
        if not self.is_connected:
            return None
        try:
            return int(self._client.mtu_size)
        except Exception:
            return None

    async def _find(self):
        _, BleakScanner = _bleak()
        if self.address:
            device = await BleakScanner.find_device_by_address(self.address, timeout=SCAN_TIMEOUT_S)
        else:
            wanted = (self.name or "").lower()

            def matches(device, advertisement) -> bool:
                if wanted:
                    return wanted in (device.name or advertisement.local_name or "").lower()
                # El equipo anuncia el UUID del servicio (ble_transport.cpp:164).
                return p.SERVICE_UUID in [uuid.lower() for uuid in advertisement.service_uuids]
            device = await BleakScanner.find_device_by_filter(matches, timeout=SCAN_TIMEOUT_S)
        if device is None:
            raise LinkError("no se encontró el Meridian V anunciándose (¿Bluetooth del equipo apagado "
                            "o ya conectado a un teléfono? El firmware solo admite un cliente)")
        return device

    async def connect(self) -> None:
        BleakClient, _ = _bleak()
        self._loop = asyncio.get_running_loop()
        self._device = await self._find()
        self._requested_disconnect = False
        self._client = BleakClient(self._device, disconnected_callback=self._disconnected,
                                   timeout=CONNECT_TIMEOUT_S)
        try:
            await self._client.connect()
        except Exception as error:
            raise LinkError(f"no conectó: {type(error).__name__}: {error}") from error
        if self._client.services.get_service(p.SERVICE_UUID) is None:
            raise LinkError("conectado, pero sin el servicio a04c0001: ¿es un Meridian V?")

    def _disconnected(self, _client) -> None:
        # bleak dice que lo llama en el bucle de eventos; si no fuera así, se pasa
        # al bucle igualmente: el banco no es seguro entre hilos.
        if not self._requested_disconnect and self.on_unexpected_disconnect:
            self._loop.call_soon_threadsafe(self.on_unexpected_disconnect)

    async def disconnect(self) -> None:
        self._requested_disconnect = True
        if self._client is not None:
            try:
                await self._client.disconnect()
            finally:
                self._client = None

    def properties(self, characteristic_uuid: str) -> set[str]:
        if self._client is None:
            return set()
        characteristic = self._client.services.get_characteristic(characteristic_uuid)
        return set(characteristic.properties) if characteristic is not None else set()

    async def start_notify(self, characteristic_uuid: str, callback: NotifyCallback) -> None:
        if not self.is_connected:
            raise LinkError("sin conexión")
        await self._client.start_notify(characteristic_uuid, lambda _sender, data: callback(bytes(data)))

    async def write(self, characteristic_uuid: str, data: bytes, with_response: bool) -> None:
        if not self.is_connected:
            raise LinkError("sin conexión")
        try:
            await self._client.write_gatt_char(characteristic_uuid, data, response=with_response)
        except Exception as error:
            raise LinkError(f"{type(error).__name__}: {error}") from error
