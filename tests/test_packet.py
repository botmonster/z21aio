"""Tests for packet.py - UDP packet serialization/deserialization."""

import pytest
from z21aio.packet import Packet


class TestPacket:
    """Tests for Packet class."""

    def test_packet_to_bytes_empty_data(self):
        """Test serialization of packet with no data."""
        packet = Packet(header=0x10, data=b"")
        result = packet.to_bytes()

        # Length should be 4 (header only)
        assert result == b"\x04\x00\x10\x00"

    def test_packet_to_bytes_with_data(self):
        """Test serialization of packet with data."""
        packet = Packet(header=0x40, data=b"\x21\x81\xa0")
        result = packet.to_bytes()

        # Length = 4 + 3 = 7
        assert result[:2] == b"\x07\x00"  # Length (LE)
        assert result[2:4] == b"\x40\x00"  # Header (LE)
        assert result[4:] == b"\x21\x81\xa0"  # Data

    def test_packet_from_bytes_empty_data(self):
        """Test deserialization of packet with no data."""
        data = b"\x04\x00\x10\x00"
        packet = Packet.from_bytes(data)

        assert packet.header == 0x10
        assert packet.data == b""
        assert packet.data_len == 4

    def test_packet_from_bytes_with_data(self):
        """Test deserialization of packet with data."""
        data = b"\x07\x00\x40\x00\x21\x81\xa0"
        packet = Packet.from_bytes(data)

        assert packet.header == 0x40
        assert packet.data == b"\x21\x81\xa0"
        assert packet.data_len == 7

    def test_packet_roundtrip(self):
        """Test that serialization and deserialization are inverse operations."""
        original = Packet(header=0x84, data=b"\x01\x02\x03\x04\x05\x06\x07\x08")
        serialized = original.to_bytes()
        restored = Packet.from_bytes(serialized)

        assert restored.header == original.header
        assert restored.data == original.data

    def test_packet_from_bytes_too_short(self):
        """Test that parsing too-short data raises ValueError."""
        with pytest.raises(ValueError, match="at least 4 bytes"):
            Packet.from_bytes(b"\x04\x00")

    def test_packet_with_header(self):
        """Test factory method for header-only packet."""
        packet = Packet.with_header(0x30)

        assert packet.header == 0x30
        assert packet.data == b""

    def test_packet_with_header_and_data(self):
        """Test factory method for packet with header and data."""
        packet = Packet.with_header_and_data(0x50, b"\x01\x00\x00\x00")

        assert packet.header == 0x50
        assert packet.data == b"\x01\x00\x00\x00"

    def test_packet_data_len_property(self):
        """Test data_len property calculation."""
        packet = Packet(header=0x10, data=b"\x01\x02\x03")
        assert packet.data_len == 7  # 4 + 3

    def test_packet_repr_lan_header(self):
        """Test string representation for regular LAN header."""
        packet = Packet(header=0x10, data=b"")
        repr_str = repr(packet)

        assert "0x0010" in repr_str
        assert "LAN_GET_SERIAL_NUMBER" in repr_str

    def test_packet_repr_x_bus_packet(self):
        """Test string representation for X-BUS packet with x-header."""
        # LAN_X header (0x40) with x-header 0xE3 (LAN_X_GET_LOCO_INFO)
        packet = Packet(header=0x40, data=b"\xe3\xf0\x00\x03")
        repr_str = repr(packet)

        assert "0x0040" in repr_str
        assert "LAN_X" in repr_str
        assert "x_header=0xE3" in repr_str
        assert "LAN_X_PURGE_LOCO/LAN_X_GET_LOCO_INFO" in repr_str
        assert "e3 f0 00 03" in repr_str

    def test_packet_repr_x_bus_set_loco_drive(self):
        """Test string representation for X-BUS loco drive command."""
        # LAN_X header (0x40) with x-header 0xE4 (LAN_X_SET_LOCO_DRIVE)
        packet = Packet(header=0x40, data=b"\xe4\x13\x00\x03\x80")
        repr_str = repr(packet)

        assert "LAN_X" in repr_str
        assert "x_header=0xE4" in repr_str
        assert "LAN_X_SET_LOCO_DRIVE" in repr_str

    def test_packet_repr_x_bus_empty_data(self):
        """Test X-BUS packet with empty data falls back to regular repr."""
        # LAN_X header but no data (edge case)
        packet = Packet(header=0x40, data=b"")
        repr_str = repr(packet)

        assert "0x0040" in repr_str
        assert "LAN_X" in repr_str
        # Should NOT have x_header since data is empty
        assert "x_header" not in repr_str

    def test_packet_repr_unknown_header(self):
        """Test string representation for unknown header."""
        packet = Packet(header=0xFF, data=b"\x01\x02")
        repr_str = repr(packet)

        assert "0x00FF" in repr_str
        assert "UNKNOWN_HEADER_0xFF" in repr_str

    def test_packet_repr_system_state(self):
        """Test string representation for system state packet."""
        packet = Packet(header=0x84, data=b"\x00" * 16)
        repr_str = repr(packet)

        assert "0x0084" in repr_str
        assert "LAN_SYSTEMSTATE_DATACHANGED" in repr_str

    def test_packet_large_data(self):
        """Test packet with larger data payload."""
        large_data = bytes(range(256))
        packet = Packet(header=0x99, data=large_data)

        assert packet.data_len == 4 + 256

        serialized = packet.to_bytes()
        restored = Packet.from_bytes(serialized)

        assert restored.data == large_data

    def test_packet_from_bytes_respects_length(self):
        """Test that from_bytes respects the length field."""
        # Packet says length is 6, but we provide more data
        data = b"\x06\x00\x40\x00\xab\xcd\xff\xff\xff"
        packet = Packet.from_bytes(data)

        # Should only include 2 bytes of data (6 - 4 = 2)
        assert packet.data == b"\xab\xcd"
