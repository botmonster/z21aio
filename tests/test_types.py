"""Tests for types.py - Data structures and enums."""

import pytest
from z21aio.types import (
    DccThrottleSteps,
    FunctionAction,
    SystemState,
    LocoState,
    RailComData,
    RailComOptions,
)


class TestDccThrottleSteps:
    """Tests for DccThrottleSteps enum."""

    def test_enum_values(self):
        """Test enum integer values."""
        assert DccThrottleSteps.STEPS_14 == 0
        assert DccThrottleSteps.STEPS_28 == 2
        assert DccThrottleSteps.STEPS_128 == 4

    def test_from_byte_steps_14(self):
        """Test parsing 14-step mode from byte."""
        assert DccThrottleSteps.from_byte(0x00) == DccThrottleSteps.STEPS_14
        assert DccThrottleSteps.from_byte(0x08) == DccThrottleSteps.STEPS_14  # With busy flag

    def test_from_byte_steps_28(self):
        """Test parsing 28-step mode from byte."""
        assert DccThrottleSteps.from_byte(0x02) == DccThrottleSteps.STEPS_28
        assert DccThrottleSteps.from_byte(0x0A) == DccThrottleSteps.STEPS_28

    def test_from_byte_steps_128(self):
        """Test parsing 128-step mode from byte."""
        assert DccThrottleSteps.from_byte(0x04) == DccThrottleSteps.STEPS_128
        assert DccThrottleSteps.from_byte(0x0C) == DccThrottleSteps.STEPS_128

    def test_from_byte_invalid(self):
        """Test that invalid value raises ValueError."""
        with pytest.raises(ValueError, match="Invalid"):
            DccThrottleSteps.from_byte(0x01)

    def test_to_speed_byte(self):
        """Test speed byte prefix conversion."""
        assert DccThrottleSteps.STEPS_14.to_speed_byte() == 0x10
        assert DccThrottleSteps.STEPS_28.to_speed_byte() == 0x12
        assert DccThrottleSteps.STEPS_128.to_speed_byte() == 0x13

    def test_max_speed(self):
        """Test max speed values."""
        assert DccThrottleSteps.STEPS_14.max_speed == 14
        assert DccThrottleSteps.STEPS_28.max_speed == 28
        assert DccThrottleSteps.STEPS_128.max_speed == 128


class TestFunctionAction:
    """Tests for FunctionAction enum."""

    def test_enum_values(self):
        """Test enum integer values."""
        assert FunctionAction.OFF == 0
        assert FunctionAction.ON == 1
        assert FunctionAction.TOGGLE == 2


class TestSystemState:
    """Tests for SystemState dataclass."""

    def test_from_bytes_valid(self):
        """Test parsing from valid 16-byte data."""
        # Create test data with known values
        data = bytes([
            0xE8, 0x03,  # main_current = 1000 mA
            0x64, 0x00,  # prog_current = 100 mA
            0xD0, 0x07,  # filtered_main_current = 2000 mA
            0x19, 0x00,  # temperature = 25 C
            0x60, 0x54,  # supply_voltage = 21600 mV
            0xD0, 0x36,  # vcc_voltage = 14032 mV
            0x00,        # central_state
            0x00,        # central_state_ex
            0x00,        # reserved
            0x01,        # capabilities
        ])

        state = SystemState.from_bytes(data)

        assert state.main_current == 1000
        assert state.prog_current == 100
        assert state.filtered_main_current == 2000
        assert state.temperature == 25
        assert state.supply_voltage == 21600
        assert state.vcc_voltage == 14032
        assert state.central_state == 0
        assert state.central_state_ex == 0
        assert state.reserved == 0
        assert state.capabilities == 1

    def test_from_bytes_negative_values(self):
        """Test parsing signed values (current can be negative)."""
        data = bytes([
            0x18, 0xFC,  # main_current = -1000 (signed)
            0x00, 0x00,
            0x00, 0x00,
            0x00, 0x00,
            0x00, 0x00,
            0x00, 0x00,
            0x00, 0x00, 0x00, 0x00,
        ])

        state = SystemState.from_bytes(data)
        assert state.main_current == -1000

    def test_from_bytes_wrong_length(self):
        """Test that wrong length raises ValueError."""
        with pytest.raises(ValueError, match="16 bytes"):
            SystemState.from_bytes(b"\x00" * 15)

        with pytest.raises(ValueError, match="16 bytes"):
            SystemState.from_bytes(b"\x00" * 17)

    def test_is_track_voltage_off(self):
        """Test track voltage off flag."""
        data = bytes([0] * 12 + [0x02, 0, 0, 0])  # central_state bit 1 set
        state = SystemState.from_bytes(data)
        assert state.is_track_voltage_off is True

        data = bytes([0] * 12 + [0x00, 0, 0, 0])
        state = SystemState.from_bytes(data)
        assert state.is_track_voltage_off is False

    def test_is_short_circuit(self):
        """Test short circuit flag."""
        data = bytes([0] * 12 + [0x04, 0, 0, 0])  # central_state bit 2 set
        state = SystemState.from_bytes(data)
        assert state.is_short_circuit is True

    def test_is_programming_mode(self):
        """Test programming mode flag."""
        data = bytes([0] * 12 + [0x20, 0, 0, 0])  # central_state bit 5 set
        state = SystemState.from_bytes(data)
        assert state.is_programming_mode is True


class TestLocoState:
    """Tests for LocoState dataclass."""

    def test_from_bytes_minimal(self):
        """Test parsing minimal 2-byte data (address only)."""
        data = bytes([0x00, 0x03])  # Address 3

        state = LocoState.from_bytes(data)

        assert state.address == 3
        assert state.is_busy is None
        assert state.stepping is None

    def test_from_bytes_with_stepping(self):
        """Test parsing with stepping info."""
        data = bytes([0x00, 0x03, 0x04])  # Address 3, 128 steps

        state = LocoState.from_bytes(data)

        assert state.address == 3
        assert state.is_busy is False
        assert state.stepping == DccThrottleSteps.STEPS_128

    def test_from_bytes_busy_flag(self):
        """Test parsing with busy flag set."""
        data = bytes([0x00, 0x03, 0x0C])  # Address 3, 128 steps, busy

        state = LocoState.from_bytes(data)

        assert state.is_busy is True

    def test_from_bytes_with_speed(self):
        """Test parsing with speed info."""
        data = bytes([0x00, 0x03, 0x04, 0xC0])  # Address 3, 128 steps, speed 64 forward

        state = LocoState.from_bytes(data)

        assert state.speed_percentage is not None
        assert state.speed_percentage > 0  # Forward

    def test_from_bytes_reverse_speed(self):
        """Test parsing with reverse speed."""
        data = bytes([0x00, 0x03, 0x04, 0x40])  # Address 3, 128 steps, speed 64 reverse

        state = LocoState.from_bytes(data)

        assert state.speed_percentage is not None
        assert state.speed_percentage < 0  # Reverse

    def test_from_bytes_with_functions_f0_f4(self):
        """Test parsing with F0-F4 functions."""
        # F0 is bit 4, F1-F4 are bits 0-3
        # 0x1A = 0b00011010 = F0 (bit4), F2 (bit1), F4 (bit3)
        data = bytes([0x00, 0x03, 0x04, 0x80, 0x1A])  # F0=1, F2=1, F4=1

        state = LocoState.from_bytes(data)

        assert state.functions is not None
        assert state.functions[0] is True   # F0 (bit 4)
        assert state.functions[1] is False  # F1 (bit 0)
        assert state.functions[2] is True   # F2 (bit 1)
        assert state.functions[3] is False  # F3 (bit 2)
        assert state.functions[4] is True   # F4 (bit 3)

    def test_from_bytes_with_functions_f5_f12(self):
        """Test parsing with F5-F12 functions."""
        data = bytes([0x00, 0x03, 0x04, 0x80, 0x00, 0xAA])  # F5,F7,F9,F11 on

        state = LocoState.from_bytes(data)

        assert state.functions is not None
        assert state.functions[5] is False
        assert state.functions[6] is True   # 0xAA = 10101010
        assert state.functions[7] is False
        assert state.functions[8] is True

    def test_from_bytes_full(self):
        """Test parsing full 9-byte response."""
        data = bytes([
            0x00, 0x03,  # Address 3
            0x04,        # 128 steps, not busy
            0xC0,        # Speed 64 forward
            0x10,        # F0 on
            0x00,        # F5-F12 off
            0x00,        # F13-F20 off
            0x00,        # F21-F28 off
            0x00,        # F29-F31 off
        ])

        state = LocoState.from_bytes(data)

        assert state.address == 3
        assert state.stepping == DccThrottleSteps.STEPS_128
        assert state.is_busy is False
        assert state.functions is not None
        assert len(state.functions) == 32
        assert state.functions[0] is True  # F0 (headlights)

    def test_from_bytes_long_address(self):
        """Test parsing long address (>127)."""
        # Address 1234 = 0x04D2, but in response format upper 2 bits are masked
        # So we receive 0x04 0xD2 and extract 0x04D2 = 1234
        data = bytes([0x04, 0xD2])

        state = LocoState.from_bytes(data)

        assert state.address == 1234

    def test_from_bytes_address_mask(self):
        """Test that upper 2 bits of first byte are ignored."""
        # Address 3 with upper bits set
        data = bytes([0xC0, 0x03])

        state = LocoState.from_bytes(data)

        assert state.address == 3

    def test_from_bytes_too_short(self):
        """Test that too-short data raises ValueError."""
        with pytest.raises(ValueError, match="at least 2 bytes"):
            LocoState.from_bytes(b"\x00")

    def test_double_traction_flag(self):
        """Test double traction flag parsing."""
        data = bytes([0x00, 0x03, 0x04, 0x80, 0x40])  # Bit 6 set

        state = LocoState.from_bytes(data)

        assert state.double_traction is True

    def test_smart_search_flag(self):
        """Test smart search flag parsing."""
        data = bytes([0x00, 0x03, 0x04, 0x80, 0x20])  # Bit 5 set

        state = LocoState.from_bytes(data)

        assert state.smart_search is True


class TestRailComOptions:
    """Tests for RailComOptions flags."""

    def test_flag_values(self):
        """Test flag integer values."""
        assert RailComOptions.NONE == 0x00
        assert RailComOptions.SPEED1 == 0x01
        assert RailComOptions.SPEED2 == 0x02
        assert RailComOptions.QOS == 0x04

    def test_flag_combination(self):
        """Test combining flags."""
        combined = RailComOptions.SPEED1 | RailComOptions.QOS
        assert combined == 0x05
        assert RailComOptions.SPEED1 in combined
        assert RailComOptions.QOS in combined
        assert RailComOptions.SPEED2 not in combined


class TestRailComData:
    """Tests for RailComData dataclass."""

    def test_from_bytes_valid(self):
        """Test parsing from valid 13-byte data."""
        # Create test data with known values:
        # Address=1234 (0x04D2), ReceiveCounter=1000, ErrorCounter=5
        # Options=0x05 (SPEED1|QOS), Speed=64, QoS=200
        data = bytes([
            0xD2, 0x04,              # LocoAddress = 1234 (LE)
            0xE8, 0x03, 0x00, 0x00,  # ReceiveCounter = 1000 (LE)
            0x05, 0x00,              # ErrorCounter = 5 (LE)
            0x00,                    # reserved
            0x05,                    # Options = SPEED1 | QOS
            0x40,                    # Speed = 64
            0xC8,                    # QoS = 200
            0x00,                    # reserved
        ])

        railcom = RailComData.from_bytes(data)

        assert railcom.loco_address == 1234
        assert railcom.receive_counter == 1000
        assert railcom.error_counter == 5
        assert railcom.options == RailComOptions.SPEED1 | RailComOptions.QOS
        assert railcom.speed == 64
        assert railcom.qos == 200

    def test_from_bytes_wrong_length_short(self):
        """Test that too-short data raises ValueError."""
        with pytest.raises(ValueError, match="13 bytes"):
            RailComData.from_bytes(b"\x00" * 12)

    def test_from_bytes_wrong_length_long(self):
        """Test that too-long data raises ValueError."""
        with pytest.raises(ValueError, match="13 bytes"):
            RailComData.from_bytes(b"\x00" * 14)

    def test_has_speed1(self):
        """Test Speed1 flag detection."""
        data = bytes([0] * 9 + [0x01, 0, 0, 0])  # Options bit 0 set
        railcom = RailComData.from_bytes(data)
        assert railcom.has_speed1 is True
        assert railcom.has_speed2 is False
        assert railcom.has_qos is False

    def test_has_speed2(self):
        """Test Speed2 flag detection."""
        data = bytes([0] * 9 + [0x02, 0, 0, 0])  # Options bit 1 set
        railcom = RailComData.from_bytes(data)
        assert railcom.has_speed1 is False
        assert railcom.has_speed2 is True
        assert railcom.has_qos is False

    def test_has_qos(self):
        """Test QoS flag detection."""
        data = bytes([0] * 9 + [0x04, 0, 0, 0])  # Options bit 2 set
        railcom = RailComData.from_bytes(data)
        assert railcom.has_speed1 is False
        assert railcom.has_speed2 is False
        assert railcom.has_qos is True

    def test_error_rate_calculation(self):
        """Test error rate percentage calculation."""
        data = bytes([
            0x00, 0x00,              # Address
            0x5A, 0x00, 0x00, 0x00,  # ReceiveCounter = 90
            0x0A, 0x00,              # ErrorCounter = 10
            0x00, 0x00, 0x00, 0x00, 0x00,
        ])
        railcom = RailComData.from_bytes(data)

        assert railcom.error_rate == 10.0  # 10 / (90 + 10) * 100

    def test_error_rate_zero_messages(self):
        """Test error rate with no messages received."""
        data = bytes([0] * 13)
        railcom = RailComData.from_bytes(data)

        assert railcom.error_rate == 0.0

    def test_large_counters(self):
        """Test parsing large counter values."""
        data = bytes([
            0x00, 0x00,              # Address
            0xFF, 0xFF, 0xFF, 0xFF,  # ReceiveCounter = 4294967295 (max u32)
            0xFF, 0xFF,              # ErrorCounter = 65535 (max u16)
            0x00, 0x00, 0x00, 0x00, 0x00,
        ])
        railcom = RailComData.from_bytes(data)

        assert railcom.receive_counter == 4294967295
        assert railcom.error_counter == 65535

    def test_all_options_set(self):
        """Test all options flags set."""
        data = bytes([0] * 9 + [0x07, 0, 0, 0])  # All flags set
        railcom = RailComData.from_bytes(data)

        assert railcom.has_speed1 is True
        assert railcom.has_speed2 is True
        assert railcom.has_qos is True
