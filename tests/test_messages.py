"""Tests for messages.py - XBus message handling."""

import pytest
from z21aio.messages import (
    XBusMessage,
    LAN_GET_SERIAL_NUMBER,
    LAN_XBUS_HEADER,
    XBUS_SET_TRACK_POWER,
    XBUS_LOCO_DRIVE,
    XBUS_LOCO_GET_INFO,
    XBUS_GET_VERSION,
    XBUS_GET_FIRMWARE_VERSION,
    XBUS_TURNOUT_INFO,
    XBUS_SET_TURNOUT,
)
from z21aio.types import DccThrottleSteps, FunctionAction


class TestXBusMessage:
    """Tests for XBusMessage class."""

    def test_xor_calculation_simple(self):
        """Test XOR checksum calculation with simple data."""
        msg = XBusMessage(x_header=0x21, dbs=b"\x81")
        # XOR of 0x21 and 0x81 = 0xA0
        assert msg.xor == 0xA0

    def test_xor_calculation_multiple_bytes(self):
        """Test XOR checksum with multiple data bytes."""
        msg = XBusMessage(x_header=0xE3, dbs=b"\xF0\x00\x03")
        # 0xE3 ^ 0xF0 ^ 0x00 ^ 0x03 = 0x10
        assert msg.xor == 0x10

    def test_xor_calculation_empty_data(self):
        """Test XOR checksum with no data bytes."""
        msg = XBusMessage(x_header=0x21, dbs=b"")
        assert msg.xor == 0x21

    def test_to_bytes(self):
        """Test serialization to bytes."""
        msg = XBusMessage(x_header=0x21, dbs=b"\x81")
        result = msg.to_bytes()

        assert result == b"\x21\x81\xa0"

    def test_from_bytes_valid(self):
        """Test parsing from valid bytes."""
        data = b"\x21\x81\xa0"
        msg = XBusMessage.from_bytes(data)

        assert msg.x_header == 0x21
        assert msg.dbs == b"\x81"
        assert msg.xor == 0xA0

    def test_from_bytes_invalid_xor(self):
        """Test that invalid XOR raises ValueError."""
        data = b"\x21\x81\xFF"  # Wrong XOR
        with pytest.raises(ValueError, match="XOR mismatch"):
            XBusMessage.from_bytes(data)

    def test_from_bytes_too_short(self):
        """Test that too-short data raises ValueError."""
        with pytest.raises(ValueError, match="at least 2 bytes"):
            XBusMessage.from_bytes(b"\x21")

    def test_roundtrip(self):
        """Test serialization and deserialization roundtrip."""
        original = XBusMessage(x_header=0xE4, dbs=b"\x13\x00\x03\x64")
        serialized = original.to_bytes()
        restored = XBusMessage.from_bytes(serialized)

        assert restored.x_header == original.x_header
        assert restored.dbs == original.dbs

    def test_track_power_on(self):
        """Test track power on command creation."""
        msg = XBusMessage.track_power_on()

        assert msg.x_header == XBUS_SET_TRACK_POWER
        assert msg.dbs == b"\x81"

    def test_track_power_off(self):
        """Test track power off command creation."""
        msg = XBusMessage.track_power_off()

        assert msg.x_header == XBUS_SET_TRACK_POWER
        assert msg.dbs == b"\x80"

    def test_get_firmware_version(self):
        """Test get firmware version command creation."""
        msg = XBusMessage.get_firmware_version()

        assert msg.x_header == XBUS_GET_FIRMWARE_VERSION
        assert msg.dbs == b"\x0a"
        # XOR = 0xF1 ^ 0x0A = 0xFB
        assert msg.xor == 0xFB

    def test_get_version(self):
        """Test get X-BUS version command creation."""
        msg = XBusMessage.get_version()

        assert msg.x_header == XBUS_GET_VERSION
        assert msg.dbs == b"\x21"
        # XOR = 0x21 ^ 0x21 = 0x00
        assert msg.xor == 0x00

    def test_loco_get_info_short_address(self):
        """Test loco get info command for address < 128."""
        msg = XBusMessage.loco_get_info(3)

        assert msg.x_header == XBUS_LOCO_GET_INFO
        assert msg.dbs[0] == 0xF0
        assert msg.dbs[1] == 0x00  # MSB
        assert msg.dbs[2] == 0x03  # LSB

    def test_loco_get_info_long_address(self):
        """Test loco get info command for address >= 128."""
        msg = XBusMessage.loco_get_info(1234)

        assert msg.x_header == XBUS_LOCO_GET_INFO
        assert msg.dbs[0] == 0xF0
        # Address 1234 = 0x04D2
        # With 0xC0 flag: MSB = 0xC4, LSB = 0xD2
        assert msg.dbs[1] == 0xC4
        assert msg.dbs[2] == 0xD2

    def test_loco_drive_128_steps_forward(self):
        """Test drive command with 128 steps, forward."""
        msg = XBusMessage.loco_drive(3, DccThrottleSteps.STEPS_128, 0xC0)  # 64 forward

        assert msg.x_header == XBUS_LOCO_DRIVE
        assert msg.dbs[0] == 0x13  # 128 steps
        assert msg.dbs[1] == 0x00  # Address MSB
        assert msg.dbs[2] == 0x03  # Address LSB
        assert msg.dbs[3] == 0xC0  # Speed byte

    def test_loco_drive_28_steps_reverse(self):
        """Test drive command with 28 steps, reverse."""
        msg = XBusMessage.loco_drive(5, DccThrottleSteps.STEPS_28, 0x14)  # 20 reverse

        assert msg.x_header == XBUS_LOCO_DRIVE
        assert msg.dbs[0] == 0x12  # 28 steps
        assert msg.dbs[3] == 0x14

    def test_loco_drive_14_steps(self):
        """Test drive command with 14 steps."""
        msg = XBusMessage.loco_drive(10, DccThrottleSteps.STEPS_14, 0x87)  # 7 forward

        assert msg.x_header == XBUS_LOCO_DRIVE
        assert msg.dbs[0] == 0x10  # 14 steps

    def test_loco_drive_long_address(self):
        """Test drive command with long address."""
        msg = XBusMessage.loco_drive(500, DccThrottleSteps.STEPS_128, 0x80)

        # Address 500 = 0x01F4
        # With 0xC0 flag: MSB = 0xC1, LSB = 0xF4
        assert msg.dbs[1] == 0xC1
        assert msg.dbs[2] == 0xF4

    def test_loco_function_on(self):
        """Test function on command."""
        msg = XBusMessage.loco_function(3, 0, FunctionAction.ON)

        assert msg.x_header == XBUS_LOCO_DRIVE
        assert msg.dbs[0] == 0xF8
        # Function byte: 01 000000 = 0x40
        assert msg.dbs[3] == 0x40

    def test_loco_function_off(self):
        """Test function off command."""
        msg = XBusMessage.loco_function(3, 5, FunctionAction.OFF)

        assert msg.dbs[0] == 0xF8
        # Function byte: 00 000101 = 0x05
        assert msg.dbs[3] == 0x05

    def test_loco_function_toggle(self):
        """Test function toggle command."""
        msg = XBusMessage.loco_function(3, 10, FunctionAction.TOGGLE)

        # Function byte: 10 001010 = 0x8A
        assert msg.dbs[3] == 0x8A

    def test_loco_function_invalid_index(self):
        """Test that invalid function index raises ValueError."""
        with pytest.raises(ValueError, match="0-31"):
            XBusMessage.loco_function(3, 32, FunctionAction.ON)

        with pytest.raises(ValueError, match="0-31"):
            XBusMessage.loco_function(3, -1, FunctionAction.ON)

    def test_loco_function_all_functions(self):
        """Test all function indices 0-31."""
        for i in range(32):
            msg = XBusMessage.loco_function(1, i, FunctionAction.ON)
            # Function byte should have function number in lower 6 bits
            assert (msg.dbs[3] & 0x3F) == i
            # Action ON = 01 in upper 2 bits
            assert (msg.dbs[3] & 0xC0) == 0x40

    def test_get_turnout_info(self):
        """Test get turnout info command for address 0."""
        msg = XBusMessage.get_turnout_info(0)

        assert msg.x_header == XBUS_TURNOUT_INFO
        assert msg.dbs[0] == 0x00  # MSB
        assert msg.dbs[1] == 0x00  # LSB

    def test_get_turnout_info_high_address(self):
        """Test get turnout info command for address > 255."""
        msg = XBusMessage.get_turnout_info(500)

        assert msg.x_header == XBUS_TURNOUT_INFO
        # Address 500 = 0x01F4
        assert msg.dbs[0] == 0x01  # MSB
        assert msg.dbs[1] == 0xF4  # LSB

    def test_set_turnout_activate_p0_queue(self):
        """Test set turnout: activate output 0, queue mode."""
        msg = XBusMessage.set_turnout(0, output=0, activate=True, queue_mode=True)

        assert msg.x_header == XBUS_SET_TURNOUT
        # DB2: 1_1_0_1_0_0_0 = 0xA8
        assert msg.dbs[2] == 0xA8

    def test_set_turnout_activate_p1_queue(self):
        """Test set turnout: activate output 1, queue mode."""
        msg = XBusMessage.set_turnout(0, output=1, activate=True, queue_mode=True)

        assert msg.x_header == XBUS_SET_TURNOUT
        # DB2: 1_1_0_1_0_0_1 = 0xA9
        assert msg.dbs[2] == 0xA9

    def test_set_turnout_deactivate_p0_queue(self):
        """Test set turnout: deactivate output 0, queue mode."""
        msg = XBusMessage.set_turnout(0, output=0, activate=False, queue_mode=True)

        assert msg.x_header == XBUS_SET_TURNOUT
        # DB2: 1_1_0_0_0_0_0 = 0xA0
        assert msg.dbs[2] == 0xA0

    def test_set_turnout_activate_p0_immediate(self):
        """Test set turnout: activate output 0, immediate mode."""
        msg = XBusMessage.set_turnout(0, output=0, activate=True, queue_mode=False)

        assert msg.x_header == XBUS_SET_TURNOUT
        # DB2: 1_0_0_1_0_0_0 = 0x88
        assert msg.dbs[2] == 0x88

    def test_set_turnout_deactivate_p1_immediate(self):
        """Test set turnout: deactivate output 1, immediate mode."""
        msg = XBusMessage.set_turnout(0, output=1, activate=False, queue_mode=False)

        assert msg.x_header == XBUS_SET_TURNOUT
        # DB2: 1_0_0_0_0_0_1 = 0x81
        assert msg.dbs[2] == 0x81

    def test_set_turnout_address_encoding(self):
        """Test set turnout address encoding."""
        msg = XBusMessage.set_turnout(500, output=0, activate=True)

        # Address 500 = 0x01F4
        assert msg.dbs[0] == 0x01  # MSB
        assert msg.dbs[1] == 0xF4  # LSB

    def test_set_turnout_invalid_output(self):
        """Test that invalid output raises ValueError."""
        with pytest.raises(ValueError, match="0 or 1"):
            XBusMessage.set_turnout(0, output=2, activate=True)

    def test_repr(self):
        """Test string representation."""
        msg = XBusMessage(x_header=0x21, dbs=b"\x81")
        repr_str = repr(msg)

        assert "0x21" in repr_str.lower()
        assert "81" in repr_str.lower()
        assert "0xa0" in repr_str.lower()
