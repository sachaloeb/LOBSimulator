"""Tick-by-tick simulation loop."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .engine import MatchingEngine, TradeRecord
from .invariants import BookInvariantError, check_book_invariants
from .state import LOBState, Order, SimulatorSpec
from .strategies import ExecutionStrategy
from .types import OrderType, Side


class SimulationError(Exception):
    """Raised when an invariant fails during a simulation tick."""


@dataclass
class TickLog:
    tick: int
    background_trades: list[TradeRecord]
    agent_order: Order | None
    agent_trades: list[TradeRecord]
    net_signed_flow: float
    mid_price_after: float


@dataclass
class ExecutionResult:
    arrival_mid_price: float
    target_qty: float
    side: Side
    strategy_name: str
    regime_name: str
    spec: SimulatorSpec
    filled_qty: float
    agent_trades: list[TradeRecord]
    tick_log: list[TickLog]
    avg_fill_price: float | None
    ticks_to_complete: int | None


def _is_agent_trade(t: TradeRecord) -> bool:
    return t.aggressor_id < 0 or t.passive_id < 0


def run_simulation(
    spec: SimulatorSpec,
    regime_params: dict,
    strategy: ExecutionStrategy,
    target_qty: float,
    side: Side = Side.BID,
    validate: bool = False,
) -> ExecutionResult:
    """Execute one simulation of spec.T ticks."""
    rng = np.random.default_rng(spec.seed)
    engine = MatchingEngine()
    state = engine.initialize_lob(regime_params, spec, rng)
    arrival_mid = state.mid_price

    next_order_id = [10_000]
    next_agent_order_id = [-1]
    agent_live_ids: set[int] = set()

    remaining = target_qty
    agent_trades_all: list[TradeRecord] = []
    tick_logs: list[TickLog] = []
    ticks_to_complete: int | None = None
    cumulative_filled = 0.0

    cancel_prob = regime_params["cancel_prob"]
    impact_coeff = regime_params["impact_coeff"]

    for t in range(spec.T):
        bg_trades: list[TradeRecord] = []
        agent_trades_tick: list[TradeRecord] = []
        net_flow = 0.0

        # Phase 1: generate background orders
        bg_orders = engine.generate_background_orders(
            state, rng, regime_params, t, next_order_id
        )

        # Phase 2: place background limit orders
        for o in bg_orders:
            if o.order_type == OrderType.LIMIT:
                state, trades = engine.place_limit_order(state, o, t)
                # collect agent fills from any crossing (unlikely for bg)
                for tr in trades:
                    if _is_agent_trade(tr):
                        agent_trades_tick.append(tr)
                    else:
                        bg_trades.append(tr)

        # Phase 3: execute background market orders
        for o in bg_orders:
            if o.order_type == OrderType.MARKET:
                mr = engine.execute_market_order(state, o, t)
                state = mr.updated_state
                for tr in mr.trades:
                    if _is_agent_trade(tr):
                        agent_trades_tick.append(tr)
                    else:
                        bg_trades.append(tr)
                signed = mr.total_filled if o.side == Side.BID else -mr.total_filled
                net_flow += signed

        # Before agent decision: cancel any live agent limit orders so the
        # strategy always starts with a clean slate (prevents over-ordering).
        if agent_live_ids:
            for live_id in list(agent_live_ids):
                for s_side in (Side.BID, Side.ASK):
                    state, ok = engine.cancel_order(state, live_id, s_side)
                    if ok:
                        break
            agent_live_ids.clear()

        # Phase 4: agent decision
        ticks_remaining = spec.T - t
        agent_order = strategy.decide(
            state, t, remaining, ticks_remaining, spec, rng, next_agent_order_id
        )
        if agent_order is not None:
            if agent_order.order_type == OrderType.MARKET:
                mr = engine.execute_market_order(state, agent_order, t)
                state = mr.updated_state
                for tr in mr.trades:
                    agent_trades_tick.append(tr)
                signed = (
                    mr.total_filled if agent_order.side == Side.BID else -mr.total_filled
                )
                net_flow += signed
            else:  # LIMIT
                state, trades = engine.place_limit_order(state, agent_order, t)
                for tr in trades:
                    agent_trades_tick.append(tr)
                # If the order (or remainder) rests in book, track it
                lvl = state.get_level_for_price(agent_order.side, agent_order.price)
                if lvl is not None:
                    for o in lvl.orders:
                        if o.order_id == agent_order.order_id:
                            agent_live_ids.add(agent_order.order_id)
                            break

        # Accumulate agent fills
        for tr in agent_trades_tick:
            agent_trades_all.append(tr)
            cumulative_filled += tr.quantity
            remaining -= tr.quantity
            # Remove filled agent orders from live set
        # Clean up filled limit IDs (any id no longer in book)
        still_live = set()
        for lvl in state.bids + state.asks:
            for o in lvl.orders:
                if o.order_id in agent_live_ids:
                    still_live.add(o.order_id)
        agent_live_ids = still_live

        if ticks_to_complete is None and cumulative_filled >= target_qty - 1e-9:
            ticks_to_complete = t

        # Phase 6: random cancellations (protect agent orders)
        state = engine.apply_random_cancellations(
            state, rng, cancel_prob, protected_ids=agent_live_ids
        )

        # Phase 7: price impact
        state = engine.apply_price_impact(state, net_flow, impact_coeff, spec.tick_size)

        # Phase 8: invariants
        if validate:
            try:
                check_book_invariants(state)
            except BookInvariantError as e:
                raise SimulationError(f"Invariant failed at tick {t}: {e}") from e

        tick_logs.append(
            TickLog(
                tick=t,
                background_trades=bg_trades,
                agent_order=agent_order,
                agent_trades=agent_trades_tick,
                net_signed_flow=net_flow,
                mid_price_after=state.mid_price,
            )
        )

        if remaining <= 1e-9:
            remaining = 0.0

    total_filled = sum(t.quantity for t in agent_trades_all)
    avg_fill = (
        sum(t.price * t.quantity for t in agent_trades_all) / total_filled
        if total_filled > 1e-12
        else None
    )
    return ExecutionResult(
        arrival_mid_price=arrival_mid,
        target_qty=target_qty,
        side=side,
        strategy_name=strategy.name,
        regime_name=spec.regime,
        spec=spec,
        filled_qty=total_filled,
        agent_trades=agent_trades_all,
        tick_log=tick_logs,
        avg_fill_price=avg_fill,
        ticks_to_complete=ticks_to_complete,
    )