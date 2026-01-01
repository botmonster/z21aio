"""
Basic Z21 usage example.

Connects to Z21, turns on power, drives a locomotive, then stops.
"""

import asyncio
import logging

from z21aio import Z21Station, Loco

logging.basicConfig(level=logging.INFO)


async def main():
    # Connect to Z21 station
    async with await Z21Station.connect("192.168.0.111") as station:
        # Get serial number
        serial = await station.get_serial_number()
        print(f"Connected to Z21, serial: {serial}")

        # Turn on track power
        await station.voltage_on()
        print("Track power ON")

        # Control locomotive at address 3
        loco = await Loco.control(station, address=3)
        print("Controlling locomotive at address 3")

        # Turn on headlights and drive forward
        await loco.set_headlights(True)
        await loco.drive(50.0)  # 50% forward
        print("Driving at 50% forward")

        await asyncio.sleep(5)

        # Stop and turn off power
        await loco.stop()
        print("Locomotive stopped")

        await station.voltage_off()
        print("Track power OFF")


if __name__ == "__main__":
    asyncio.run(main())
