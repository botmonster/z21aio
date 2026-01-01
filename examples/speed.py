"""
Speed control example.

Demonstrates forward, reverse, stop, and emergency halt.
"""

import asyncio
import logging

from z21aio import Z21Station, Loco, DccThrottleSteps

logging.basicConfig(level=logging.INFO)


async def main():
    async with await Z21Station.connect("192.168.0.111") as station:
        await station.voltage_on()

        # Control locomotive with 128-step mode (default)
        loco = await Loco.control(station, address=3)

        # Or use different throttle steps:
        # loco = await Loco.control(station, address=3, steps=DccThrottleSteps.STEPS_28)

        print("Forward speeds...")
        await loco.drive(25.0)  # 25% forward
        await asyncio.sleep(2)

        await loco.drive(50.0)  # 50% forward
        await asyncio.sleep(2)

        await loco.drive(75.0)  # 75% forward
        await asyncio.sleep(2)

        print("Reverse...")
        await loco.drive(-50.0)  # 50% reverse
        await asyncio.sleep(3)

        print("Normal stop (with braking)...")
        await loco.stop()
        await asyncio.sleep(2)

        print("Accelerating again...")
        await loco.drive(80.0)
        await asyncio.sleep(2)

        print("Emergency halt!")
        await loco.halt()  # Immediate stop, no braking curve

        await station.voltage_off()
        print("Done")


if __name__ == "__main__":
    asyncio.run(main())
