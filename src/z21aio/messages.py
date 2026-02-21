"""
Z21 protocol message constants and XBus message handling.

Contains LAN headers, XBus headers, and the XBusMessage class
for handling XBus protocol messages with XOR checksums.
"""

from dataclasses import dataclass
from functools import reduce
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .types import DccThrottleSteps, FunctionAction

# LAN Headers (message types)
LAN_GET_SERIAL_NUMBER = 0x10
LAN_LOGOFF = 0x30
LAN_DISCOVER_DEVICES = 0x35
LAN_XBUS_HEADER = 0x40
LAN_SET_BROADCASTFLAGS = 0x50
LAN_GET_BROADCASTFLAGS = 0x51
LAN_SYSTEMSTATE_DATACHANGED = 0x84
LAN_SYSTEMSTATE_GETDATA = 0x85

# XBus Headers (command types within XBus messages)
XBUS_SET_TRACK_POWER = 0x21
XBUS_GET_VERSION = 0x21
XBUS_GET_VERSION_REPLY = 0x63
XBUS_BC_TRACK_POWER = 0x61
XBUS_BC_TRACK_POWER_OFF_DB0 = 0x00  # DB0 value in power-off broadcast (2.7)
XBUS_BC_TRACK_POWER_ON_DB0 = 0x01   # DB0 value in power-on broadcast (2.8)
XBUS_LOCO_GET_INFO = 0xE3
XBUS_LOCO_DRIVE = 0xE4
XBUS_LOCO_INFO = 0xEF
XBUS_GET_FIRMWARE_VERSION = 0xF1
XBUS_GET_FIRMWARE_VERSION_REPLY = 0xF3

# Broadcast flags
BROADCAST_LOCO_INFO = 0x00000001
BROADCAST_TURNOUT_INFO = 0x00000001  # Same as LOCO_INFO
BROADCAST_RAILCOM_SUBSCRIBED = 0x00000004  # RailCom data for subscribed locos
BROADCAST_SYSTEMSTATE = 0x00000100
BROADCAST_RAILCOM_ALL = 0x00040000  # All RailCom data (FW 1.29+)

# RailCom LAN Headers
LAN_RAILCOM_DATACHANGED = 0x88
LAN_RAILCOM_GETDATA = 0x89


@dataclass
class XBusMessage:
    """
    XBus protocol message.

    XBus messages are encapsulated within LAN packets with header 0x40.
    Format: [x_header][data_bytes...][xor_checksum]

    The XOR checksum is calculated as XOR of x_header and all data bytes.

    Attributes:
        x_header: Command type byte
        dbs: Data bytes (variable length)
    """

    x_header: int
    dbs: bytes = b""

    @property
    def xor(self) -> int:
        """Calculate XOR checksum of x_header and all data bytes."""
        return reduce(lambda acc, x: acc ^ x, self.dbs, self.x_header)

    def to_bytes(self) -> bytes:
        """
        Serialize to bytes with XOR checksum.

        Returns:
            Bytes: [x_header][data_bytes][xor]
        """
        return bytes([self.x_header]) + self.dbs + bytes([self.xor])

    @classmethod
    def from_bytes(cls, data: bytes) -> "XBusMessage":
        """
        Parse XBus message from bytes with XOR validation.

        Args:
            data: Raw XBus message bytes

        Returns:
            XBusMessage instance

        Raises:
            ValueError: If XOR checksum is invalid
        """
        if len(data) < 2:
            raise ValueError(f"XBusMessage requires at least 2 bytes, got {len(data)}")

        x_header = data[0]
        dbs = data[1:-1]
        received_xor = data[-1]

        msg = cls(x_header=x_header, dbs=dbs)

        if msg.xor != received_xor:
            raise ValueError(
                f"XBus XOR mismatch: calculated 0x{msg.xor:02X}, "
                f"received 0x{received_xor:02X}"
            )

        return msg

    @classmethod
    def get_firmware_version(cls) -> "XBusMessage":
        """Create command to request firmware version."""
        return cls(x_header=XBUS_GET_FIRMWARE_VERSION, dbs=bytes([0x0A]))

    @classmethod
    def get_version(cls) -> "XBusMessage":
        """Create command to request X-BUS version and command station ID."""
        return cls(x_header=XBUS_GET_VERSION, dbs=bytes([0x21]))

    @classmethod
    def track_power_on(cls) -> "XBusMessage":
        """Create command to turn on track power."""
        return cls(x_header=XBUS_SET_TRACK_POWER, dbs=bytes([0x81]))

    @classmethod
    def track_power_off(cls) -> "XBusMessage":
        """Create command to turn off track power (emergency stop)."""
        return cls(x_header=XBUS_SET_TRACK_POWER, dbs=bytes([0x80]))

    @classmethod
    def loco_get_info(cls, address: int) -> "XBusMessage":
        """
        Create command to request locomotive state.

        Args:
            address: DCC locomotive address (1-9999)

        Returns:
            XBusMessage for getting locomotive info
        """
        addr_msb = (address >> 8) & 0xFF
        addr_lsb = address & 0xFF

        # For addresses >= 128, set the high bits
        if address >= 128:
            addr_msb |= 0xC0

        return cls(x_header=XBUS_LOCO_GET_INFO, dbs=bytes([0xF0, addr_msb, addr_lsb]))

    @classmethod
    def loco_drive(
        cls, address: int, steps: "DccThrottleSteps", speed_byte: int
    ) -> "XBusMessage":
        """
        Create command to drive a locomotive.

        Args:
            address: DCC locomotive address (1-9999)
            steps: Throttle step mode (14/28/128)
            speed_byte: Speed value with direction bit 7
                       (0x00 = stop, 0x01 = emergency stop)

        Returns:
            XBusMessage for driving locomotive
        """
        addr_msb = (address >> 8) & 0xFF
        addr_lsb = address & 0xFF

        # For addresses >= 128, set the high bits
        if address >= 128:
            addr_msb |= 0xC0

        return cls(
            x_header=XBUS_LOCO_DRIVE,
            dbs=bytes([steps.to_speed_byte(), addr_msb, addr_lsb, speed_byte]),
        )

    @classmethod
    def loco_function(
        cls, address: int, function: int, action: "FunctionAction"
    ) -> "XBusMessage":
        """
        Create command to control a locomotive function.

        Args:
            address: DCC locomotive address (1-9999)
            function: Function number (0-31)
            action: Action to perform (OFF, ON, TOGGLE)

        Returns:
            XBusMessage for controlling locomotive function

        Raises:
            ValueError: If function is not 0-31
        """
        if not 0 <= function <= 31:
            raise ValueError(f"Function must be 0-31, got {function}")

        addr_msb = (address >> 8) & 0xFF
        addr_lsb = address & 0xFF

        # For addresses >= 128, set the high bits
        if address >= 128:
            addr_msb |= 0xC0

        # Function byte: TT NNNNNN
        # TT = action type (bits 7-6)
        # NNNNNN = function number (bits 5-0)
        function_byte = (int(action) << 6) | function

        return cls(
            x_header=XBUS_LOCO_DRIVE,
            dbs=bytes([0xF8, addr_msb, addr_lsb, function_byte]),
        )

    def __repr__(self) -> str:
        return (
            f"XBusMessage(x_header=0x{self.x_header:02X}, "
            f"dbs={self.dbs.hex()}, xor=0x{self.xor:02X})"
        )
