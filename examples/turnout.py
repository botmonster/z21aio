"""
Turnout control example.

Demonstrates switching turnouts and subscribing to state updates.
"""

import asyncio
import logging

from z21aio import Z21Station, TurnoutPosition, TurnoutState
from z21aio.turnout import Turnout

logging.basicConfig(level=logging.DEBUG)


def on_turnout_state(state: TurnoutState):
    """Handle turnout state update."""
    print(f"Turnout {state.address}: position={state.position.name}")


def on_any_turnout(state: TurnoutState):
    """Handle turnout state update from any turnout."""
    print(f"  Event: turnout {state.address} -> {state.position.name}")


async def main():
    async with await Z21Station.connect("192.168.0.111") as station:
        # Control turnout at address 0
        turnout = Turnout(station, address=0)

        await asyncio.sleep(1)
        # Subscribe to state updates
        turnout.subscribe_state(on_turnout_state)
        # Subscribe to all turnout state updates
        station.subscribe_turnout_state(on_any_turnout)

        # Get current state
        state = await turnout.get_state()
        print(f"Current position: {state.position.name}")

        # Switch to position P0 (output 1)
        await turnout.switch(TurnoutPosition.P0)
        print("Switched to P0")
        await asyncio.sleep(1)

        # Switch to position P1 (output 2)
        await turnout.switch(TurnoutPosition.P1)
        print("Switched to P1")
        await asyncio.sleep(1)

        # Listen for turnout events from all turnouts
        print("\nListening for turnout events (press Ctrl+C to stop)...")

        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    asyncio.run(main())
