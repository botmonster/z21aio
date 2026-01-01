# z21aio

Async Python library for Z21 DCC command station communication using UDP protocol.

## Features

- Pure Python asyncio implementation
- Control locomotives (speed, direction, functions F0-F31)
- Track power control (on/off)
- System state monitoring
- Support for multiple simultaneous Z21 connections
- No external dependencies (stdlib only)

## Requirements

- Python 3.10+
- Z21 command station (Roco/Fleischmann)

## Installation

```bash
pip install z21aio
```

Or install from source:

```bash
git clone https://github.com/botmonster/z21aio.git
cd z21-dcc
pip install -e .
```

## Quick Start

```python
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
```

## Multi-Station Support

Connect to multiple Z21 stations simultaneously:

```python
async def multi_station():
    async with await Z21Station.connect("192.168.0.111") as station1, \
               await Z21Station.connect("192.168.0.112") as station2:
        loco1 = await Loco.control(station1, address=3)
        loco2 = await Loco.control(station2, address=5)

        await loco1.drive(50.0)
        await loco2.drive(30.0)
```

## API Reference

### Z21Station

Main class for communicating with a Z21 command station.

```python
# Connect to station
station = await Z21Station.connect(host, port=21105, timeout=2.0)

# Track power control
await station.voltage_on()
await station.voltage_off()

# Get station info
serial = await station.get_serial_number()

# Subscribe to system state updates
station.subscribe_system_state(callback, freq_hz=1.0)

# Clean disconnect
await station.logout()
await station.close()
```

### Loco

Control a locomotive on the track.

```python
# Get control of locomotive
loco = await Loco.control(station, address=3)

# Speed control (-100 to 100, negative = reverse)
await loco.drive(50.0)   # 50% forward
await loco.drive(-30.0)  # 30% reverse
await loco.stop()        # Normal stop (with braking)
await loco.halt()        # Emergency stop

# Function control (F0-F31)
await loco.set_headlights(True)  # F0
await loco.function_on(2)        # F2 on
await loco.function_off(2)       # F2 off
await loco.function_toggle(3)    # Toggle F3

# Get current state
state = await loco.get_state()
print(f"Speed: {state.speed_percentage}%")
```

### DccThrottleSteps

Throttle step modes for locomotive control.

```python
from z21aio import DccThrottleSteps

# Available modes
DccThrottleSteps.STEPS_14   # 14-step mode
DccThrottleSteps.STEPS_28   # 28-step mode
DccThrottleSteps.STEPS_128  # 128-step mode (default)
```

## Examples

See the `examples/` directory for complete working examples:

| File                                          | Description                                             |
| --------------------------------------------- | ------------------------------------------------------- |
| [basic.py](examples/basic.py)                 | Quick start - connect, power on, drive locomotive       |
| [multi_station.py](examples/multi_station.py) | Connect to multiple Z21 stations simultaneously         |
| [speed.py](examples/speed.py)                 | Speed control - forward, reverse, stop, emergency halt  |
| [functions.py](examples/functions.py)         | Locomotive function control (F0-F31)                    |
| [monitor.py](examples/monitor.py)             | System state monitoring (current, voltage, temperature) |
| [loco_state.py](examples/loco_state.py)       | Get and subscribe to locomotive state updates           |

## Protocol Documentation

This library implements the Z21 LAN Protocol as documented by Roco/Fleischmann.

## License

MIT License - see [LICENSE](LICENSE) file for details.
