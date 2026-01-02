===========
Quick Start
===========

Basic Connection
================

To connect to a Z21 station and control a locomotive, you only need a few lines of code:

.. code-block:: python

    import asyncio
    from z21aio import Z21Station, Loco

    async def main():
        # Connect to Z21 station
        async with await Z21Station.connect("192.168.0.111") as station:
            # Get serial number to verify connection
            serial = await station.get_serial_number()
            print(f"Connected to Z21, serial: {serial}")

            # Turn on track power
            await station.voltage_on()

            # Control locomotive at address 3
            loco = await Loco.control(station, address=3)
            await loco.set_headlights(True)
            await loco.drive(50.0)  # 50% forward

            await asyncio.sleep(5)

            await loco.stop()
            await station.voltage_off()

    asyncio.run(main())

Key Points
==========

- Always use :class:`Z21Station` as an async context manager to ensure proper cleanup
- Use :meth:`Z21Station.connect` to establish a connection
- Use :meth:`Loco.control` to take control of a locomotive
- Speed is specified as a percentage: -100 to 100 (negative = reverse)
- The default throttle mode is 128 steps (smoothest control)

Multi-Station Control
=====================

Control multiple Z21 stations simultaneously:

.. code-block:: python

    async def multi_station():
        async with await Z21Station.connect("192.168.0.111") as station1, \
                   await Z21Station.connect("192.168.0.112") as station2:
            loco1 = await Loco.control(station1, address=3)
            loco2 = await Loco.control(station2, address=5)

            await loco1.drive(50.0)
            await loco2.drive(30.0)

            await asyncio.sleep(10)

            await loco1.stop()
            await loco2.stop()

    asyncio.run(multi_station())

Speed Control
=============

Speed is controlled with a percentage from -100 to 100:

.. code-block:: python

    # Forward speeds
    await loco.drive(25.0)   # 25% forward
    await loco.drive(50.0)   # 50% forward (medium speed)
    await loco.drive(100.0)  # 100% forward (full speed)

    # Reverse speeds
    await loco.drive(-50.0)  # 50% reverse

    # Stops
    await loco.stop()   # Normal stop with braking curve
    await loco.halt()   # Emergency stop (immediate)

Function Control
================

Control locomotive functions (F0-F31):

.. code-block:: python

    # Control specific functions
    await loco.set_headlights(True)   # Turn F0 (headlights) on
    await loco.function_on(2)         # Turn F2 on
    await loco.function_off(2)        # Turn F2 off
    await loco.function_toggle(3)     # Toggle F3

Throttle Modes
==============

Specify throttle step resolution:

.. code-block:: python

    from z21aio import DccThrottleSteps, Loco

    # 128-step mode (default, smoothest)
    loco = await Loco.control(
        station,
        address=3,
        steps=DccThrottleSteps.STEPS_128
    )

    # 28-step mode (common)
    loco = await Loco.control(
        station,
        address=3,
        steps=DccThrottleSteps.STEPS_28
    )

    # 14-step mode (legacy)
    loco = await Loco.control(
        station,
        address=3,
        steps=DccThrottleSteps.STEPS_14
    )

Getting Station Information
============================

Query the Z21 station for information:

.. code-block:: python

    async with await Z21Station.connect("192.168.0.111") as station:
        # Serial number
        serial = await station.get_serial_number()
        print(f"Serial: {serial}")

        # Firmware version
        major, minor = await station.get_firmware_version()
        print(f"Firmware: {major}.{minor}")

        # X-Bus version and command station ID
        xbus_version, cs_id = await station.get_version()
        print(f"X-Bus Version: {xbus_version}, Command Station ID: {cs_id}")

System State Monitoring
=======================

Subscribe to system state updates to monitor voltage, current, and temperature:

.. code-block:: python

    def on_state_change(state):
        print(f"Voltage: {state.voltage}V")
        print(f"Current: {state.current}mA")
        print(f"Temperature: {state.temperature}°C")

    async with await Z21Station.connect("192.168.0.111") as station:
        # Subscribe to updates (1 Hz)
        task = station.subscribe_system_state(on_state_change, freq_hz=1.0)

        await asyncio.sleep(30)

        # Cancel the subscription
        task.cancel()

Locomotive State
================

Get and monitor locomotive state:

.. code-block:: python

    async with await Z21Station.connect("192.168.0.111") as station:
        loco = await Loco.control(station, address=3)

        # Get current state
        state = await loco.get_state()
        print(f"Speed: {state.speed_percentage}%")
        print(f"Direction: {state.direction}")
        print(f"Functions: {state.functions}")

        # Subscribe to state changes
        def on_loco_state(state):
            print(f"Locomotive {state.address}: Speed {state.speed_percentage}%")

        loco.subscribe_state(on_loco_state)

RailCom Support
===============

Read back locomotive decoder data with RailCom (firmware 1.29+ required):

.. code-block:: python

    async with await Z21Station.connect("192.168.0.111") as station:
        loco = await Loco.control(station, address=3)

        # Request RailCom data
        try:
            railcom_data = await loco.get_railcom_data()
            print(f"Speed: {railcom_data.speed}")
            print(f"Load: {railcom_data.load}")
        except asyncio.TimeoutError:
            print("No RailCom data (decoder may not support RailCom)")

        # Subscribe to RailCom broadcasts
        await station.enable_railcom_broadcasts(all_locos=False)

        def on_railcom(data):
            print(f"Locomotive {data.loco_address}: Speed {data.speed}")

        loco.subscribe_railcom(on_railcom)

Error Handling
==============

Handle common errors:

.. code-block:: python

    try:
        async with await Z21Station.connect("192.168.0.111") as station:
            serial = await station.get_serial_number()
    except ConnectionError as e:
        print(f"Failed to connect: {e}")
    except asyncio.TimeoutError as e:
        print(f"Command timed out: {e}")
    except ValueError as e:
        print(f"Invalid response: {e}")

Next Steps
==========

- See :doc:`examples` for complete working examples
- Review the :doc:`api` for detailed API documentation
- Check the `GitHub repository <https://github.com/botmonster/z21aio>`_ for issues and discussions
