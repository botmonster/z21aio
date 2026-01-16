"""
Z21 Station controller.

Main class for communicating with a Z21 DCC command station over UDP.
Provides async methods for station control and locomotive operations.
"""

from __future__ import annotations

import asyncio
import logging
import struct
from collections.abc import Callable
from typing import Any

from .packet import Packet
from .messages import (
    LAN_DISCOVER_DEVICES,
    LAN_GET_SERIAL_NUMBER,
    LAN_LOGOFF,
    LAN_XBUS_HEADER,
    LAN_SET_BROADCASTFLAGS,
    LAN_SYSTEMSTATE_DATACHANGED,
    LAN_SYSTEMSTATE_GETDATA,
    LAN_RAILCOM_DATACHANGED,
    LAN_RAILCOM_GETDATA,
    XBUS_GET_VERSION_REPLY,
    XBUS_GET_FIRMWARE_VERSION_REPLY,
    BROADCAST_LOCO_INFO,
    BROADCAST_RAILCOM_SUBSCRIBED,
    BROADCAST_RAILCOM_ALL,
    XBusMessage,
)
from .types import SystemState, RailComData, LocoState

log = logging.getLogger(__name__)

DEFAULT_PORT = 21105
DEFAULT_TIMEOUT = 2.0
KEEP_ALIVE_INTERVAL = 20.0
BUFFER_SIZE = 1024


class Z21Protocol(asyncio.DatagramProtocol):
    """UDP protocol handler for Z21 communication."""

    def __init__(self, station: Z21Station) -> None:
        log.debug("Initializing Z21Protocol")
        self._station = station
        self._transport: asyncio.DatagramTransport | None = None

    def connection_made(self, transport: asyncio.DatagramTransport) -> None:  # type: ignore[override]
        log.debug("UDP connection established")
        self._transport = transport

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        offset = 0
        while offset < len(data):
            try:
                packet = Packet.from_bytes(data[offset:])
                log.debug("datagram_received: %d bytes from %s %s", len(data), addr, packet)
                self._station._handle_packet(packet)
                offset += packet.data_len
            except Exception as e:
                log.error(
                    "Failed to parse packet from %s at offset %d: %s <%s>",
                    addr,
                    offset,
                    e,
                    data[offset:].hex(" "),
                )
                break

    def error_received(self, exc: Exception) -> None:
        log.error("Protocol error: %s", exc)

    def connection_lost(self, exc: Exception | None) -> None:
        if exc:
            log.error("Connection lost with error: %s", exc)
        else:
            log.debug("Connection closed")
        self._station._connection_lost = True


class Z21Station:
    """
    Z21 DCC command station controller.

    Provides async methods for communicating with a Z21 station over UDP.
    Supports multiple simultaneous connections to different stations.

    Example:
        async with await Z21Station.connect("192.168.0.111") as station:
            await station.voltage_on()
            serial = await station.get_serial_number()
            print(f"Serial: {serial}")
    """

    def __init__(self) -> None:
        self._transport: asyncio.DatagramTransport | None = None
        self._protocol: Z21Protocol | None = None
        self._timeout: float = DEFAULT_TIMEOUT
        self._host: str = ""
        self._port: int = DEFAULT_PORT

        self._keep_alive_task: asyncio.Task[None] | None = None
        self._running: bool = False
        self._connection_lost: bool = False

        # Packet routing
        self._packet_waiters: dict[int, asyncio.Queue[Packet]] = {}
        self._subscribers: dict[int, list[Callable[[Packet], None]]] = {}

        self._broadcast_flags: int = BROADCAST_LOCO_INFO

    @classmethod
    async def connect(
        cls,
        host: str,
        port: int = DEFAULT_PORT,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> Z21Station:
        """
        Connect to a Z21 station.

        Args:
            host: IP address of the Z21 station
            port: UDP port (default 21105)
            timeout: Command timeout in seconds (default 2.0)

        Returns:
            Connected Z21Station instance
        """
        station = cls()
        station._host = host
        station._port = port
        station._timeout = timeout

        loop = asyncio.get_running_loop()

        transport, protocol = await loop.create_datagram_endpoint(
            lambda: Z21Protocol(station),
            remote_addr=(host, port),
        )

        station._transport = transport
        station._protocol = protocol
        station._running = True

        station._keep_alive_task = asyncio.create_task(station._keep_alive_loop())

        await station._set_broadcast_flags(station._broadcast_flags)

        return station

    async def _keep_alive_loop(self) -> None:
        """Background task to send keep-alive packets."""
        while self._running:
            try:
                await asyncio.sleep(KEEP_ALIVE_INTERVAL)
                if self._running and not self._connection_lost:
                    await self._set_broadcast_flags(self._broadcast_flags)
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    async def _set_broadcast_flags(self, flags: int) -> None:
        """Set broadcast flags to control which events we receive."""
        data = struct.pack("<I", flags)
        packet = Packet.with_header_and_data(LAN_SET_BROADCASTFLAGS, data)
        await self.send_packet(packet)

    def _handle_packet(self, packet: Packet) -> None:
        """Route incoming packet to waiters and subscribers."""
        header = packet.header

        if header == LAN_XBUS_HEADER:
            header = XBusMessage.from_bytes(packet.data).x_header

        if header in self._packet_waiters:
            try:
                self._packet_waiters[header].put_nowait(packet)
            except asyncio.QueueFull:
                log.error(f"Queue is full on packet waiters header={header}")

        if header in self._subscribers:
            for callback in self._subscribers[header]:
                try:
                    callback(packet)
                except Exception as e:
                    log.error(f"Got callback error from subscribed header={header} {e}")

    async def send_packet(self, packet: Packet) -> None:
        """
        Send a packet to the Z21 station.

        Args:
            packet: Packet to send
        """
        log.debug("Sending packet: %s", packet)
        if self._transport is None:
            raise ConnectionError("Not connected to Z21 station")

        self._transport.sendto(packet.to_bytes())

    async def receive_packet(
        self,
        header: int,
        timeout: float | None = None,
    ) -> Packet:
        """
        Wait for a packet with the specified header.

        Args:
            header: Expected packet header
            timeout: Timeout in seconds (uses default if None)

        Returns:
            Received packet

        Raises:
            asyncio.TimeoutError: If no packet received within timeout
        """
        if timeout is None:
            timeout = self._timeout

        if header not in self._packet_waiters:
            self._packet_waiters[header] = asyncio.Queue(maxsize=100)

        queue = self._packet_waiters[header]

        try:
            return await asyncio.wait_for(queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            raise asyncio.TimeoutError(
                f"Timeout waiting for packet with header 0x{header:04X}"
            )

    async def send_xbus_command(
        self,
        msg: XBusMessage,
        expected_response_header: int | None = None,
    ) -> XBusMessage | None:
        """
        Send an XBus command and optionally wait for response.

        Args:
            msg: XBus message to send
            expected_response_header: XBus header to wait for (None = no wait)

        Returns:
            Response XBusMessage if expected_response_header specified, else None
        """
        packet = Packet.with_header_and_data(LAN_XBUS_HEADER, msg.to_bytes())
        await self.send_packet(packet)

        if expected_response_header is not None:
            response_packet = await self.receive_packet(expected_response_header)
            return XBusMessage.from_bytes(response_packet.data)

        return None

    async def get_serial_number(self) -> int:
        """
        Get the Z21 station serial number.

        Returns:
            Station serial number as integer
        """
        packet = Packet.with_header(LAN_GET_SERIAL_NUMBER)
        await self.send_packet(packet)

        response = await self.receive_packet(LAN_GET_SERIAL_NUMBER)

        if len(response.data) < 4:
            raise ValueError("Invalid serial number response")

        return struct.unpack("<I", response.data[:4])[0]

    async def discover_devices(self) -> None:
        """
        Get the Z21 station devices.

        Returns:
            None
        """
        packet = Packet.with_header(LAN_DISCOVER_DEVICES)
        await self.send_packet(packet)

    async def get_firmware_version(self) -> tuple[int, int]:
        """
        Get the Z21 station firmware version.

        Returns:
            Tuple of (major, minor) version in BCD format.
            For example, (1, 30) represents firmware version 1.30
        """
        msg = XBusMessage.get_firmware_version()
        response = await self.send_xbus_command(
            msg, expected_response_header=XBUS_GET_FIRMWARE_VERSION_REPLY
        )

        if response is None or len(response.dbs) < 3:
            raise ValueError("Invalid firmware version response")

        # Response format: DB0=0x0A, DB1=V_MSB (BCD), DB2=V_LSB (BCD)
        v_msb = response.dbs[1]  # Major version in BCD
        v_lsb = response.dbs[2]  # Minor version in BCD

        return (v_msb, v_lsb)

    async def get_version(self) -> tuple[int, int]:
        """
        Get the X-BUS protocol version and command station ID.

        Returns:
            Tuple of (xbus_version, command_station_id).
            xbus_version is in BCD format (e.g., 0x36 = version 3.6).
            command_station_id identifies the type of command station.
        """
        msg = XBusMessage.get_version()
        response = await self.send_xbus_command(
            msg, expected_response_header=XBUS_GET_VERSION_REPLY
        )

        if response is None or len(response.dbs) < 3:
            raise ValueError("Invalid version response")

        # Response format: DB0=0x21, DB1=X-BUS Version, DB2=Command Station ID
        xbus_version = response.dbs[1]
        command_station_id = response.dbs[2]

        return (xbus_version, command_station_id)

    async def voltage_on(self) -> None:
        """Turn on track power."""
        msg = XBusMessage.track_power_on()
        await self.send_xbus_command(msg)

    async def voltage_off(self) -> None:
        """Turn off track power (emergency stop all locomotives)."""
        msg = XBusMessage.track_power_off()
        await self.send_xbus_command(msg)

    async def logout(self) -> None:
        """Send logout/disconnect command to Z21."""
        packet = Packet.with_header(LAN_LOGOFF)
        await self.send_packet(packet)

    def subscribe_system_state(
        self,
        callback: Callable[[SystemState], None],
        freq_hz: float = 1.0,
    ) -> asyncio.Task[None]:
        """
        Subscribe to system state updates.

        Args:
            callback: Function called with SystemState on each update
            freq_hz: Polling frequency in Hz (default 1.0)

        Returns:
            Background task handle (can be cancelled)
        """

        async def poll_loop() -> None:
            interval = 1.0 / freq_hz if freq_hz > 0 else 1.0
            while self._running:
                try:
                    # Request system state
                    packet = Packet.with_header(LAN_SYSTEMSTATE_GETDATA)
                    await self.send_packet(packet)
                    await asyncio.sleep(interval)
                except asyncio.CancelledError:
                    break
                except Exception:
                    pass

        def handle_state(packet: Packet) -> None:
            try:
                state = SystemState.from_bytes(packet.data)
                callback(state)
            except Exception:
                pass

        # Subscribe to state change packets
        if LAN_SYSTEMSTATE_DATACHANGED not in self._subscribers:
            self._subscribers[LAN_SYSTEMSTATE_DATACHANGED] = []
        self._subscribers[LAN_SYSTEMSTATE_DATACHANGED].append(handle_state)

        # Start polling task
        return asyncio.create_task(poll_loop())

    async def enable_railcom_broadcasts(self, all_locos: bool = False) -> None:
        """
        Enable RailCom data broadcasts.

        Args:
            all_locos: If True, receive RailCom data for all locos.
                      If False (default), only receive data for subscribed locos.

        Note:
            all_locos=True requires firmware 1.29+
        """
        if all_locos:
            self._broadcast_flags |= BROADCAST_RAILCOM_ALL
        else:
            self._broadcast_flags |= BROADCAST_RAILCOM_SUBSCRIBED
        await self._set_broadcast_flags(self._broadcast_flags)

    async def disable_railcom_broadcasts(self) -> None:
        """Disable RailCom data broadcasts."""
        self._broadcast_flags &= ~(BROADCAST_RAILCOM_SUBSCRIBED | BROADCAST_RAILCOM_ALL)
        await self._set_broadcast_flags(self._broadcast_flags)

    async def get_railcom_data(
        self,
        address: int | None = None,
        timeout: float | None = None,
    ) -> RailComData:
        """
        Request RailCom data for a specific locomotive or next in queue.

        Args:
            address: DCC address to query, or None for circular polling
            timeout: Response timeout in seconds (uses default if None)

        Returns:
            RailComData for the queried locomotive

        Raises:
            asyncio.TimeoutError: If no response within timeout

        Note:
            Requires firmware 1.29+
        """
        if address is None:
            # Type 0x00 = poll next in circular queue
            data = struct.pack("<BH", 0x00, 0x0000)
        else:
            # Type 0x01 = poll specific address
            data = struct.pack("<BH", 0x01, address)

        packet = Packet.with_header_and_data(LAN_RAILCOM_GETDATA, data)
        await self.send_packet(packet)

        response = await self.receive_packet(LAN_RAILCOM_DATACHANGED, timeout)

        return RailComData.from_bytes(response.data)

    def subscribe_railcom(
        self,
        callback: Callable[[RailComData], None],
        address: int | None = None,
    ) -> None:
        """
        Subscribe to RailCom data broadcasts.

        Args:
            callback: Function called with RailComData on each update
            address: If specified, filter for this address only.
                    If None, receive all RailCom broadcasts.

        Note:
            Call enable_railcom_broadcasts() first to receive broadcasts.
        """

        def handle_railcom(packet: Packet) -> None:
            try:
                railcom_data = RailComData.from_bytes(packet.data)
                if address is None or railcom_data.loco_address == address:
                    callback(railcom_data)
            except Exception as e:
                log.error(f"Error handling RailCom packet: {e}")

        if LAN_RAILCOM_DATACHANGED not in self._subscribers:
            self._subscribers[LAN_RAILCOM_DATACHANGED] = []
        self._subscribers[LAN_RAILCOM_DATACHANGED].append(handle_railcom)

    def subscribe_railcom_polled(
        self,
        callback: Callable[[RailComData], None],
        address: int | None = None,
        freq_hz: float = 1.0,
    ) -> asyncio.Task[None]:
        """
        Subscribe to RailCom data via polling.

        Polls the Z21 at the specified frequency for RailCom data.
        Useful when broadcast flags cannot be changed or for specific addresses.

        Args:
            callback: Function called with RailComData on each poll
            address: Specific address to poll, or None for circular polling
            freq_hz: Polling frequency in Hz (default 1.0)

        Returns:
            Background task handle (can be cancelled)
        """

        async def poll_loop() -> None:
            interval = 1.0 / freq_hz if freq_hz > 0 else 1.0
            while self._running:
                try:
                    data = await self.get_railcom_data(address)
                    callback(data)
                    await asyncio.sleep(interval)
                except asyncio.CancelledError:
                    break
                except asyncio.TimeoutError:
                    # No response - may be no RailCom-capable decoder
                    await asyncio.sleep(interval)
                except Exception as e:
                    log.error(f"RailCom poll error: {e}")
                    await asyncio.sleep(interval)

        return asyncio.create_task(poll_loop())

    def subscribe_loco_state(
        self,
        callback: Callable[[LocoState], None],
    ) -> None:
        """
        Subscribe to locomotive state updates from all locomotives.

        The callback will be called whenever the station broadcasts
        a state update for any locomotive. The LocoState object
        includes the locomotive address, speed, functions, and other state.

        Args:
            callback: Function called with LocoState for each update.
                     Receives updates for ALL locomotives.

        Example:
            def on_any_loco_state(state: LocoState):
                print(f"Loco {state.address}: speed={state.speed_percentage}%")

            station.subscribe_loco_state(on_any_loco_state)
        """
        from .messages import XBUS_LOCO_INFO

        def handle_packet(packet: Packet) -> None:
            try:
                xbus_msg = XBusMessage.from_bytes(packet.data)
                if xbus_msg.x_header == XBUS_LOCO_INFO:
                    state = LocoState.from_bytes(xbus_msg.dbs)
                    callback(state)
            except Exception as e:
                log.error(f"Error in loco state subscription callback: {e}")

        # Register subscriber for XBUS_LOCO_INFO header
        if XBUS_LOCO_INFO not in self._subscribers:
            self._subscribers[XBUS_LOCO_INFO] = []
        self._subscribers[XBUS_LOCO_INFO].append(handle_packet)

    async def close(self) -> None:
        """
        Close the connection and clean up resources.

        Stops keep-alive task, sends logout, and closes transport.
        """
        self._running = False

        # Cancel keep-alive task
        if self._keep_alive_task is not None:
            self._keep_alive_task.cancel()
            try:
                await self._keep_alive_task
            except asyncio.CancelledError as e:
                log.warning(f"Error while canceling keep alive task error={e}")

        try:
            await self.logout()
        except Exception as e:
            log.warning(f"Error while logging out error={e}")

        if self._transport is not None:
            self._transport.close()
            self._transport = None

    async def __aenter__(self) -> Z21Station:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        await self.close()

    def __repr__(self) -> str:
        status = "connected" if self._running else "disconnected"
        return f"Z21Station({self._host}:{self._port}, {status})"
