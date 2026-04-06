"""Matching engine: stateless operations over LOBState."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field

import numpy as np

from .state import LOBState, Order, PriceLevel, SimulatorSpec
from .types import OrderStatus, OrderType, Side


def _round_to_tick(price: float, tick_size: float) -> float:
    """Round price to nearest tick_size."""
    return round(round(price / tick_size) * tick_size, 10)


@dataclass
class TradeRecord:
    """A single matched trade (fill)."""

    timestamp: int
    price: float
    quantity: float
    aggressor_side: Side
    aggressor_id: int
    passive_id: int


@dataclass
class MatchResult:
    """Output of executing a market order against the book."""

    updated_state: LOBState
    trades: list[TradeRecord] = field(default_factory=list)
    unfilled_qty: float = 0.0
    vwap: float | None = None
    total_filled: float = 0.0


class MatchingEngine:
    """Stateless engine: all methods take and return LOBState (no mutation)."""

    # ── Matching ──────────────────────────────────────────────────────────

    def execute_market_order(
        self,
        state: LOBState,
        order: Order,
        timestamp: int,
    ) -> MatchResult:
        """Execute market order by sweeping the opposite side (FIFO)."""
        opp_side = Side.ASK if order.side == Side.BID else Side.BID
        src_levels = state.asks if opp_side == Side.ASK else state.bids
        opp_levels = list(src_levels)  # shallow; copy levels only when modified

        remaining = order.quantity
        trades: list[TradeRecord] = []

        # Iterate levels in natural order (ascending for asks, descending for bids)
        i = 0
        while i < len(opp_levels) and remaining > 1e-12:
            # Copy this level (we're about to modify it)
            old_lvl = opp_levels[i]
            lvl = PriceLevel(
                price=old_lvl.price,
                orders=[
                    Order(o.order_id, o.side, o.order_type, o.price, o.quantity, o.timestamp, o.status)
                    for o in old_lvl.orders
                ],
            )
            opp_levels[i] = lvl
            # FIFO: consume from front
            while lvl.orders and remaining > 1e-12:
                resting = lvl.orders[0]
                trade_qty = min(resting.quantity, remaining)
                trades.append(
                    TradeRecord(
                        timestamp=timestamp,
                        price=lvl.price,
                        quantity=trade_qty,
                        aggressor_side=order.side,
                        aggressor_id=order.order_id,
                        passive_id=resting.order_id,
                    )
                )
                resting.quantity -= trade_qty
                remaining -= trade_qty
                if resting.quantity <= 1e-12:
                    resting.status = OrderStatus.FILLED
                    lvl.orders.pop(0)
                else:
                    resting.status = OrderStatus.PARTIAL
            if not lvl.orders:
                opp_levels.pop(i)
            else:
                i += 1

        new_state = state.with_updated_side(opp_side, opp_levels)
        total_filled = order.quantity - remaining
        vwap = (
            sum(t.price * t.quantity for t in trades) / total_filled
            if total_filled > 1e-12
            else None
        )
        return MatchResult(
            updated_state=new_state,
            trades=trades,
            unfilled_qty=max(remaining, 0.0),
            vwap=vwap,
            total_filled=total_filled,
        )

    # ── Placement ─────────────────────────────────────────────────────────

    def place_limit_order(
        self,
        state: LOBState,
        order: Order,
        timestamp: int,
    ) -> tuple[LOBState, list[TradeRecord]]:
        """
        Place a limit order. If it crosses, it matches against resting orders
        at the passive price. Returns (new_state, trades_from_crossing).
        """
        trades: list[TradeRecord] = []
        working = order

        # Step 1: check crossing
        if order.side == Side.BID and state.best_ask is not None and order.price is not None and order.price >= state.best_ask - 1e-12:
            mr = self.execute_market_order(
                state,
                Order(
                    order_id=order.order_id,
                    side=Side.BID,
                    order_type=OrderType.MARKET,
                    price=None,
                    quantity=order.quantity,
                    timestamp=timestamp,
                ),
                timestamp,
            )
            trades.extend(mr.trades)
            state = mr.updated_state
            if mr.unfilled_qty <= 1e-12:
                return state, trades
            working = Order(
                order_id=order.order_id,
                side=order.side,
                order_type=OrderType.LIMIT,
                price=order.price,
                quantity=mr.unfilled_qty,
                timestamp=timestamp,
            )
        elif order.side == Side.ASK and state.best_bid is not None and order.price is not None and order.price <= state.best_bid + 1e-12:
            mr = self.execute_market_order(
                state,
                Order(
                    order_id=order.order_id,
                    side=Side.ASK,
                    order_type=OrderType.MARKET,
                    price=None,
                    quantity=order.quantity,
                    timestamp=timestamp,
                ),
                timestamp,
            )
            trades.extend(mr.trades)
            state = mr.updated_state
            if mr.unfilled_qty <= 1e-12:
                return state, trades
            working = Order(
                order_id=order.order_id,
                side=order.side,
                order_type=OrderType.LIMIT,
                price=order.price,
                quantity=mr.unfilled_qty,
                timestamp=timestamp,
            )

        # Step 2: insert into book (shallow copy list; copy only touched level)
        side = working.side
        src = state.bids if side == Side.BID else state.asks
        levels = list(src)
        existing_idx = None
        for idx, lvl in enumerate(levels):
            if abs(lvl.price - working.price) < 1e-9:
                existing_idx = idx
                break
        if existing_idx is not None:
            old_lvl = levels[existing_idx]
            levels[existing_idx] = PriceLevel(
                price=old_lvl.price,
                orders=old_lvl.orders + [working],
            )
        else:
            new_lvl = PriceLevel(price=working.price, orders=[working])
            # insertion: bids descending, asks ascending
            inserted = False
            for idx, lvl in enumerate(levels):
                if side == Side.BID and new_lvl.price > lvl.price:
                    levels.insert(idx, new_lvl)
                    inserted = True
                    break
                if side == Side.ASK and new_lvl.price < lvl.price:
                    levels.insert(idx, new_lvl)
                    inserted = True
                    break
            if not inserted:
                levels.append(new_lvl)

        # Step 3: enforce depth cap
        while len(levels) > state.max_depth:
            dropped = levels.pop()  # worst-priced is last
            for o in dropped.orders:
                o.status = OrderStatus.EXPIRED

        return state.with_updated_side(side, levels), trades

    # ── Cancellation ──────────────────────────────────────────────────────

    def cancel_order(
        self,
        state: LOBState,
        order_id: int,
        side: Side,
    ) -> tuple[LOBState, bool]:
        """Find and remove order_id from the specified side."""
        src = state.bids if side == Side.BID else state.asks
        for i, lvl in enumerate(src):
            for j, o in enumerate(lvl.orders):
                if o.order_id == order_id:
                    levels = list(src)
                    new_orders = [oo for k, oo in enumerate(lvl.orders) if k != j]
                    if new_orders:
                        levels[i] = PriceLevel(price=lvl.price, orders=new_orders)
                    else:
                        levels.pop(i)
                    return state.with_updated_side(side, levels), True
        return state, False

    def apply_random_cancellations(
        self,
        state: LOBState,
        rng: np.random.Generator,
        cancel_prob: float,
        protected_ids: set[int] | None = None,
    ) -> LOBState:
        """Each non-protected resting order cancels independently."""
        protected = protected_ids or set()
        new_state = state
        for side in (Side.BID, Side.ASK):
            src = new_state.bids if side == Side.BID else new_state.asks
            new_levels: list[PriceLevel] = []
            changed = False
            for lvl in src:
                kept_orders = []
                level_changed = False
                for o in lvl.orders:
                    if o.order_id in protected:
                        kept_orders.append(o)
                    elif rng.random() < cancel_prob:
                        level_changed = True
                        changed = True
                    else:
                        kept_orders.append(o)
                if level_changed:
                    if kept_orders:
                        new_levels.append(PriceLevel(price=lvl.price, orders=kept_orders))
                else:
                    new_levels.append(lvl)
            if changed:
                new_state = new_state.with_updated_side(side, new_levels)
        return new_state

    # ── Price impact ──────────────────────────────────────────────────────

    def apply_price_impact(
        self,
        state: LOBState,
        net_signed_flow: float,
        impact_coeff: float,
        tick_size: float,
    ) -> LOBState:
        """Shift mid_price and increment timestamp. Rests unchanged."""
        new_mid = state.mid_price + impact_coeff * net_signed_flow
        new_mid = _round_to_tick(new_mid, tick_size)
        # Clamp within current best bid/ask so invariant 7 holds
        if state.best_bid is not None and new_mid < state.best_bid:
            new_mid = state.best_bid
        if state.best_ask is not None and new_mid > state.best_ask:
            new_mid = state.best_ask
        return LOBState(
            bids=state.bids,
            asks=state.asks,
            mid_price=new_mid,
            timestamp=state.timestamp + 1,
            max_depth=state.max_depth,
        )

    # ── Initialization ────────────────────────────────────────────────────

    def initialize_lob(
        self,
        regime_params: dict,
        spec: SimulatorSpec,
        rng: np.random.Generator,
    ) -> LOBState:
        """Build a fresh LOBState at t=0."""
        import math
        initial_mid = 100.0
        half_spread = regime_params["spread_ticks"] * spec.tick_size / 2
        best_bid = math.floor((initial_mid - half_spread) / spec.tick_size) * spec.tick_size
        best_ask = math.ceil((initial_mid + half_spread) / spec.tick_size) * spec.tick_size
        if best_bid >= best_ask:
            best_bid = initial_mid - spec.tick_size
            best_ask = initial_mid + spec.tick_size
        best_bid = round(best_bid, 10)
        best_ask = round(best_ask, 10)
        vol = regime_params["vol_per_order"]

        next_id = 1
        bids: list[PriceLevel] = []
        asks: list[PriceLevel] = []
        for i in range(spec.max_depth):
            bp = _round_to_tick(best_bid - i * spec.tick_size, spec.tick_size)
            ap = _round_to_tick(best_ask + i * spec.tick_size, spec.tick_size)
            b_orders = []
            a_orders = []
            for _ in range(3):
                b_orders.append(
                    Order(
                        order_id=next_id,
                        side=Side.BID,
                        order_type=OrderType.LIMIT,
                        price=bp,
                        quantity=vol,
                        timestamp=0,
                    )
                )
                next_id += 1
                a_orders.append(
                    Order(
                        order_id=next_id,
                        side=Side.ASK,
                        order_type=OrderType.LIMIT,
                        price=ap,
                        quantity=vol,
                        timestamp=0,
                    )
                )
                next_id += 1
            bids.append(PriceLevel(price=bp, orders=b_orders))
            asks.append(PriceLevel(price=ap, orders=a_orders))

        return LOBState(
            bids=bids,
            asks=asks,
            mid_price=initial_mid,
            timestamp=0,
            max_depth=spec.max_depth,
        )

    # ── Background order generation ───────────────────────────────────────

    def generate_background_orders(
        self,
        state: LOBState,
        rng: np.random.Generator,
        regime_params: dict,
        tick: int,
        next_order_id: list[int],
    ) -> list[Order]:
        """Sample background limit bids, limit asks, and market orders."""
        vol = regime_params["vol_per_order"]
        tick_size = 0.01  # tick_size not on state; engine caller uses spec tick
        # Use state.max_depth as spread of price sampling
        max_depth = state.max_depth
        orders: list[Order] = []

        n_bids = int(rng.poisson(regime_params["lambda_bid"]))
        n_asks = int(rng.poisson(regime_params["lambda_ask"]))
        n_mkt = int(rng.poisson(regime_params["lambda_market"]))

        def sample_qty() -> float:
            q = rng.exponential(vol)
            return float(np.clip(q, 0.1, 10 * vol))

        for _ in range(n_bids):
            offset = int(rng.integers(1, max_depth + 1))
            price = _round_to_tick(state.mid_price - offset * tick_size, tick_size)
            oid = next_order_id[0]
            next_order_id[0] += 1
            orders.append(
                Order(
                    order_id=oid,
                    side=Side.BID,
                    order_type=OrderType.LIMIT,
                    price=price,
                    quantity=sample_qty(),
                    timestamp=tick,
                )
            )
        for _ in range(n_asks):
            offset = int(rng.integers(1, max_depth + 1))
            price = _round_to_tick(state.mid_price + offset * tick_size, tick_size)
            oid = next_order_id[0]
            next_order_id[0] += 1
            orders.append(
                Order(
                    order_id=oid,
                    side=Side.ASK,
                    order_type=OrderType.LIMIT,
                    price=price,
                    quantity=sample_qty(),
                    timestamp=tick,
                )
            )
        for _ in range(n_mkt):
            side = Side.BID if rng.random() < 0.5 else Side.ASK
            oid = next_order_id[0]
            next_order_id[0] += 1
            orders.append(
                Order(
                    order_id=oid,
                    side=side,
                    order_type=OrderType.MARKET,
                    price=None,
                    quantity=sample_qty(),
                    timestamp=tick,
                )
            )
        return orders