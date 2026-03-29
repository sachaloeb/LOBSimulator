"""Tests for LOB structural invariant checks."""

from __future__ import annotations

import pytest

from src.lob_simulator.invariants import BookInvariantError, check_book_invariants
from src.lob_simulator.state import LOBState, Order, PriceLevel
from src.lob_simulator.types import OrderStatus, OrderType, Side


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_next_id = 0


def make_order(
    *,
    side: Side = Side.BID,
    price: float = 100.0,
    quantity: float = 1.0,
    timestamp: int = 0,
) -> Order:
    """Create an Order with auto-incrementing ID and sensible defaults."""
    global _next_id
    _next_id += 1
    return Order(
        order_id=_next_id,
        side=side,
        order_type=OrderType.LIMIT,
        price=price,
        quantity=quantity,
        timestamp=timestamp,
        status=OrderStatus.ACTIVE,
    )


def make_level(price: float, *, side: Side = Side.BID, n_orders: int = 1) -> PriceLevel:
    """Create a PriceLevel with *n_orders* unit-size orders."""
    return PriceLevel(
        price=price,
        orders=[make_order(side=side, price=price) for _ in range(n_orders)],
    )


def _valid_book() -> LOBState:
    """Construct a minimal, invariant-respecting LOBState."""
    return LOBState(
        bids=[make_level(100.00, side=Side.BID), make_level(99.99, side=Side.BID)],
        asks=[make_level(100.01, side=Side.ASK), make_level(100.02, side=Side.ASK)],
        mid_price=100.005,
        timestamp=0,
        max_depth=3,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBookInvariants:
    """Suite covering all 7 structural invariants + edge cases."""

    def test_valid_book_passes(self) -> None:
        """A correctly formed book raises nothing."""
        check_book_invariants(_valid_book())

    def test_crossed_book_raises(self) -> None:
        """best_bid >= best_ask must raise BookInvariantError."""
        state = LOBState(
            bids=[make_level(100.05, side=Side.BID)],
            asks=[make_level(100.03, side=Side.ASK)],
            mid_price=100.04,
            timestamp=42,
            max_depth=3,
        )
        with pytest.raises(BookInvariantError, match="Crossed book"):
            check_book_invariants(state)

    def test_misordered_bids_raises(self) -> None:
        """Bid levels not strictly descending by price must raise."""
        state = LOBState(
            bids=[make_level(99.99, side=Side.BID), make_level(100.00, side=Side.BID)],
            asks=[make_level(100.01, side=Side.ASK)],
            mid_price=100.00,
            timestamp=1,
            max_depth=3,
        )
        with pytest.raises(BookInvariantError, match="not strictly descending"):
            check_book_invariants(state)

    def test_misordered_asks_raises(self) -> None:
        """Ask levels not strictly ascending by price must raise."""
        state = LOBState(
            bids=[make_level(99.99, side=Side.BID)],
            asks=[make_level(100.02, side=Side.ASK), make_level(100.01, side=Side.ASK)],
            mid_price=100.005,
            timestamp=2,
            max_depth=3,
        )
        with pytest.raises(BookInvariantError, match="not strictly ascending"):
            check_book_invariants(state)

    def test_negative_quantity_raises(self) -> None:
        """Any order with quantity < 0 must raise."""
        bad_order = make_order(side=Side.BID, price=100.00, quantity=-5.0)
        state = LOBState(
            bids=[PriceLevel(price=100.00, orders=[bad_order])],
            asks=[make_level(100.01, side=Side.ASK)],
            mid_price=100.005,
            timestamp=3,
            max_depth=3,
        )
        with pytest.raises(BookInvariantError, match="Negative quantity"):
            check_book_invariants(state)

    def test_ghost_level_raises(self) -> None:
        """A PriceLevel with an empty orders list must raise."""
        state = LOBState(
            bids=[PriceLevel(price=100.00, orders=[])],
            asks=[make_level(100.01, side=Side.ASK)],
            mid_price=100.005,
            timestamp=4,
            max_depth=3,
        )
        with pytest.raises(BookInvariantError, match="Ghost level"):
            check_book_invariants(state)

    def test_depth_cap_violation_raises(self) -> None:
        """More price levels than max_depth must raise."""
        state = LOBState(
            bids=[
                make_level(100.00, side=Side.BID),
                make_level(99.99, side=Side.BID),
                make_level(99.98, side=Side.BID),
                make_level(99.97, side=Side.BID),
            ],
            asks=[make_level(100.01, side=Side.ASK)],
            mid_price=100.005,
            timestamp=5,
            max_depth=3,
        )
        with pytest.raises(BookInvariantError, match="Depth cap exceeded"):
            check_book_invariants(state)

    def test_mid_price_outside_spread_raises(self) -> None:
        """mid_price outside [best_bid, best_ask] must raise."""
        state = LOBState(
            bids=[make_level(100.00, side=Side.BID)],
            asks=[make_level(100.02, side=Side.ASK)],
            mid_price=100.05,  # above best_ask
            timestamp=6,
            max_depth=3,
        )
        with pytest.raises(BookInvariantError, match="Mid-price above best ask"):
            check_book_invariants(state)

        state_low = LOBState(
            bids=[make_level(100.00, side=Side.BID)],
            asks=[make_level(100.02, side=Side.ASK)],
            mid_price=99.95,  # below best_bid
            timestamp=7,
            max_depth=3,
        )
        with pytest.raises(BookInvariantError, match="Mid-price below best bid"):
            check_book_invariants(state_low)

    def test_empty_book_passes(self) -> None:
        """Both sides empty — vacuously valid, no error."""
        state = LOBState(
            bids=[],
            asks=[],
            mid_price=100.0,
            timestamp=0,
            max_depth=3,
        )
        check_book_invariants(state)
