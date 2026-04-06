"""Execution strategies for the agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

import numpy as np

from .state import LOBState, Order, SimulatorSpec
from .types import OrderType, Side


@runtime_checkable
class ExecutionStrategy(Protocol):
    """Strategy interface for agent order execution."""

    name: str

    def decide(
        self,
        state: LOBState,
        tick: int,
        remaining_qty: float,
        ticks_remaining: int,
        spec: SimulatorSpec,
        rng: np.random.Generator,
        next_agent_order_id: list[int],
    ) -> Order | None: ...


@dataclass
class PureMarket:
    """Submits a market buy for all remaining quantity each tick it has qty."""

    name: str = field(default="pure_market", init=False)

    def decide(
        self,
        state: LOBState,
        tick: int,
        remaining_qty: float,
        ticks_remaining: int,
        spec: SimulatorSpec,
        rng: np.random.Generator,
        next_agent_order_id: list[int],
    ) -> Order | None:
        if remaining_qty <= 0:
            return None
        oid = next_agent_order_id[0]
        next_agent_order_id[0] -= 1
        return Order(
            order_id=oid,
            side=Side.BID,
            order_type=OrderType.MARKET,
            price=None,
            quantity=remaining_qty,
            timestamp=tick,
        )


@dataclass
class PureLimit:
    """Posts a limit buy at current best_bid each tick (never chases)."""

    name: str = field(default="pure_limit", init=False)

    def decide(
        self,
        state: LOBState,
        tick: int,
        remaining_qty: float,
        ticks_remaining: int,
        spec: SimulatorSpec,
        rng: np.random.Generator,
        next_agent_order_id: list[int],
    ) -> Order | None:
        if remaining_qty <= 0:
            return None
        bid_price = (
            state.best_bid
            if state.best_bid is not None
            else round(state.mid_price - spec.tick_size, 8)
        )
        oid = next_agent_order_id[0]
        next_agent_order_id[0] -= 1
        return Order(
            order_id=oid,
            side=Side.BID,
            order_type=OrderType.LIMIT,
            price=bid_price,
            quantity=remaining_qty,
            timestamp=tick,
        )


@dataclass
class Hybrid:
    """Passive limit while time remains; flips to market when urgent."""

    urgency_threshold: float = 0.20
    name: str = field(default="hybrid", init=False)

    def decide(
        self,
        state: LOBState,
        tick: int,
        remaining_qty: float,
        ticks_remaining: int,
        spec: SimulatorSpec,
        rng: np.random.Generator,
        next_agent_order_id: list[int],
    ) -> Order | None:
        if remaining_qty <= 0:
            return None
        oid = next_agent_order_id[0]
        next_agent_order_id[0] -= 1
        urgent = (ticks_remaining <= self.urgency_threshold * spec.T) or (
            ticks_remaining == 1
        )
        if urgent:
            return Order(
                order_id=oid,
                side=Side.BID,
                order_type=OrderType.MARKET,
                price=None,
                quantity=remaining_qty,
                timestamp=tick,
            )
        bid_price = (
            state.best_bid
            if state.best_bid is not None
            else round(state.mid_price - spec.tick_size, 8)
        )
        return Order(
            order_id=oid,
            side=Side.BID,
            order_type=OrderType.LIMIT,
            price=bid_price,
            quantity=remaining_qty,
            timestamp=tick,
        )