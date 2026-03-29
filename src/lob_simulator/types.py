"""Enumerated types for the LOB simulator domain model."""

from __future__ import annotations

from enum import Enum, auto


class Side(Enum):
    """Which side of the book an order belongs to."""

    BID = auto()  # buy side
    ASK = auto()  # sell side


class OrderType(Enum):
    """Execution instruction for an order."""

    MARKET = auto()  # execute immediately at best available price
    LIMIT = auto()   # rest in book at specified price or better
    CANCEL = auto()  # remove an existing resting order


class OrderStatus(Enum):
    """Lifecycle state of an order."""

    ACTIVE = auto()     # resting in the book
    FILLED = auto()     # fully executed
    PARTIAL = auto()    # partially executed, remainder still active
    CANCELLED = auto()  # removed before fill
    EXPIRED = auto()    # TTL elapsed without fill
