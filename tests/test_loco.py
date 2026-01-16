"""Tests for loco.py - Locomotive control."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from z21aio.loco import Loco, _calc_speed_byte
from z21aio.types import DccThrottleSteps, FunctionAction, RailComData


class TestCalcSpeedByte:
    """Tests for _calc_speed_byte function."""

    def test_forward_50_percent_128_steps(self):
        """Test 50% forward speed with 128 steps."""
        result = _calc_speed_byte(DccThrottleSteps.STEPS_128, 50.0)

        # 50% of 128 = 64, with forward bit = 0x80 | 64 = 0xC0
        assert result == 0xC0

    def test_forward_100_percent_128_steps(self):
        """Test 100% forward speed with 128 steps."""
        result = _calc_speed_byte(DccThrottleSteps.STEPS_128, 100.0)

        # 100% of 128 = 127 (clamped), with forward bit
        assert result == 0xFF

    def test_reverse_50_percent_128_steps(self):
        """Test 50% reverse speed with 128 steps."""
        result = _calc_speed_byte(DccThrottleSteps.STEPS_128, 50.0, reverse=True)

        # 50% of 128 = 64, without forward bit
        assert result == 64

    def test_zero_speed(self):
        """Test zero speed."""
        result = _calc_speed_byte(DccThrottleSteps.STEPS_128, 0.0)

        # 0% = 0, with forward bit (zero is technically forward)
        assert result == 0x80

    def test_forward_28_steps(self):
        """Test forward speed with 28 steps."""
        result = _calc_speed_byte(DccThrottleSteps.STEPS_28, 50.0)

        # 50% of 28 = 14, with forward bit
        assert result == 0x80 | 14

    def test_forward_14_steps(self):
        """Test forward speed with 14 steps."""
        result = _calc_speed_byte(DccThrottleSteps.STEPS_14, 50.0)

        # 50% of 14 = 7, with forward bit
        assert result == 0x80 | 7

    def test_speed_clamping_high(self):
        """Test that speed over 100% is clamped."""
        result = _calc_speed_byte(DccThrottleSteps.STEPS_128, 150.0)

        # Should be clamped to 100%
        assert result == 0xFF

    def test_speed_clamping_low(self):
        """Test that negative speed is clamped to 0."""
        result = _calc_speed_byte(DccThrottleSteps.STEPS_128, -50.0)

        # Negative speed should be clamped to 0, with forward bit
        assert result == 0x80

    def test_small_forward_speed(self):
        """Test small forward speed."""
        result = _calc_speed_byte(DccThrottleSteps.STEPS_128, 1.0)

        # 1% of 128 = 1, with forward bit
        assert result == 0x80 | 1

    def test_small_reverse_speed(self):
        """Test small reverse speed."""
        result = _calc_speed_byte(DccThrottleSteps.STEPS_128, 1.0, reverse=True)

        # 1% of 128 = 1, without forward bit
        assert result == 1

    def test_zero_speed_forward(self):
        """Test zero speed with forward direction."""
        result = _calc_speed_byte(DccThrottleSteps.STEPS_128, 0.0, reverse=False)

        # 0% with forward bit
        assert result == 0x80

    def test_zero_speed_reverse(self):
        """Test zero speed with reverse direction."""
        result = _calc_speed_byte(DccThrottleSteps.STEPS_128, 0.0, reverse=True)

        # 0% without forward bit
        assert result == 0x00

    def test_full_speed_reverse(self):
        """Test 100% reverse speed."""
        result = _calc_speed_byte(DccThrottleSteps.STEPS_128, 100.0, reverse=True)

        # 100% of 128 = 127, without forward bit
        assert result == 127

    def test_direction_28_steps_reverse(self):
        """Test reverse direction with 28 steps."""
        result = _calc_speed_byte(DccThrottleSteps.STEPS_28, 50.0, reverse=True)

        # 50% of 28 = 14, without forward bit
        assert result == 14


class TestLoco:
    """Tests for Loco class."""

    @pytest.fixture
    def mock_station(self):
        """Create a mock Z21Station."""
        station = MagicMock()
        station.send_xbus_command = AsyncMock()
        station._subscribers = {}
        return station

    def test_loco_init(self, mock_station):
        """Test Loco initialization."""
        loco = Loco(mock_station, address=3)

        assert loco.address == 3
        assert loco.steps == DccThrottleSteps.STEPS_128

    def test_loco_init_custom_steps(self, mock_station):
        """Test Loco initialization with custom throttle steps."""
        loco = Loco(mock_station, address=5, steps=DccThrottleSteps.STEPS_28)

        assert loco.address == 5
        assert loco.steps == DccThrottleSteps.STEPS_28

    @pytest.mark.asyncio
    async def test_drive_forward(self, mock_station):
        """Test driving forward."""
        loco = Loco(mock_station, address=3)
        await loco.drive(50.0)

        mock_station.send_xbus_command.assert_called_once()
        call_args = mock_station.send_xbus_command.call_args
        msg = call_args[0][0]

        assert msg.x_header == 0xE4
        assert msg.dbs[0] == 0x13  # 128 steps
        assert msg.dbs[3] == 0xC0  # 50% forward

    @pytest.mark.asyncio
    async def test_drive_reverse(self, mock_station):
        """Test driving in reverse."""
        loco = Loco(mock_station, address=3)
        await loco.drive(50.0, reverse=True)

        mock_station.send_xbus_command.assert_called_once()
        call_args = mock_station.send_xbus_command.call_args
        msg = call_args[0][0]

        assert msg.dbs[3] == 64  # 50% reverse (no direction bit)

    @pytest.mark.asyncio
    async def test_drive_zero_speed_forward(self, mock_station):
        """Test setting zero speed with forward direction."""
        loco = Loco(mock_station, address=3)
        await loco.drive(0.0, reverse=False)

        mock_station.send_xbus_command.assert_called_once()
        call_args = mock_station.send_xbus_command.call_args
        msg = call_args[0][0]

        assert msg.dbs[3] == 0x80  # Zero speed with forward direction bit

    @pytest.mark.asyncio
    async def test_drive_zero_speed_reverse(self, mock_station):
        """Test setting zero speed with reverse direction."""
        loco = Loco(mock_station, address=3)
        await loco.drive(0.0, reverse=True)

        mock_station.send_xbus_command.assert_called_once()
        call_args = mock_station.send_xbus_command.call_args
        msg = call_args[0][0]

        assert msg.dbs[3] == 0x00  # Zero speed with reverse direction

    @pytest.mark.asyncio
    async def test_stop(self, mock_station):
        """Test normal stop."""
        loco = Loco(mock_station, address=3)
        await loco.stop()

        mock_station.send_xbus_command.assert_called_once()
        call_args = mock_station.send_xbus_command.call_args
        msg = call_args[0][0]

        assert msg.dbs[3] == 0x00  # Stop

    @pytest.mark.asyncio
    async def test_halt(self, mock_station):
        """Test emergency stop."""
        loco = Loco(mock_station, address=3)
        await loco.halt()

        mock_station.send_xbus_command.assert_called_once()
        call_args = mock_station.send_xbus_command.call_args
        msg = call_args[0][0]

        assert msg.dbs[3] == 0x01  # Emergency stop

    @pytest.mark.asyncio
    async def test_function_on(self, mock_station):
        """Test turning function on."""
        loco = Loco(mock_station, address=3)
        await loco.function_on(2)

        mock_station.send_xbus_command.assert_called_once()
        call_args = mock_station.send_xbus_command.call_args
        msg = call_args[0][0]

        assert msg.dbs[0] == 0xF8
        assert msg.dbs[3] == 0x42  # ON (01) + function 2 = 0x40 | 0x02

    @pytest.mark.asyncio
    async def test_function_off(self, mock_station):
        """Test turning function off."""
        loco = Loco(mock_station, address=3)
        await loco.function_off(5)

        mock_station.send_xbus_command.assert_called_once()
        call_args = mock_station.send_xbus_command.call_args
        msg = call_args[0][0]

        assert msg.dbs[3] == 0x05  # OFF (00) + function 5

    @pytest.mark.asyncio
    async def test_function_toggle(self, mock_station):
        """Test toggling function."""
        loco = Loco(mock_station, address=3)
        await loco.function_toggle(10)

        mock_station.send_xbus_command.assert_called_once()
        call_args = mock_station.send_xbus_command.call_args
        msg = call_args[0][0]

        assert msg.dbs[3] == 0x8A  # TOGGLE (10) + function 10

    @pytest.mark.asyncio
    async def test_set_headlights_on(self, mock_station):
        """Test turning headlights on."""
        loco = Loco(mock_station, address=3)
        await loco.set_headlights(True)

        mock_station.send_xbus_command.assert_called_once()
        call_args = mock_station.send_xbus_command.call_args
        msg = call_args[0][0]

        assert msg.dbs[3] == 0x40  # ON + function 0

    @pytest.mark.asyncio
    async def test_set_headlights_off(self, mock_station):
        """Test turning headlights off."""
        loco = Loco(mock_station, address=3)
        await loco.set_headlights(False)

        mock_station.send_xbus_command.assert_called_once()
        call_args = mock_station.send_xbus_command.call_args
        msg = call_args[0][0]

        assert msg.dbs[3] == 0x00  # OFF + function 0

    @pytest.mark.asyncio
    async def test_set_function_invalid_index(self, mock_station):
        """Test that invalid function index raises ValueError."""
        loco = Loco(mock_station, address=3)

        with pytest.raises(ValueError, match="0-31"):
            await loco.set_function(32, FunctionAction.ON)

        with pytest.raises(ValueError, match="0-31"):
            await loco.set_function(-1, FunctionAction.ON)

    def test_repr(self, mock_station):
        """Test string representation."""
        loco = Loco(mock_station, address=42, steps=DccThrottleSteps.STEPS_28)
        repr_str = repr(loco)

        assert "42" in repr_str
        assert "STEPS_28" in repr_str

    @pytest.mark.asyncio
    async def test_long_address_drive(self, mock_station):
        """Test drive command with long address."""
        loco = Loco(mock_station, address=1234)
        await loco.drive(50.0)

        call_args = mock_station.send_xbus_command.call_args
        msg = call_args[0][0]

        # Address 1234 = 0x04D2
        # With 0xC0 flag: MSB = 0xC4, LSB = 0xD2
        assert msg.dbs[1] == 0xC4
        assert msg.dbs[2] == 0xD2


class TestLocoRailCom:
    """Tests for Loco RailCom functionality."""

    @pytest.fixture
    def mock_station(self):
        """Create a mock Z21Station."""
        station = MagicMock()
        station.send_xbus_command = AsyncMock()
        station.get_railcom_data = AsyncMock()
        station.subscribe_railcom = MagicMock()
        station._subscribers = {}
        return station

    def test_railcom_property_initially_none(self, mock_station):
        """Test railcom property is None before subscription."""
        loco = Loco(mock_station, address=3)
        assert loco.railcom is None

    @pytest.mark.asyncio
    async def test_get_railcom_data_delegates_to_station(self, mock_station):
        """Test get_railcom_data delegates to station."""
        expected_data = MagicMock(spec=RailComData)
        mock_station.get_railcom_data.return_value = expected_data

        loco = Loco(mock_station, address=3)
        result = await loco.get_railcom_data()

        mock_station.get_railcom_data.assert_called_once_with(3, None)
        assert result is expected_data

    @pytest.mark.asyncio
    async def test_get_railcom_data_with_timeout(self, mock_station):
        """Test get_railcom_data passes timeout."""
        loco = Loco(mock_station, address=5)
        await loco.get_railcom_data(timeout=5.0)

        mock_station.get_railcom_data.assert_called_once_with(5, 5.0)

    def test_subscribe_railcom_registers_with_station(self, mock_station):
        """Test subscribe_railcom registers callback with station."""
        loco = Loco(mock_station, address=3)
        loco.subscribe_railcom()

        mock_station.subscribe_railcom.assert_called_once()
        # Verify address filter is passed
        call_args = mock_station.subscribe_railcom.call_args
        assert call_args[0][1] == 3  # Second positional arg is address

    def test_subscribe_railcom_updates_property(self, mock_station):
        """Test subscribe_railcom auto-updates railcom property."""
        # Capture the internal callback that Loco registers
        captured_callback = None

        def capture_subscribe(cb, addr):
            nonlocal captured_callback
            captured_callback = cb

        mock_station.subscribe_railcom = capture_subscribe

        loco = Loco(mock_station, address=3)
        loco.subscribe_railcom()

        # Simulate receiving RailCom data
        mock_railcom = MagicMock(spec=RailComData)
        captured_callback(mock_railcom)

        assert loco.railcom is mock_railcom

    def test_subscribe_railcom_calls_user_callback(self, mock_station):
        """Test subscribe_railcom calls user callback."""
        captured_callback = None

        def capture_subscribe(cb, addr):
            nonlocal captured_callback
            captured_callback = cb

        mock_station.subscribe_railcom = capture_subscribe

        loco = Loco(mock_station, address=3)
        user_callback = MagicMock()
        loco.subscribe_railcom(user_callback)

        mock_railcom = MagicMock(spec=RailComData)
        captured_callback(mock_railcom)

        user_callback.assert_called_once_with(mock_railcom)
        assert loco.railcom is mock_railcom
