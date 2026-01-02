==================
API Reference
==================

Core Classes
============

Z21Station
----------

.. autoclass:: z21aio.Z21Station
   :members:
   :special-members: __aenter__, __aexit__
   :show-inheritance:

Loco
----

.. autoclass:: z21aio.Loco
   :members:
   :show-inheritance:

Message Handling
================

Packet
------

.. autoclass:: z21aio.Packet
   :members:
   :show-inheritance:
   :no-index:

XBusMessage
-----------

.. autoclass:: z21aio.XBusMessage
   :members:
   :show-inheritance:
   :no-index:

Data Types
==========

.. autoclass:: z21aio.SystemState
   :members:
   :show-inheritance:

.. autoclass:: z21aio.LocoState
   :members:
   :show-inheritance:

.. autoclass:: z21aio.RailComData
   :members:
   :show-inheritance:
   :no-index:

.. autoclass:: z21aio.RailComOptions
   :members:
   :show-inheritance:

.. autoclass:: z21aio.DccThrottleSteps
   :members:
   :show-inheritance:
   :no-index:

.. autoclass:: z21aio.FunctionAction
   :members:
   :show-inheritance:
   :no-index:

Low-Level Details
==================

Constants and Protocol Headers
-------------------------------

Protocol constants, message headers, and header names are defined in the low-level modules.

The ``z21aio.headers`` module contains:
- LAN packet header constants
- X-Bus message header constants
- Helper functions for header name lookup

The ``z21aio.messages`` module contains:
- Broadcast flag constants
- LAN command constants
- XBusMessage class for low-level protocol messages
