"""
System state monitoring example.

Subscribes to Z21 system state updates and prints them.
"""

import asyncio
import logging

from z21aio import Z21Station, SystemState

logging.basicConfig(level=logging.INFO)


def on_system_state(state: SystemState):
    """Callback for system state updates."""
    print(f"Main current: {state.main_current} mA")
    print(f"Temperature: {state.temperature} C")
    print(f"Supply voltage: {state.supply_voltage} mV")
    print(f"Track voltage: {state.vcc_voltage} mV")
    print(f"Track power off: {state.is_track_voltage_off}")
    print(f"Short circuit: {state.is_short_circuit}")
    print("-" * 40)


async def main():
    async with await Z21Station.connect("192.168.0.111") as station:
        print("Connected, subscribing to system state...")

        # Subscribe to system state at 1 Hz (1 update per second)
        task = station.subscribe_system_state(on_system_state, freq_hz=1.0)

        # Turn on power to see current readings
        await station.voltage_on()

        # Monitor for 10 seconds
        await asyncio.sleep(10)

        # Cancel the subscription task
        task.cancel()

        await station.voltage_off()
        print("Done monitoring")


if __name__ == "__main__":
    asyncio.run(main())
