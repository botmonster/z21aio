========
Examples
========

This directory contains complete working examples demonstrating z21aio functionality. All examples assume a Z21 command station at ``192.168.0.111`` with a locomotive at address 3.

Basic Example
=============

**File:** `basic.py <https://github.com/botmonster/z21aio/blob/main/examples/basic.py>`_

The simplest example showing how to:

- Connect to a Z21 station
- Get the serial number
- Turn on track power
- Control a locomotive
- Stop and disconnect

.. code-block:: python

    async with await Z21Station.connect("192.168.0.111") as station:
        serial = await station.get_serial_number()
        print(f"Connected to Z21, serial: {serial}")

        await station.voltage_on()

        loco = await Loco.control(station, address=3)
        await loco.set_headlights(True)
        await loco.drive(50.0)

        await asyncio.sleep(5)

        await loco.stop()
        await station.voltage_off()

**Run it:**

.. code-block:: bash

    python examples/basic.py

Speed Control Example
=====================

**File:** `speed.py <https://github.com/botmonster/z21aio/blob/main/examples/speed.py>`_

Demonstrates speed control including:

- Forward speeds at different percentages
- Reverse operation
- Normal stop with braking curve
- Emergency halt (immediate stop)
- Different throttle step modes

.. code-block:: python

    loco = await Loco.control(station, address=3)

    # Different speeds
    await loco.drive(25.0)   # 25% forward
    await loco.drive(50.0)   # 50% forward
    await loco.drive(75.0)   # 75% forward
    await loco.drive(-50.0)  # 50% reverse

    # Normal stop (with braking curve)
    await loco.stop()

    # Emergency halt (immediate stop)
    await loco.halt()

**Run it:**

.. code-block:: bash

    python examples/speed.py

Function Control Example
========================

**File:** `functions.py <https://github.com/botmonster/z21aio/blob/main/examples/functions.py>`_

Shows how to control locomotive functions (F0-F31):

- F0 (headlights) using convenience method
- Turn functions on and off
- Toggle functions
- Using the FunctionAction enum

.. code-block:: python

    loco = await Loco.control(station, address=3)

    # Headlights (F0) - convenience method
    await loco.set_headlights(True)

    # Turn on specific functions
    await loco.function_on(1)   # F1
    await loco.function_on(2)   # F2

    # Toggle a function
    await loco.function_toggle(3)

    # Using set_function with FunctionAction enum
    await loco.set_function(4, FunctionAction.ON)
    await loco.set_function(4, FunctionAction.OFF)

**Run it:**

.. code-block:: bash

    python examples/functions.py

Multi-Station Example
=====================

**File:** `multi_station.py <https://github.com/botmonster/z21aio/blob/main/examples/multi_station.py>`_

Demonstrates controlling multiple Z21 stations simultaneously:

- Connect to multiple stations in parallel
- Control different locomotives on different stations
- Independent speed control for each locomotive

.. code-block:: python

    async with await Z21Station.connect("192.168.0.111") as station1, \
               await Z21Station.connect("192.168.0.112") as station2:

        loco1 = await Loco.control(station1, address=3)
        loco2 = await Loco.control(station2, address=5)

        await loco1.drive(50.0)
        await loco2.drive(30.0)

        await asyncio.sleep(10)

**Run it:**

.. code-block:: bash

    python examples/multi_station.py

System State Monitoring Example
===============================

**File:** `monitor.py <https://github.com/botmonster/z21aio/blob/main/examples/monitor.py>`_

Shows how to monitor system state including:

- Voltage and current draw
- Temperature
- Track power status
- Frequency-based polling

.. code-block:: python

    def on_state_change(state):
        print(f"Voltage: {state.voltage}V")
        print(f"Current: {state.current}mA")
        print(f"Temperature: {state.temperature}°C")

    # Subscribe to updates at 1 Hz
    task = station.subscribe_system_state(on_state_change, freq_hz=1.0)

    await asyncio.sleep(30)

    task.cancel()

**Run it:**

.. code-block:: bash

    python examples/monitor.py

Locomotive State Example
========================

**File:** `loco_state.py <https://github.com/botmonster/z21aio/blob/main/examples/loco_state.py>`_

Demonstrates locomotive state management:

- Get current locomotive state
- Parse speed and direction
- Get function states
- Subscribe to state change notifications
- Respond to state updates in real-time

.. code-block:: python

    # Get current state
    state = await loco.get_state()
    print(f"Speed: {state.speed_percentage}%")
    print(f"Direction: {state.direction}")

    # Subscribe to state changes
    def on_loco_state(state):
        print(f"Loco {state.address}: Speed {state.speed_percentage}%")

    loco.subscribe_state(on_loco_state)

**Run it:**

.. code-block:: bash

    python examples/loco_state.py

Custom Example
==============

To create your own example, start with the basic template:

.. code-block:: python

    import asyncio
    from z21aio import Z21Station, Loco

    async def main():
        async with await Z21Station.connect("192.168.0.111") as station:
            # Your code here
            pass

    if __name__ == "__main__":
        asyncio.run(main())

Tips
====

- Change the IP address from ``192.168.0.111`` to match your Z21 station
- Change the locomotive address (usually 3) to match your test locomotive
- Enable logging to see debug information:

.. code-block:: python

    import logging
    logging.basicConfig(level=logging.DEBUG)

- Use ``asyncio.sleep()`` to add delays between commands
- All methods are async - remember to use ``await``
