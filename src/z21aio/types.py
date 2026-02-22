"""
Data types for Z21 protocol.

Contains enums and dataclasses for protocol data structures.
"""

from dataclasses import dataclass
from enum import IntEnum, IntFlag
import struct


class DccThrottleSteps(IntEnum):
    """DCC throttle step modes."""

    STEPS_14 = 0
    STEPS_28 = 2
    STEPS_128 = 4

    @classmethod
    def from_byte(cls, value: int) -> "DccThrottleSteps":
        """Convert byte value to DccThrottleSteps."""
        match value & 0x07:
            case 0:
                return cls.STEPS_14
            case 2:
                return cls.STEPS_28
            case 4:
                return cls.STEPS_128
            case _:
                raise ValueError(f"Invalid DCC throttle steps value: {value}")

    def to_speed_byte(self) -> int:
        """Convert to speed command byte prefix."""
        match self:
            case DccThrottleSteps.STEPS_14:
                return 0x10
            case DccThrottleSteps.STEPS_28:
                return 0x12
            case DccThrottleSteps.STEPS_128:
                return 0x13

    @property
    def max_speed(self) -> int:
        """Maximum speed value for this throttle mode."""
        match self:
            case DccThrottleSteps.STEPS_14:
                return 14
            case DccThrottleSteps.STEPS_28:
                return 28
            case DccThrottleSteps.STEPS_128:
                return 128


class FunctionAction(IntEnum):
    """Action to perform on a locomotive function."""

    OFF = 0
    ON = 1
    TOGGLE = 2


class TurnoutPosition(IntEnum):
    """Turnout position from LAN_X_TURNOUT_INFO ZZ bits."""

    UNKNOWN = 0  # ZZ=00: not switched yet
    P0 = 1  # ZZ=01: position P=0 (output 1)
    P1 = 2  # ZZ=10: position P=1 (output 2)
    INVALID = 3  # ZZ=11: invalid


@dataclass
class TurnoutState:
    """Turnout state from LAN_X_TURNOUT_INFO."""

    address: int
    position: TurnoutPosition

    @classmethod
    def from_bytes(cls, data: bytes) -> "TurnoutState":
        """Parse from 3 XBus DB bytes (FAdr_MSB, FAdr_LSB, status).

        Args:
            data: 3 bytes of turnout state data

        Returns:
            TurnoutState instance

        Raises:
            ValueError: If data length is not 3 bytes
        """
        if len(data) != 3:
            raise ValueError(f"TurnoutState requires 3 bytes, got {len(data)}")
        address = (data[0] << 8) | data[1]
        position = TurnoutPosition(data[2] & 0x03)
        return cls(address=address, position=position)


@dataclass
class SystemState:
    """
    Z21 system state (16 bytes).

    Contains information about the command station's current state
    including current, voltage, and temperature readings.
    """

    main_current: int  # Main track current in mA
    prog_current: int  # Programming track current in mA
    filtered_main_current: int  # Smoothed main current in mA
    temperature: int  # Internal temperature in C
    supply_voltage: int  # Supply voltage in mV
    vcc_voltage: int  # VCC/track voltage in mV
    central_state: int  # Central state bitmask
    central_state_ex: int  # Extended central state bitmask
    reserved: int  # Reserved byte
    capabilities: int  # Capabilities bitmask (FW 1.42+)

    @classmethod
    def from_bytes(cls, data: bytes) -> "SystemState":
        """
        Parse SystemState from 16 bytes of data.

        Args:
            data: 16 bytes of system state data

        Returns:
            SystemState instance

        Raises:
            ValueError: If data length is not 16 bytes
        """
        if len(data) != 16:
            raise ValueError(f"SystemState requires 16 bytes, got {len(data)}")

        (
            main_current,
            prog_current,
            filtered_main_current,
            temperature,
            supply_voltage,
            vcc_voltage,
            central_state,
            central_state_ex,
            reserved,
            capabilities,
        ) = struct.unpack("<hhhhHHBBBB", data)

        return cls(
            main_current=main_current,
            prog_current=prog_current,
            filtered_main_current=filtered_main_current,
            temperature=temperature,
            supply_voltage=supply_voltage,
            vcc_voltage=vcc_voltage,
            central_state=central_state,
            central_state_ex=central_state_ex,
            reserved=reserved,
            capabilities=capabilities,
        )

    @property
    def is_track_voltage_off(self) -> bool:
        """Check if track voltage is off."""
        return bool(self.central_state & 0x02)

    @property
    def is_short_circuit(self) -> bool:
        """Check if short circuit detected."""
        return bool(self.central_state & 0x04)

    @property
    def is_programming_mode(self) -> bool:
        """Check if in programming mode."""
        return bool(self.central_state & 0x20)


@dataclass
class LocoState:
    """
    Locomotive state (variable length, 2-9 bytes).

    Contains information about a locomotive's current state including
    speed, direction, and function states.
    """

    address: int
    is_busy: bool | None = None
    stepping: DccThrottleSteps | None = None
    speed_percentage: float | None = None
    reverse: bool | None = None
    double_traction: bool | None = None
    smart_search: bool | None = None
    functions: list[bool] | None = None

    @classmethod
    def from_bytes(cls, data: bytes) -> "LocoState":
        """
        Parse LocoState from variable-length data.

        Args:
            data: 2-9 bytes of locomotive state data

        Returns:
            LocoState instance

        Raises:
            ValueError: If data length is less than 2 bytes
        """
        if len(data) < 2:
            raise ValueError(f"LocoState requires at least 2 bytes, got {len(data)}")

        # Bytes 0-1: Address (ignore 2 MSBs of byte 0)
        address = ((data[0] & 0x3F) << 8) | data[1]

        state = cls(address=address)

        if len(data) >= 3:
            # Byte 2: Busy flag and stepping
            state.is_busy = bool(data[2] & 0x08)
            try:
                state.stepping = DccThrottleSteps.from_byte(data[2])
            except ValueError:
                pass

        if len(data) >= 4:
            # Byte 3: Speed and direction
            speed_byte = data[3]
            state.reverse = not bool(speed_byte & 0x80)
            speed_value = speed_byte & 0x7F

            if state.stepping is not None:
                max_speed = state.stepping.max_speed
                state.speed_percentage = (speed_value / max_speed) * 100.0

        if len(data) >= 5:
            # Byte 4: Functions F0-F4, double traction, smart search
            state.double_traction = bool(data[4] & 0x40)
            state.smart_search = bool(data[4] & 0x20)

            # Initialize functions array
            functions = [False] * 32

            # F0 is in bit 4
            functions[0] = bool(data[4] & 0x10)
            # F1-F4 are in bits 0-3
            for i in range(1, 5):
                functions[i] = bool(data[4] & (1 << (i - 1)))

            state.functions = functions

        if len(data) >= 6 and state.functions is not None:
            # Byte 5: Functions F5-F12
            for i in range(8):
                state.functions[5 + i] = bool(data[5] & (1 << i))

        if len(data) >= 7 and state.functions is not None:
            # Byte 6: Functions F13-F20
            for i in range(8):
                state.functions[13 + i] = bool(data[6] & (1 << i))

        if len(data) >= 8 and state.functions is not None:
            # Byte 7: Functions F21-F28
            for i in range(8):
                state.functions[21 + i] = bool(data[7] & (1 << i))

        if len(data) >= 9 and state.functions is not None:
            # Byte 8: Functions F29-F31 (3 bits only)
            for i in range(3):
                state.functions[29 + i] = bool(data[8] & (1 << i))

        return state


class RailComOptions(IntFlag):
    """RailCom option flags from the Options byte."""

    NONE = 0x00
    SPEED1 = 0x01  # Speed 1 data available
    SPEED2 = 0x02  # Speed 2 data available
    QOS = 0x04  # Quality of Service data valid


@dataclass
class RailComData:
    """
    RailCom feedback data (13 bytes).

    Contains RailCom data broadcast from the Z21 command station,
    providing real-time feedback from RailCom-equipped decoders.

    Attributes:
        loco_address: Detected decoder address
        receive_counter: Number of valid RailCom messages received
        error_counter: Number of RailCom reception errors
        options: Option flags (speed type, QoS validity)
        speed: Current speed value (interpretation depends on options)
        qos: Quality of Service value (0-255, higher is better)
    """

    loco_address: int
    receive_counter: int
    error_counter: int
    options: RailComOptions
    speed: int
    qos: int

    @classmethod
    def from_bytes(cls, data: bytes) -> "RailComData":
        """
        Parse RailComData from 13 bytes of data.

        Args:
            data: 13 bytes of RailCom data

        Returns:
            RailComData instance

        Raises:
            ValueError: If data length is not 13 bytes
        """
        if len(data) != 13:
            raise ValueError(f"RailComData requires 13 bytes, got {len(data)}")

        (
            loco_address,
            receive_counter,
            error_counter,
            _reserved1,
            options,
            speed,
            qos,
            _reserved2,
        ) = struct.unpack("<HIHBBBBB", data)

        return cls(
            loco_address=loco_address,
            receive_counter=receive_counter,
            error_counter=error_counter,
            options=RailComOptions(options),
            speed=speed,
            qos=qos,
        )

    @property
    def has_speed1(self) -> bool:
        """Check if speed field contains Speed 1 value."""
        return bool(self.options & RailComOptions.SPEED1)

    @property
    def has_speed2(self) -> bool:
        """Check if speed field contains Speed 2 value."""
        return bool(self.options & RailComOptions.SPEED2)

    @property
    def has_qos(self) -> bool:
        """Check if QoS value is valid."""
        return bool(self.options & RailComOptions.QOS)

    @property
    def error_rate(self) -> float:
        """
        Calculate error rate as percentage.

        Returns:
            Error rate (0.0 to 100.0), or 0.0 if no messages received
        """
        total = self.receive_counter + self.error_counter
        if total == 0:
            return 0.0
        return (self.error_counter / total) * 100.0
