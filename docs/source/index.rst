====================================
z21aio - Z21 DCC Command Station API
====================================

.. image:: https://img.shields.io/badge/python-3.10+-blue.svg
   :alt: Python 3.10+

**z21aio** is an async Python library for controlling Roco/Fleischmann Z21 DCC command stations over UDP.

Features
========

- **Pure Python asyncio implementation** - No external dependencies, stdlib only
- **Control locomotives** - Speed, direction, and functions (F0-F31)
- **Track power management** - Turn track power on/off
- **System state monitoring** - Monitor voltage, current, and temperature
- **Multiple simultaneous connections** - Control multiple Z21 stations in parallel
- **RailCom support** - Read back locomotive data (firmware 1.29+)

Requirements
============

- Python 3.10 or higher
- Roco/Fleischmann Z21 command station

Installation
============

Install via pip::

    pip install z21aio

Or install from source::

    git clone https://github.com/botmonster/z21aio.git
    cd z21-dcc
    pip install -e .

Quick Start
===========

Here's a minimal example to connect to a Z21 station and control a locomotive::

    import asyncio
    from z21aio import Z21Station, Loco

    async def main():
        # Connect to Z21 station
        async with await Z21Station.connect("192.168.0.111") as station:
            # Get serial number
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

Contents
========

.. toctree::
   :maxdepth: 2

   quickstart
   api
   examples

Key Concepts
============

Z21Station
----------

The main entry point for communicating with a Z21 command station. Use the async context manager for proper resource management.

**Example:**

::

    async with await Z21Station.connect("192.168.0.111") as station:
        await station.voltage_on()

Loco
----

Control a locomotive on the track. Use the ``control()`` class method to take control of a locomotive by its address.

**Example:**

::

    loco = await Loco.control(station, address=3)
    await loco.drive(75.0)  # 75% forward

DccThrottleSteps
----------------

Specify the throttle resolution for a locomotive. Supported modes:

- ``DccThrottleSteps.STEPS_14`` - 14-step mode (legacy)
- ``DccThrottleSteps.STEPS_28`` - 28-step mode (common)
- ``DccThrottleSteps.STEPS_128`` - 128-step mode (default, smoothest)

**Example:**

::

    loco = await Loco.control(
        station,
        address=3,
        steps=DccThrottleSteps.STEPS_128
    )

Architecture
============

z21aio implements a layered protocol stack:

1. **Packet** - UDP frame serialization/deserialization
2. **XBusMessage** - X-Bus tunneling layer (encapsulated in UDP)
3. **Z21Station** - Connection management and packet routing
4. **Loco** - High-level locomotive control

All communication uses the official `Z21 LAN Protocol <https://github.com/botmonster/z21aio/blob/main/z21.md>`_ specification.

Protocol Reference
===================

For detailed protocol documentation, see the `Z21 LAN Protocol Specification <https://github.com/botmonster/z21aio/blob/main/z21.md>`_ included in the repository.

License
=======

MIT License - See LICENSE file for details.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
