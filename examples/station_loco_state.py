"""
Example: Subscribe to all locomotive state updates at the station level.

This demonstrates subscribing to state updates from ALL locomotives
without needing to create Loco instances or know addresses in advance.
"""

import asyncio
from z21aio import Z21Station
from z21aio.types import LocoState


def on_any_loco_state(state: LocoState):
    """Called when any locomotive state changes."""
    print(f"Loco {state.address}: ", end="")
    if state.speed_percentage is not None:
        print(f"speed={state.speed_percentage:+.1f}%", end=" ")
    if state.functions:
        active = [f"F{i}" for i, on in enumerate(state.functions) if on]
        if active:
            print(f"functions={','.join(active)}", end=" ")
    print()


async def main():
    async with await Z21Station.connect("192.168.2.216") as station:
        # Subscribe to all loco state updates
        station.subscribe_loco_state(on_any_loco_state)

        print("Listening for locomotive state updates...")
        print("Control locomotives from your Z21 controller or other apps.")
        print("Press Ctrl+C to exit.")

        # Keep connection alive
        while True:
            await asyncio.sleep(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
