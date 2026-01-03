"""
Z21 LAN packet handling.

Handles serialization and deserialization of Z21 UDP packets.
Packet format: [u16 length LE][u16 header LE][data bytes]
"""

from dataclasses import dataclass
import struct

from .headers import LAN_X, get_header_name, get_x_header_name


@dataclass
class Packet:
    """
    Z21 LAN packet.

    The packet format is:
    - 2 bytes: Total length (little-endian), includes header
    - 2 bytes: Message header/type (little-endian)
    - N bytes: Payload data

    Attributes:
        header: 16-bit message type identifier
        data: Variable-length payload bytes
    """

    header: int
    data: bytes = b""

    @property
    def data_len(self) -> int:
        """Total packet length including 4-byte header."""
        return 4 + len(self.data)

    def to_bytes(self) -> bytes:
        """
        Serialize packet to bytes.

        Returns:
            Bytes in Z21 LAN packet format
        """
        return struct.pack("<HH", self.data_len, self.header) + self.data

    @classmethod
    def from_bytes(cls, data: bytes) -> "Packet":
        """
        Deserialize packet from bytes.

        Args:
            data: Raw packet bytes

        Returns:
            Packet instance

        Raises:
            ValueError: If data is too short (< 4 bytes)
        """
        if len(data) < 4:
            raise ValueError(f"Packet requires at least 4 bytes, got {len(data)}")

        data_len, header = struct.unpack("<HH", data[:4])
        payload = data[4:data_len] if data_len > 4 else b""

        return cls(header=header, data=payload)

    @classmethod
    def with_header(cls, header: int) -> "Packet":
        """
        Create a packet with just a header (no data).

        Args:
            header: Message header/type

        Returns:
            Packet with empty data
        """
        return cls(header=header)

    @classmethod
    def with_header_and_data(cls, header: int, data: bytes) -> "Packet":
        """
        Create a packet with header and data.

        Args:
            header: Message header/type
            data: Payload bytes

        Returns:
            Packet with specified header and data
        """
        return cls(header=header, data=data)

    def __repr__(self) -> str:
        header_name = get_header_name(self.header)

        # Check if this is an X-BUS packet (LAN_X header with x-header in data)
        if self.header == LAN_X and len(self.data) >= 1:
            x_header = self.data[0]
            x_header_name = get_x_header_name(x_header)
            return (
                f"Packet(header=0x{self.header:04X} [{header_name}], "
                f"x_header=0x{x_header:02X} [{x_header_name}], "
                f'data={self.data.hex(" ")})'
            )

        return f'Packet(header=0x{self.header:04X} [{header_name}], data={self.data.hex(" ")})'
