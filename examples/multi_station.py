"""
Multi-station example.

Demonstrates connecting to multiple Z21 stations simultaneously
and controlling locomotives on each.
"""

import asyncio
import logging

from z21aio import Z21Station, Loco

logging.basicConfig(level=logging.INFO)


async def main():
    # Connect to two Z21 stations simultaneously
    async with (
        await Z21Station.connect("192.168.0.111") as station1,
        await Z21Station.connect("192.168.0.112") as station2,
    ):

        print("Connected to both stations")

        # Turn on power on both stations
        await station1.voltage_on()
        await station2.voltage_on()

        # Control locomotives on different stations
        loco1 = await Loco.control(station1, address=3)
        loco2 = await Loco.control(station2, address=5)

        print("Controlling loco 3 on station 1, loco 5 on station 2")

        # Drive both locomotives
        await loco1.drive(50.0)
        await loco2.drive(30.0)

        await asyncio.sleep(5)

        # Stop both
        await loco1.stop()
        await loco2.stop()

        # Power off
        await station1.voltage_off()
        await station2.voltage_off()

        print("Done")


if __name__ == "__main__":
    asyncio.run(main())
