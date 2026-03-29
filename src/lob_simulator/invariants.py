"""Structural invariant checks for the limit order book state."""

from __future__ import annotations

from lob_simulator.state import LOBState


class BookInvariantError(Exception):
    """Raised when the LOB violates a structural invariant."""


def check_book_invariants(state: LOBState) -> None:
    """
    Assert all structural invariants of a LOBState.

    Raises BookInvariantError (never AssertionError) on the FIRST violation
    found, with a descriptive message identifying which invariant failed
    and the offending values.

    Invariants checked (in order):
        1. No crossed book — best_bid < best_ask
        2. Bid levels strictly descending by price
        3. Ask levels strictly ascending by price
        4. All order quantities >= 0
        5. No ghost (empty) price levels
        6. Depth cap not exceeded
        7. Mid-price within [best_bid, best_ask]
    """
    _check_no_crossed_book(state)
    _check_bids_descending(state)
    _check_asks_ascending(state)
    _check_non_negative_quantities(state)
    _check_no_ghost_levels(state)
    _check_depth_cap(state)
    _check_mid_price_within_spread(state)


def _check_no_crossed_book(state: LOBState) -> None:
    """Invariant 1: best_bid must be strictly less than best_ask."""
    if state.best_bid is not None and state.best_ask is not None:
        if state.best_bid >= state.best_ask:
            raise BookInvariantError(
                f"Crossed book at t={state.timestamp}: "
                f"best_bid={state.best_bid} >= best_ask={state.best_ask}"
            )


def _check_bids_descending(state: LOBState) -> None:
    """Invariant 2: bid price levels must be strictly descending."""
    for i in range(1, len(state.bids)):
        if state.bids[i].price >= state.bids[i - 1].price:
            raise BookInvariantError(
                f"Bid levels not strictly descending at t={state.timestamp}: "
                f"level[{i - 1}].price={state.bids[i - 1].price} "
                f"<= level[{i}].price={state.bids[i].price}"
            )


def _check_asks_ascending(state: LOBState) -> None:
    """Invariant 3: ask price levels must be strictly ascending."""
    for i in range(1, len(state.asks)):
        if state.asks[i].price <= state.asks[i - 1].price:
            raise BookInvariantError(
                f"Ask levels not strictly ascending at t={state.timestamp}: "
                f"level[{i - 1}].price={state.asks[i - 1].price} "
                f">= level[{i}].price={state.asks[i].price}"
            )


def _check_non_negative_quantities(state: LOBState) -> None:
    """Invariant 4: all order quantities must be >= 0."""
    for side_label, levels in [("bid", state.bids), ("ask", state.asks)]:
        for lvl in levels:
            for order in lvl.orders:
                if order.quantity < 0:
                    raise BookInvariantError(
                        f"Negative quantity at t={state.timestamp}: "
                        f"{side_label} order_id={order.order_id} "
                        f"quantity={order.quantity} at price={lvl.price}"
                    )


def _check_no_ghost_levels(state: LOBState) -> None:
    """Invariant 5: no price level may have an empty orders list."""
    for side_label, levels in [("bid", state.bids), ("ask", state.asks)]:
        for lvl in levels:
            if lvl.is_empty:
                raise BookInvariantError(
                    f"Ghost level at t={state.timestamp}: "
                    f"{side_label} price={lvl.price} has no orders"
                )


def _check_depth_cap(state: LOBState) -> None:
    """Invariant 6: number of price levels per side must not exceed max_depth."""
    if len(state.bids) > state.max_depth:
        raise BookInvariantError(
            f"Depth cap exceeded at t={state.timestamp}: "
            f"bid levels={len(state.bids)} > max_depth={state.max_depth}"
        )
    if len(state.asks) > state.max_depth:
        raise BookInvariantError(
            f"Depth cap exceeded at t={state.timestamp}: "
            f"ask levels={len(state.asks)} > max_depth={state.max_depth}"
        )


def _check_mid_price_within_spread(state: LOBState) -> None:
    """Invariant 7: mid_price must lie within [best_bid, best_ask]."""
    if state.best_bid is not None and state.best_ask is not None:
        if state.mid_price < state.best_bid:
            raise BookInvariantError(
                f"Mid-price below best bid at t={state.timestamp}: "
                f"mid_price={state.mid_price} < best_bid={state.best_bid}"
            )
        if state.mid_price > state.best_ask:
            raise BookInvariantError(
                f"Mid-price above best ask at t={state.timestamp}: "
                f"mid_price={state.mid_price} > best_ask={state.best_ask}"
            )
