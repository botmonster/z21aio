"""
Locomotive function control example.

Demonstrates controlling locomotive functions F0-F31.
"""

import asyncio
import logging

from z21aio import Z21Station, Loco, FunctionAction

logging.basicConfig(level=logging.INFO)


async def main():
    async with await Z21Station.connect("192.168.0.111") as station:
        await station.voltage_on()

        loco = await Loco.control(station, address=3)

        # F0 - Headlights (convenience method)
        await loco.set_headlights(True)
        print("Headlights ON")

        await asyncio.sleep(1)

        # Turn on specific functions
        await loco.function_on(1)  # F1 - often rear lights
        await loco.function_on(2)  # F2 - often horn/whistle
        print("F1 and F2 ON")

        await asyncio.sleep(2)

        # Toggle a function
        await loco.function_toggle(3)
        print("F3 toggled")

        await asyncio.sleep(1)

        # Turn off functions
        await loco.function_off(1)
        await loco.function_off(2)
        print("F1 and F2 OFF")

        # Using FunctionAction enum directly
        await loco.set_function(4, FunctionAction.ON)
        await asyncio.sleep(1)
        await loco.set_function(4, FunctionAction.OFF)

        # Turn off headlights
        await loco.set_headlights(False)
        print("Headlights OFF")

        await station.voltage_off()


if __name__ == "__main__":
    asyncio.run(main())
