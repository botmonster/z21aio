"""
Locomotive control.

Provides the Loco class for controlling DCC locomotives via Z21.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import logging
from typing import TYPE_CHECKING

from .messages import (
    XBUS_LOCO_INFO,
    XBusMessage,
)
from .types import DccThrottleSteps, FunctionAction, LocoState, RailComData

if TYPE_CHECKING:
    from .station import Z21Station

log = logging.getLogger(__name__)


def _calc_speed_byte(steps: DccThrottleSteps, speed_percent: float) -> int:
    """
    Calculate speed byte from percentage and throttle steps.

    Args:
        steps: Throttle step mode
        speed_percent: Speed as percentage (-100 to 100, negative = reverse)

    Returns:
        Speed byte with direction bit (bit 7)
    """
    # Clamp speed to valid range
    speed_percent = max(-100.0, min(100.0, speed_percent))

    # Calculate direction and absolute speed
    forward = speed_percent >= 0
    abs_speed = abs(speed_percent)

    # Map percentage to throttle steps
    max_speed = steps.max_speed
    speed_value = int((abs_speed / 100.0) * max_speed)

    # Clamp to valid range (0-127 for step values)
    speed_value = min(speed_value, 127)

    # Combine with direction bit
    if forward:
        return speed_value | 0x80
    else:
        return speed_value


class Loco:
    """
    Locomotive controller.

    Provides methods for controlling a single DCC locomotive including
    speed, direction, and function control.

    Example:
        loco = await Loco.control(station, address=3)
        await loco.set_headlights(True)
        await loco.drive(50.0)  # 50% forward
        await loco.stop()
    """

    def __init__(
        self,
        station: Z21Station,
        address: int,
        steps: DccThrottleSteps = DccThrottleSteps.STEPS_128,
    ) -> None:
        """
        Initialize locomotive controller.

        Use Loco.control() class method for proper initialization.

        Args:
            station: Z21Station instance
            address: DCC locomotive address (1-9999)
            steps: Throttle step mode (default 128 steps)
        """
        self._station = station
        self._address = address
        self._steps = steps
        self._railcom: RailComData | None = None

    @classmethod
    async def control(
        cls,
        station: Z21Station,
        address: int,
        steps: DccThrottleSteps = DccThrottleSteps.STEPS_128,
    ) -> Loco:
        """
        Get control of a locomotive.

        Args:
            station: Z21Station instance
            address: DCC locomotive address (1-9999)
            steps: Throttle step mode (default 128 steps)

        Returns:
            Loco instance ready for control
        """
        loco = cls(station, address, steps)

        # Request initial state to "register" with the station
        try:
            await loco.get_state()
        except asyncio.TimeoutError:
            # It's OK if we don't get a response - loco may not be on track
            pass

        return loco

    @property
    def address(self) -> int:
        """DCC address of this locomotive."""
        return self._address

    @property
    def steps(self) -> DccThrottleSteps:
        """Throttle step mode for this locomotive."""
        return self._steps

    async def drive(self, speed_percent: float) -> None:
        """
        Set locomotive speed and direction.

        Args:
            speed_percent: Speed as percentage (-100 to 100)
                          Positive = forward, negative = reverse
        """
        speed_byte = _calc_speed_byte(self._steps, speed_percent)
        msg = XBusMessage.loco_drive(self._address, self._steps, speed_byte)
        await self._station.send_xbus_command(msg)

    async def stop(self) -> None:
        """
        Normal stop with braking curve.

        The locomotive will decelerate according to its decoder settings.
        """
        msg = XBusMessage.loco_drive(self._address, self._steps, 0x00)
        await self._station.send_xbus_command(msg)

    async def halt(self) -> None:
        """
        Emergency stop (immediate halt).

        The locomotive will stop immediately without deceleration.
        """
        msg = XBusMessage.loco_drive(self._address, self._steps, 0x01)
        await self._station.send_xbus_command(msg)

    async def set_function(self, index: int, action: FunctionAction) -> None:
        """
        Set a locomotive function.

        Args:
            index: Function number (0-31)
            action: Action to perform (OFF, ON, TOGGLE)

        Raises:
            ValueError: If index is not 0-31
        """
        if not 0 <= index <= 31:
            raise ValueError(f"Function index must be 0-31, got {index}")

        msg = XBusMessage.loco_function(self._address, index, action)
        await self._station.send_xbus_command(msg)

    async def function_on(self, index: int) -> None:
        """
        Turn on a locomotive function.

        Args:
            index: Function number (0-31)
        """
        await self.set_function(index, FunctionAction.ON)

    async def function_off(self, index: int) -> None:
        """
        Turn off a locomotive function.

        Args:
            index: Function number (0-31)
        """
        await self.set_function(index, FunctionAction.OFF)

    async def function_toggle(self, index: int) -> None:
        """
        Toggle a locomotive function.

        Args:
            index: Function number (0-31)
        """
        await self.set_function(index, FunctionAction.TOGGLE)

    async def set_headlights(self, on: bool) -> None:
        """
        Turn headlights on or off (F0).

        Args:
            on: True to turn on, False to turn off
        """
        action = FunctionAction.ON if on else FunctionAction.OFF
        await self.set_function(0, action)

    async def get_state(self) -> LocoState:
        """
        Get current locomotive state.

        Returns:
            LocoState with current speed, direction, and function states

        Raises:
            asyncio.TimeoutError: If no response received
        """
        msg = XBusMessage.loco_get_info(self._address)
        response = await self._station.send_xbus_command(msg, XBUS_LOCO_INFO)
        if response is None:
            raise RuntimeError("No response received")

        state = LocoState.from_bytes(response.dbs)
        log.debug(f"Got loco state {state}")

        return state

    def subscribe_state(
        self,
        callback: Callable[[LocoState], None],
    ) -> None:
        """
        Subscribe to locomotive state updates.

        The callback will be called whenever the station broadcasts
        an update for this locomotive's address.

        Args:
            callback: Function called with LocoState on each update
        """

        def handle_packet(packet: "XBusMessage") -> None:  # type: ignore[name-defined]
            try:
                xbus_msg = XBusMessage.from_bytes(packet.data)
                if xbus_msg.x_header == XBUS_LOCO_INFO:
                    state = LocoState.from_bytes(xbus_msg.dbs)
                    if state.address == self._address:
                        callback(state)
            except Exception as e:
                log.error(f"Got exception handling packet in loco state callback {e}")
                pass

        if XBUS_LOCO_INFO not in self._station._subscribers:
            self._station._subscribers[XBUS_LOCO_INFO] = []
        self._station._subscribers[XBUS_LOCO_INFO].append(handle_packet)

    @property
    def railcom(self) -> RailComData | None:
        """
        Current RailCom data for this locomotive.

        Returns None if no RailCom subscription is active or no data received.
        Subscribe with subscribe_railcom() to receive updates.
        """
        return self._railcom

    async def get_railcom_data(self, timeout: float | None = None) -> RailComData:
        """
        Request RailCom data for this locomotive.

        Args:
            timeout: Response timeout in seconds (uses station default if None)

        Returns:
            RailComData for this locomotive

        Raises:
            asyncio.TimeoutError: If no response within timeout

        Note:
            Requires firmware 1.29+ and RailCom-capable decoder
        """
        return await self._station.get_railcom_data(self._address, timeout)

    def subscribe_railcom(
        self,
        callback: Callable[[RailComData], None] | None = None,
    ) -> None:
        """
        Subscribe to RailCom data updates for this locomotive.

        Updates the railcom property and optionally calls a callback.

        Args:
            callback: Optional function called with RailComData on each update.
                     If None, only updates the railcom property.

        Note:
            Requires enabling RailCom broadcasts on the station first.
        """

        def handle_railcom(railcom_data: RailComData) -> None:
            self._railcom = railcom_data
            if callback is not None:
                callback(railcom_data)

        self._station.subscribe_railcom(handle_railcom, self._address)

    def __repr__(self) -> str:
        return f"Loco(address={self._address}, steps={self._steps.name})"
