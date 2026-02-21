"""
Locomotive state example.

Demonstrates getting and subscribing to locomotive state.
"""

import asyncio
import logging

from z21aio import Z21Station, Loco, LocoState

logging.basicConfig(level=logging.INFO)


def on_loco_state(state: LocoState):
    """Callback for locomotive state updates."""
    print(f"Address: {state.address}")
    if state.speed_percentage is not None:
        direction = "reverse" if state.reverse else "forward"
        print(f"Speed: {state.speed_percentage:.1f}% ({direction})")
    else:
        print("Speed: N/A")
    print(f"Busy: {state.is_busy}")
    if state.functions:
        active = [f"F{i}" for i, on in enumerate(state.functions) if on]
        print(f"Active functions: {', '.join(active) if active else 'None'}")
    print("-" * 40)


async def main():
    async with await Z21Station.connect("192.168.0.111") as station:
        await station.voltage_on()

        loco = await Loco.control(station, address=3)

        # Get current state once
        print("Getting current state:")
        state = await loco.get_state()
        on_loco_state(state)

        # Subscribe to state updates
        print("\nSubscribing to state updates...")
        loco.subscribe_state(on_loco_state)

        # Make some changes to see updates
        await loco.set_headlights(True)
        await asyncio.sleep(1)

        await loco.drive(30.0)
        await asyncio.sleep(2)

        await loco.drive(60.0)
        await asyncio.sleep(2)

        # Normal stop - decelerates per decoder settings
        await loco.stop()
        await asyncio.sleep(1)

        # Emergency stop - immediate halt (E-Stop, speed byte 0x01)
        await loco.drive(30.0)
        await asyncio.sleep(1)
        await loco.estop()
        await asyncio.sleep(1)

        await loco.set_headlights(False)

        await station.voltage_off()


if __name__ == "__main__":
    asyncio.run(main())
