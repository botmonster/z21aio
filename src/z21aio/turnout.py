"""Turnout/accessory control.

Provides the Turnout class for controlling DCC turnouts via Z21.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import logging
from typing import TYPE_CHECKING

from z21aio.packet import Packet

from .messages import XBUS_TURNOUT_INFO, XBusMessage
from .types import TurnoutPosition, TurnoutState

if TYPE_CHECKING:
    from .station import Z21Station

log = logging.getLogger(__name__)

# Default timing for activate/deactivate in immediate (Q=0) mode
DEFAULT_ACTIVATE_DURATION = 0.15  # 150ms per protocol recommendation


class Turnout:
    """Turnout/accessory controller.

    Provides methods for controlling a single DCC turnout including
    switching outputs and subscribing to state updates.

    Example:
        turnout = Turnout(station, address=0)
        await turnout.switch(TurnoutPosition.P0)
        await turnout.switch(TurnoutPosition.P1)
    """

    def __init__(self, station: Z21Station, address: int) -> None:
        """Initialize turnout controller.

        Args:
            station: Z21Station instance
            address: Turnout function address (0-2047)
        """
        self._station = station
        self._address = address

    @property
    def address(self) -> int:
        """Turnout function address."""
        return self._address

    async def switch(
        self,
        position: TurnoutPosition,
        *,
        queue_mode: bool = True,
        activate_duration: float = DEFAULT_ACTIVATE_DURATION,
    ) -> None:
        """Switch turnout to the specified position.

        In queue mode (default), the Z21 handles activate/deactivate timing
        internally. In immediate mode (queue_mode=False), this method sends
        activate, waits for activate_duration, then sends deactivate.

        Args:
            position: Target position (P0 or P1)
            queue_mode: Use Z21 queue mode for timing (default True)
            activate_duration: Duration in seconds for activate pulse
                             in immediate mode (default 150ms)

        Raises:
            ValueError: If position is UNKNOWN or INVALID
        """
        if position not in (TurnoutPosition.P0, TurnoutPosition.P1):
            raise ValueError(
                f"Can only switch to P0 or P1, got {position.name}"
            )

        output = position.value - 1  # P0=1 -> output 0, P1=2 -> output 1

        if queue_mode:
            msg = XBusMessage.set_turnout(
                self._address, output, activate=True, queue_mode=True
            )
            await self._station.send_xbus_command(msg)
        else:
            activate_msg = XBusMessage.set_turnout(
                self._address, output, activate=True, queue_mode=False
            )
            await self._station.send_xbus_command(activate_msg)

            await asyncio.sleep(activate_duration)

            deactivate_msg = XBusMessage.set_turnout(
                self._address, output, activate=False, queue_mode=False
            )
            await self._station.send_xbus_command(deactivate_msg)

    async def activate(self, output: int, *, queue_mode: bool = True) -> None:
        """Activate a specific turnout output.

        Low-level method for direct output control.

        Args:
            output: Output number (0 or 1)
            queue_mode: Use Z21 queue mode (default True)
        """
        msg = XBusMessage.set_turnout(
            self._address, output, activate=True, queue_mode=queue_mode
        )
        await self._station.send_xbus_command(msg)

    async def deactivate(self, output: int, *, queue_mode: bool = True) -> None:
        """Deactivate a specific turnout output.

        Low-level method for direct output control.

        Args:
            output: Output number (0 or 1)
            queue_mode: Use Z21 queue mode (default True)
        """
        msg = XBusMessage.set_turnout(
            self._address, output, activate=False, queue_mode=queue_mode
        )
        await self._station.send_xbus_command(msg)

    async def get_state(self) -> TurnoutState:
        """Get current turnout state.

        Returns:
            TurnoutState with current position

        Raises:
            TimeoutError: If no response received
        """
        msg = XBusMessage.get_turnout_info(self._address)
        response = await self._station.send_xbus_command(
            msg, XBUS_TURNOUT_INFO
        )
        if response is None:
            raise RuntimeError("No response received")

        state = TurnoutState.from_bytes(response.dbs)
        log.debug("Got turnout state %s", state)
        return state

    def subscribe_state(
        self,
        callback: Callable[[TurnoutState], None],
    ) -> None:
        """Subscribe to turnout state updates.

        The callback will be called whenever the station broadcasts
        an update for this turnout's address.

        Args:
            callback: Function called with TurnoutState on each update
        """

        def handle_packet(packet: Packet) -> None:
            try:
                xbus_msg = XBusMessage.from_bytes(packet.data)
                if (
                    xbus_msg.x_header == XBUS_TURNOUT_INFO
                    and len(xbus_msg.dbs) == 3
                ):
                    state = TurnoutState.from_bytes(xbus_msg.dbs)
                    if state.address == self._address:
                        callback(state)
            except (ValueError, TypeError) as e:
                log.error(
                    "Got exception handling packet in turnout state callback %s",
                    e,
                )

        if XBUS_TURNOUT_INFO not in self._station._subscribers:
            self._station._subscribers[XBUS_TURNOUT_INFO] = []
        self._station._subscribers[XBUS_TURNOUT_INFO].append(handle_packet)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"Turnout(address={self._address})"
