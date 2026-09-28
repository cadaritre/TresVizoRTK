"""El enlace que usa el banco: la radio de verdad (`ble_link.py`) o el simulador.

Los escenarios solo conocen esta interfaz, así que corren igual contra el
Meridian V por Bluetooth que contra el simulador en proceso de las pruebas.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable

NotifyCallback = Callable[[bytes], None]


class LinkError(RuntimeError):
    """Fallo del enlace: conexión, descubrimiento, suscripción o escritura."""


class Link(ABC):
    #: Se llama cuando el enlace se cae sin que el banco lo pidiera.
    on_unexpected_disconnect: Callable[[], None] | None = None

    @property
    @abstractmethod
    def description(self) -> str: ...

    @property
    @abstractmethod
    def is_connected(self) -> bool: ...

    @property
    @abstractmethod
    def negotiated_mtu(self) -> int | None:
        """MTU ATT que ve este lado, o None si la pila no lo dice."""

    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Desconexión pedida. No llama a `on_unexpected_disconnect`."""

    @abstractmethod
    def properties(self, characteristic_uuid: str) -> set[str]:
        """Propiedades GATT anunciadas: 'write', 'write-without-response', 'notify'…"""

    @abstractmethod
    async def start_notify(self, characteristic_uuid: str, callback: NotifyCallback) -> None: ...

    @abstractmethod
    async def write(self, characteristic_uuid: str, data: bytes, with_response: bool) -> None:
        """Escribe. Con respuesta espera la confirmación ATT; sin ella, el hueco de la pila."""
