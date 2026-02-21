"""
Track power control example.

Demonstrates turning track power on/off and subscribing to power state changes.
Power state changes can be triggered by this client OR by external devices (e.g., multiMaus).
"""

import asyncio
import logging

from z21aio import Z21Station

logging.basicConfig(level=logging.INFO)


def on_track_power(is_on: bool) -> None:
    """Called when track power state changes."""
    state = "ON" if is_on else "OFF"
    print(f"Track power: {state}")


async def main() -> None:
    """Connect, subscribe to track power events, toggle power, and disconnect."""
    async with await Z21Station.connect("192.168.0.111") as station:
        # Subscribe to power state changes (works for all sources)
        station.subscribe_track_power(on_track_power)

        # Turn on track power
        print("Turning power on...")
        await station.voltage_on()

        # Wait to observe the power-on broadcast
        await asyncio.sleep(3)

        # Turn off track power
        print("Turning power off...")
        await station.voltage_off()

        # Wait to observe the power-off broadcast
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
