"""Tests for turnout.py - Turnout control and TurnoutState/TurnoutPosition types."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from z21aio.messages import XBUS_TURNOUT_INFO, XBUS_SET_TURNOUT, XBusMessage
from z21aio.packet import Packet
from z21aio.turnout import Turnout
from z21aio.types import TurnoutPosition, TurnoutState


class TestTurnoutPosition:
    """Tests for TurnoutPosition enum."""

    def test_enum_values(self):
        """Test enum integer values match protocol ZZ bits."""
        assert TurnoutPosition.UNKNOWN == 0
        assert TurnoutPosition.P0 == 1
        assert TurnoutPosition.P1 == 2
        assert TurnoutPosition.INVALID == 3


class TestTurnoutState:
    """Tests for TurnoutState dataclass."""

    def test_from_bytes_position_p0(self):
        """Test parsing ZZ=01 as P0."""
        state = TurnoutState.from_bytes(bytes([0x00, 0x00, 0x01]))

        assert state.address == 0
        assert state.position == TurnoutPosition.P0

    def test_from_bytes_position_p1(self):
        """Test parsing ZZ=10 as P1."""
        state = TurnoutState.from_bytes(bytes([0x00, 0x00, 0x02]))

        assert state.address == 0
        assert state.position == TurnoutPosition.P1

    def test_from_bytes_unknown(self):
        """Test parsing ZZ=00 as UNKNOWN."""
        state = TurnoutState.from_bytes(bytes([0x00, 0x00, 0x00]))

        assert state.position == TurnoutPosition.UNKNOWN

    def test_from_bytes_invalid(self):
        """Test parsing ZZ=11 as INVALID."""
        state = TurnoutState.from_bytes(bytes([0x00, 0x00, 0x03]))

        assert state.position == TurnoutPosition.INVALID

    def test_from_bytes_address_encoding(self):
        """Test address is (MSB << 8) | LSB."""
        state = TurnoutState.from_bytes(bytes([0x01, 0xF4, 0x01]))

        assert state.address == 500

    def test_from_bytes_masks_zz_bits(self):
        """Test that only lower 2 bits of status byte are used."""
        state = TurnoutState.from_bytes(bytes([0x00, 0x00, 0xFE]))

        # 0xFE & 0x03 = 0x02 = P1
        assert state.position == TurnoutPosition.P1

    def test_from_bytes_wrong_length(self):
        """Test that wrong length raises ValueError."""
        with pytest.raises(ValueError, match="3 bytes"):
            TurnoutState.from_bytes(bytes([0x00, 0x00]))

        with pytest.raises(ValueError, match="3 bytes"):
            TurnoutState.from_bytes(bytes([0x00, 0x00, 0x00, 0x00]))


class TestTurnout:
    """Tests for Turnout class."""

    @pytest.fixture
    def mock_station(self):
        """Create a mock Z21Station."""
        station = MagicMock()
        station.send_xbus_command = AsyncMock()
        station._subscribers = {}
        return station

    def test_init(self, mock_station):
        """Test Turnout initialization."""
        turnout = Turnout(mock_station, address=5)

        assert turnout.address == 5

    @pytest.mark.asyncio
    async def test_control_returns_turnout(self, mock_station):
        """Test that control() returns a Turnout with the correct address."""
        response_msg = XBusMessage(
            x_header=XBUS_TURNOUT_INFO,
            dbs=bytes([0x00, 0x07, 0x01]),  # Address 7, P0
        )
        mock_station.send_xbus_command.return_value = response_msg

        turnout = await Turnout.control(mock_station, address=7)

        assert isinstance(turnout, Turnout)
        assert turnout.address == 7

    @pytest.mark.asyncio
    async def test_control_requests_initial_state(self, mock_station):
        """Test that control() fetches initial state to register with station."""
        response_msg = XBusMessage(
            x_header=XBUS_TURNOUT_INFO,
            dbs=bytes([0x00, 0x03, 0x02]),  # Address 3, P1
        )
        mock_station.send_xbus_command.return_value = response_msg

        await Turnout.control(mock_station, address=3)

        mock_station.send_xbus_command.assert_called_once()

    @pytest.mark.asyncio
    async def test_control_suppresses_timeout(self, mock_station):
        """Test that control() succeeds even if the initial get_state times out."""
        mock_station.send_xbus_command.side_effect = TimeoutError

        turnout = await Turnout.control(mock_station, address=10)

        assert turnout.address == 10

    def test_repr(self, mock_station):
        """Test string representation."""
        turnout = Turnout(mock_station, address=42)

        assert "42" in repr(turnout)

    @pytest.mark.asyncio
    async def test_switch_p0_queue_mode(self, mock_station):
        """Test switching to P0 in queue mode."""
        turnout = Turnout(mock_station, address=3)
        await turnout.switch(TurnoutPosition.P0)

        mock_station.send_xbus_command.assert_called_once()
        msg = mock_station.send_xbus_command.call_args[0][0]

        assert msg.x_header == XBUS_SET_TURNOUT
        assert msg.dbs[0] == 0x00  # Address MSB
        assert msg.dbs[1] == 0x03  # Address LSB
        # P0 -> output 0, activate, queue: 1_1_0_1_0_0_0 = 0xA8
        assert msg.dbs[2] == 0xA8

    @pytest.mark.asyncio
    async def test_switch_p1_queue_mode(self, mock_station):
        """Test switching to P1 in queue mode."""
        turnout = Turnout(mock_station, address=3)
        await turnout.switch(TurnoutPosition.P1)

        msg = mock_station.send_xbus_command.call_args[0][0]

        # P1 -> output 1, activate, queue: 1_1_0_1_0_0_1 = 0xA9
        assert msg.dbs[2] == 0xA9

    @pytest.mark.asyncio
    async def test_switch_p0_immediate_mode(self, mock_station):
        """Test switching to P0 in immediate mode sends activate then deactivate."""
        turnout = Turnout(mock_station, address=3)

        with patch("z21aio.turnout.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await turnout.switch(
                TurnoutPosition.P0, queue_mode=False, activate_duration=0.15
            )

        # Should have sent two commands: activate then deactivate
        assert mock_station.send_xbus_command.call_count == 2

        activate_msg = mock_station.send_xbus_command.call_args_list[0][0][0]
        deactivate_msg = mock_station.send_xbus_command.call_args_list[1][0][0]

        # Activate: immediate, output 0, A=1: 1_0_0_1_0_0_0 = 0x88
        assert activate_msg.dbs[2] == 0x88
        # Deactivate: immediate, output 0, A=0: 1_0_0_0_0_0_0 = 0x80
        assert deactivate_msg.dbs[2] == 0x80

        # Sleep should have been called with the duration
        mock_sleep.assert_called_once_with(0.15)

    @pytest.mark.asyncio
    async def test_switch_invalid_position_unknown(self, mock_station):
        """Test that UNKNOWN position raises ValueError."""
        turnout = Turnout(mock_station, address=0)

        with pytest.raises(ValueError, match="P0 or P1"):
            await turnout.switch(TurnoutPosition.UNKNOWN)

    @pytest.mark.asyncio
    async def test_switch_invalid_position_invalid(self, mock_station):
        """Test that INVALID position raises ValueError."""
        turnout = Turnout(mock_station, address=0)

        with pytest.raises(ValueError, match="P0 or P1"):
            await turnout.switch(TurnoutPosition.INVALID)

    @pytest.mark.asyncio
    async def test_activate(self, mock_station):
        """Test low-level activate."""
        turnout = Turnout(mock_station, address=5)
        await turnout.activate(0)

        msg = mock_station.send_xbus_command.call_args[0][0]
        assert msg.x_header == XBUS_SET_TURNOUT
        # Activate, output 0, queue: 0xA8
        assert msg.dbs[2] == 0xA8

    @pytest.mark.asyncio
    async def test_deactivate(self, mock_station):
        """Test low-level deactivate."""
        turnout = Turnout(mock_station, address=5)
        await turnout.deactivate(1)

        msg = mock_station.send_xbus_command.call_args[0][0]
        assert msg.x_header == XBUS_SET_TURNOUT
        # Deactivate, output 1, queue: 1_1_0_0_0_0_1 = 0xA1
        assert msg.dbs[2] == 0xA1

    @pytest.mark.asyncio
    async def test_get_state(self, mock_station):
        """Test getting turnout state."""
        # Create a mock response
        response_msg = XBusMessage(
            x_header=XBUS_TURNOUT_INFO,
            dbs=bytes([0x00, 0x05, 0x01]),  # Address 5, P0
        )
        mock_station.send_xbus_command.return_value = response_msg

        turnout = Turnout(mock_station, address=5)
        state = await turnout.get_state()

        assert state.address == 5
        assert state.position == TurnoutPosition.P0

        # Verify the request was sent with correct response header
        call_args = mock_station.send_xbus_command.call_args
        request_msg = call_args[0][0]
        expected_response_header = call_args[0][1]

        assert request_msg.x_header == XBUS_TURNOUT_INFO
        assert request_msg.dbs == bytes([0x00, 0x05])
        assert expected_response_header == XBUS_TURNOUT_INFO

    @pytest.mark.asyncio
    async def test_get_state_no_response(self, mock_station):
        """Test get_state raises RuntimeError when no response."""
        mock_station.send_xbus_command.return_value = None

        turnout = Turnout(mock_station, address=0)

        with pytest.raises(RuntimeError, match="No response"):
            await turnout.get_state()

    def test_subscribe_state(self, mock_station):
        """Test subscribing to turnout state updates."""
        turnout = Turnout(mock_station, address=5)
        callback = MagicMock()
        turnout.subscribe_state(callback)

        # Verify subscriber was registered
        assert XBUS_TURNOUT_INFO in mock_station._subscribers
        assert len(mock_station._subscribers[XBUS_TURNOUT_INFO]) == 1

        # Simulate receiving a TURNOUT_INFO packet for address 5
        info_msg = XBusMessage(
            x_header=XBUS_TURNOUT_INFO,
            dbs=bytes([0x00, 0x05, 0x02]),  # Address 5, P1
        )
        packet = Packet(header=0x40, data=info_msg.to_bytes())
        mock_station._subscribers[XBUS_TURNOUT_INFO][0](packet)

        callback.assert_called_once()
        state = callback.call_args[0][0]
        assert state.address == 5
        assert state.position == TurnoutPosition.P1

    def test_subscribe_state_filters_address(self, mock_station):
        """Test that subscription filters by turnout address."""
        turnout = Turnout(mock_station, address=5)
        callback = MagicMock()
        turnout.subscribe_state(callback)

        # Simulate receiving a TURNOUT_INFO packet for a different address
        info_msg = XBusMessage(
            x_header=XBUS_TURNOUT_INFO,
            dbs=bytes([0x00, 0x0A, 0x01]),  # Address 10, P0
        )
        packet = Packet(header=0x40, data=info_msg.to_bytes())
        mock_station._subscribers[XBUS_TURNOUT_INFO][0](packet)

        callback.assert_not_called()

    def test_subscribe_state_ignores_short_packets(self, mock_station):
        """Test that GET_TURNOUT_INFO packets (2 DB bytes) are ignored."""
        turnout = Turnout(mock_station, address=5)
        callback = MagicMock()
        turnout.subscribe_state(callback)

        # Simulate receiving a GET_TURNOUT_INFO packet (only 2 DB bytes)
        get_msg = XBusMessage(
            x_header=XBUS_TURNOUT_INFO,
            dbs=bytes([0x00, 0x05]),  # Only 2 bytes = GET request
        )
        packet = Packet(header=0x40, data=get_msg.to_bytes())
        mock_station._subscribers[XBUS_TURNOUT_INFO][0](packet)

        callback.assert_not_called()
