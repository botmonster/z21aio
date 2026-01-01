"""Tests for station.py - Z21 Station controller."""

import asyncio
import struct
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from z21aio.station import Z21Station, Z21Protocol
from z21aio.packet import Packet
from z21aio.messages import (
    LAN_GET_SERIAL_NUMBER,
    LAN_XBUS_HEADER,
    LAN_RAILCOM_DATACHANGED,
    LAN_RAILCOM_GETDATA,
    BROADCAST_RAILCOM_SUBSCRIBED,
    BROADCAST_RAILCOM_ALL,
    XBUS_GET_VERSION_REPLY,
    XBUS_GET_FIRMWARE_VERSION_REPLY,
    XBusMessage,
)
from z21aio.types import RailComData


class TestZ21Protocol:
    """Tests for Z21Protocol class."""

    def test_datagram_received_valid(self):
        """Test receiving a valid datagram."""
        station = MagicMock()
        station._handle_packet = MagicMock()
        protocol = Z21Protocol(station)

        # Valid packet: length=4, header=0x10
        data = b"\x04\x00\x10\x00"
        protocol.datagram_received(data, ("192.168.0.111", 21105))

        station._handle_packet.assert_called_once()
        packet = station._handle_packet.call_args[0][0]
        assert packet.header == 0x10

    def test_datagram_received_invalid(self):
        """Test receiving invalid data doesn't crash."""
        station = MagicMock()
        station._handle_packet = MagicMock(side_effect=Exception("Parse error"))
        protocol = Z21Protocol(station)

        # Should not raise
        protocol.datagram_received(b"\x00", ("192.168.0.111", 21105))

    def test_connection_lost(self):
        """Test connection lost flag."""
        station = MagicMock()
        station._connection_lost = False
        protocol = Z21Protocol(station)

        protocol.connection_lost(None)

        assert station._connection_lost is True


class TestZ21Station:
    """Tests for Z21Station class."""

    @pytest.fixture
    def station(self):
        """Create a Z21Station instance without connecting."""
        s = Z21Station()
        s._transport = MagicMock()
        s._running = True
        return s

    def test_init(self):
        """Test station initialization."""
        station = Z21Station()

        assert station._transport is None
        assert station._running is False
        assert station._timeout == 2.0

    def test_handle_packet_routes_to_waiter(self, station):
        """Test that packets are routed to waiters."""
        queue = asyncio.Queue()
        station._packet_waiters[0x10] = queue

        packet = Packet(header=0x10, data=b"\x01\x02\x03\x04")
        station._handle_packet(packet)

        assert not queue.empty()
        received = queue.get_nowait()
        assert received.header == 0x10

    def test_handle_packet_routes_to_subscribers(self, station):
        """Test that packets are routed to subscribers."""
        callback = MagicMock()
        station._subscribers[0x10] = [callback]

        packet = Packet(header=0x10, data=b"\x01\x02\x03\x04")
        station._handle_packet(packet)

        callback.assert_called_once_with(packet)

    def test_handle_packet_multiple_subscribers(self, station):
        """Test routing to multiple subscribers."""
        callback1 = MagicMock()
        callback2 = MagicMock()
        station._subscribers[0x10] = [callback1, callback2]

        packet = Packet(header=0x10, data=b"\x01")
        station._handle_packet(packet)

        callback1.assert_called_once()
        callback2.assert_called_once()

    def test_handle_packet_lan_xbus_header_routing(self, station):
        """Test that LAN_XBUS_HEADER packets route using X-BUS header from data."""
        # X-BUS header 0x61 (XBUS_BC_TRACK_POWER) is a single byte
        xbus_header = 0x61
        callback = MagicMock()
        queue = asyncio.Queue()

        # Register callback and waiter for the X-BUS header, NOT LAN_XBUS_HEADER
        station._subscribers[xbus_header] = [callback]
        station._packet_waiters[xbus_header] = queue

        # Create packet with LAN_XBUS_HEADER but X-BUS header in data
        # XBusMessage format: [x_header][data_bytes...][xor_checksum]
        # x_header=0x61, dbs=b"\x01", xor=0x61^0x01=0x60
        packet = Packet(
            header=LAN_XBUS_HEADER, data=b"\x61\x01\x60"
        )
        station._handle_packet(packet)

        # Should route to xbus_header (0x61), not LAN_XBUS_HEADER
        callback.assert_called_once_with(packet)
        assert not queue.empty()
        received = queue.get_nowait()
        assert received.header == LAN_XBUS_HEADER  # Original header unchanged
        assert received.data[0] == xbus_header

    @pytest.mark.asyncio
    async def test_send_packet(self, station):
        """Test sending a packet."""
        packet = Packet(header=0x10, data=b"")
        await station.send_packet(packet)

        station._transport.sendto.assert_called_once()
        sent_data = station._transport.sendto.call_args[0][0]
        assert sent_data == b"\x04\x00\x10\x00"

    @pytest.mark.asyncio
    async def test_send_packet_not_connected(self):
        """Test sending when not connected raises error."""
        station = Z21Station()

        with pytest.raises(ConnectionError):
            await station.send_packet(Packet(header=0x10))

    @pytest.mark.asyncio
    async def test_receive_packet_timeout(self, station):
        """Test that receive times out properly."""
        with pytest.raises(asyncio.TimeoutError):
            await station.receive_packet(0x99, timeout=0.01)

    @pytest.mark.asyncio
    async def test_receive_packet_success(self, station):
        """Test successful packet reception."""
        # Pre-populate queue
        queue = asyncio.Queue()
        packet = Packet(header=0x10, data=b"\x01\x02\x03\x04")
        await queue.put(packet)
        station._packet_waiters[0x10] = queue

        received = await station.receive_packet(0x10, timeout=1.0)

        assert received.header == 0x10
        assert received.data == b"\x01\x02\x03\x04"

    @pytest.mark.asyncio
    async def test_get_serial_number(self, station):
        """Test get_serial_number command."""
        # Prepare response
        queue = asyncio.Queue()
        serial_bytes = struct.pack("<I", 12345678)
        response = Packet(header=LAN_GET_SERIAL_NUMBER, data=serial_bytes)
        await queue.put(response)
        station._packet_waiters[LAN_GET_SERIAL_NUMBER] = queue

        serial = await station.get_serial_number()

        assert serial == 12345678
        station._transport.sendto.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_firmware_version(self, station):
        """Test get_firmware_version command."""
        # Prepare response: X-Header=0xF3, DB0=0x0A, DB1=0x01, DB2=0x30
        # XOR = 0xF3 ^ 0x0A ^ 0x01 ^ 0x30 = 0xC8
        queue = asyncio.Queue()
        response = Packet(
            header=LAN_XBUS_HEADER,
            data=b"\xf3\x0a\x01\x30\xc8"
        )
        await queue.put(response)
        station._packet_waiters[XBUS_GET_FIRMWARE_VERSION_REPLY] = queue

        major, minor = await station.get_firmware_version()

        assert major == 0x01
        assert minor == 0x30
        station._transport.sendto.assert_called_once()
        # Verify request contains X-Header 0xF1 and DB0 0x0A
        sent_data = station._transport.sendto.call_args[0][0]
        assert b"\xf1\x0a" in sent_data

    @pytest.mark.asyncio
    async def test_get_version(self, station):
        """Test get_version command."""
        # Prepare response: X-Header=0x63, DB0=0x21, DB1=0x36 (v3.6), DB2=0x12 (CS ID)
        # XOR = 0x63 ^ 0x21 ^ 0x36 ^ 0x12 = 0x66
        queue = asyncio.Queue()
        response = Packet(
            header=LAN_XBUS_HEADER,
            data=b"\x63\x21\x36\x12\x66"
        )
        await queue.put(response)
        station._packet_waiters[XBUS_GET_VERSION_REPLY] = queue

        xbus_version, cs_id = await station.get_version()

        assert xbus_version == 0x36
        assert cs_id == 0x12
        station._transport.sendto.assert_called_once()
        # Verify request contains X-Header 0x21 and DB0 0x21
        sent_data = station._transport.sendto.call_args[0][0]
        assert b"\x21\x21" in sent_data

    @pytest.mark.asyncio
    async def test_voltage_on(self, station):
        """Test voltage_on command."""
        # Prepare response
        queue = asyncio.Queue()
        response = Packet(header=LAN_XBUS_HEADER, data=b"\x61\x01\x60")
        await queue.put(response)
        station._packet_waiters[LAN_XBUS_HEADER] = queue

        await station.voltage_on()

        # Verify packet sent
        sent_data = station._transport.sendto.call_args[0][0]
        # Should contain XBus power on command
        assert b"\x21\x81" in sent_data

    @pytest.mark.asyncio
    async def test_voltage_off(self, station):
        """Test voltage_off command."""
        # Prepare response
        queue = asyncio.Queue()
        response = Packet(header=LAN_XBUS_HEADER, data=b"\x61\x00\x61")
        await queue.put(response)
        station._packet_waiters[LAN_XBUS_HEADER] = queue

        await station.voltage_off()

        sent_data = station._transport.sendto.call_args[0][0]
        assert b"\x21\x80" in sent_data

    @pytest.mark.asyncio
    async def test_logout(self, station):
        """Test logout command."""
        await station.logout()

        sent_data = station._transport.sendto.call_args[0][0]
        # Logout packet: length=4, header=0x30
        assert sent_data == b"\x04\x00\x30\x00"

    @pytest.mark.asyncio
    async def test_close(self, station):
        """Test closing the connection."""
        station._keep_alive_task = asyncio.create_task(asyncio.sleep(100))

        await station.close()

        assert station._running is False
        assert station._transport is None
        assert station._keep_alive_task.cancelled()

    @pytest.mark.asyncio
    async def test_context_manager(self, station):
        """Test async context manager."""
        station._keep_alive_task = asyncio.create_task(asyncio.sleep(100))

        async with station:
            assert station._running is True

        assert station._running is False

    def test_repr_disconnected(self):
        """Test repr when disconnected."""
        station = Z21Station()
        repr_str = repr(station)

        assert "disconnected" in repr_str

    def test_repr_connected(self, station):
        """Test repr when connected."""
        station._host = "192.168.0.111"
        station._port = 21105
        repr_str = repr(station)

        assert "connected" in repr_str
        assert "192.168.0.111" in repr_str


class TestZ21StationConnect:
    """Integration tests for Z21Station.connect()."""

    @pytest.mark.asyncio
    async def test_connect_creates_endpoint(self):
        """Test that connect creates UDP endpoint."""
        with patch("asyncio.get_running_loop") as mock_loop:
            mock_transport = MagicMock()
            mock_protocol = MagicMock()
            mock_loop.return_value.create_datagram_endpoint = AsyncMock(
                return_value=(mock_transport, mock_protocol)
            )

            station = await Z21Station.connect("192.168.0.111")

            mock_loop.return_value.create_datagram_endpoint.assert_called_once()
            assert station._transport is mock_transport
            assert station._running is True

            # Cleanup
            station._running = False
            if station._keep_alive_task:
                station._keep_alive_task.cancel()
                try:
                    await station._keep_alive_task
                except asyncio.CancelledError:
                    pass


class TestZ21StationRailCom:
    """Tests for Z21Station RailCom functionality."""

    @pytest.fixture
    def station(self):
        """Create a Z21Station instance without connecting."""
        s = Z21Station()
        s._transport = MagicMock()
        s._running = True
        return s

    @pytest.mark.asyncio
    async def test_enable_railcom_broadcasts_subscribed(self, station):
        """Test enabling RailCom broadcasts for subscribed locos."""
        await station.enable_railcom_broadcasts(all_locos=False)

        assert station._broadcast_flags & BROADCAST_RAILCOM_SUBSCRIBED
        station._transport.sendto.assert_called()

    @pytest.mark.asyncio
    async def test_enable_railcom_broadcasts_all(self, station):
        """Test enabling RailCom broadcasts for all locos."""
        await station.enable_railcom_broadcasts(all_locos=True)

        assert station._broadcast_flags & BROADCAST_RAILCOM_ALL
        station._transport.sendto.assert_called()

    @pytest.mark.asyncio
    async def test_disable_railcom_broadcasts(self, station):
        """Test disabling RailCom broadcasts."""
        station._broadcast_flags = BROADCAST_RAILCOM_SUBSCRIBED | BROADCAST_RAILCOM_ALL

        await station.disable_railcom_broadcasts()

        assert not (station._broadcast_flags & BROADCAST_RAILCOM_SUBSCRIBED)
        assert not (station._broadcast_flags & BROADCAST_RAILCOM_ALL)

    @pytest.mark.asyncio
    async def test_get_railcom_data_specific_address(self, station):
        """Test polling RailCom data for specific address."""
        queue = asyncio.Queue()
        railcom_bytes = bytes([
            0x03, 0x00,              # Address = 3
            0x64, 0x00, 0x00, 0x00,  # ReceiveCounter = 100
            0x02, 0x00,              # ErrorCounter = 2
            0x00, 0x05, 0x40, 0xC8, 0x00,
        ])
        response = Packet(header=LAN_RAILCOM_GETDATA, data=railcom_bytes)
        await queue.put(response)
        station._packet_waiters[LAN_RAILCOM_GETDATA] = queue

        data = await station.get_railcom_data(address=3)

        assert data.loco_address == 3
        assert data.receive_counter == 100

        # Verify request format
        sent_data = station._transport.sendto.call_args[0][0]
        # Should contain Type=0x01 and Address=0x0003
        assert b"\x01\x03\x00" in sent_data

    @pytest.mark.asyncio
    async def test_get_railcom_data_circular_poll(self, station):
        """Test circular RailCom polling."""
        queue = asyncio.Queue()
        railcom_bytes = bytes([0] * 13)
        response = Packet(header=LAN_RAILCOM_GETDATA, data=railcom_bytes)
        await queue.put(response)
        station._packet_waiters[LAN_RAILCOM_GETDATA] = queue

        await station.get_railcom_data(address=None)

        # Verify request format
        sent_data = station._transport.sendto.call_args[0][0]
        # Should contain Type=0x00 and Address=0x0000
        assert b"\x00\x00\x00" in sent_data

    def test_subscribe_railcom_routes_to_callback(self, station):
        """Test RailCom subscription routing."""
        callback = MagicMock()
        station.subscribe_railcom(callback)

        railcom_bytes = bytes([
            0x03, 0x00,              # Address = 3
            0x00, 0x00, 0x00, 0x00,  # ReceiveCounter
            0x00, 0x00,              # ErrorCounter
            0x00, 0x00, 0x00, 0x00, 0x00,
        ])
        packet = Packet(header=LAN_RAILCOM_DATACHANGED, data=railcom_bytes)
        station._handle_packet(packet)

        callback.assert_called_once()
        railcom_data = callback.call_args[0][0]
        assert isinstance(railcom_data, RailComData)
        assert railcom_data.loco_address == 3

    def test_subscribe_railcom_filters_by_address(self, station):
        """Test RailCom subscription filtering by address."""
        callback = MagicMock()
        station.subscribe_railcom(callback, address=5)

        # Send packet for address 3 - should not trigger callback
        railcom_bytes = bytes([0x03, 0x00] + [0] * 11)
        packet = Packet(header=LAN_RAILCOM_DATACHANGED, data=railcom_bytes)
        station._handle_packet(packet)

        callback.assert_not_called()

        # Send packet for address 5 - should trigger callback
        railcom_bytes = bytes([0x05, 0x00] + [0] * 11)
        packet = Packet(header=LAN_RAILCOM_DATACHANGED, data=railcom_bytes)
        station._handle_packet(packet)

        callback.assert_called_once()
        assert callback.call_args[0][0].loco_address == 5
