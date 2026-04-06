"""Tests for the matching engine."""

from __future__ import annotations

from copy import deepcopy

import numpy as np
import pytest

from lob_simulator.engine import MatchingEngine
from lob_simulator.invariants import check_book_invariants
from lob_simulator.state import LOBState, Order, PriceLevel, SimulatorSpec
from lob_simulator.types import OrderStatus, OrderType, Side


def make_state() -> LOBState:
    bids = [
        PriceLevel(
            price=99.99,
            orders=[
                Order(1, Side.BID, OrderType.LIMIT, 99.99, 2.0, 0),
                Order(2, Side.BID, OrderType.LIMIT, 99.99, 3.0, 0),
            ],
        ),
        PriceLevel(
            price=99.98,
            orders=[Order(3, Side.BID, OrderType.LIMIT, 99.98, 5.0, 0)],
        ),
    ]
    asks = [
        PriceLevel(
            price=100.01,
            orders=[
                Order(4, Side.ASK, OrderType.LIMIT, 100.01, 2.0, 0),
                Order(5, Side.ASK, OrderType.LIMIT, 100.01, 2.0, 0),
            ],
        ),
        PriceLevel(
            price=100.02,
            orders=[Order(6, Side.ASK, OrderType.LIMIT, 100.02, 3.0, 0)],
        ),
    ]
    return LOBState(bids=bids, asks=asks, mid_price=100.0, timestamp=0, max_depth=3)


def test_market_buy_full_fill():
    eng = MatchingEngine()
    s = make_state()
    o = Order(100, Side.BID, OrderType.MARKET, None, 3.0, 0)
    mr = eng.execute_market_order(s, o, 0)
    assert mr.unfilled_qty == 0
    assert mr.total_filled == pytest.approx(3.0)
    assert mr.vwap == pytest.approx(100.01)
    assert len(mr.trades) == 2


def test_market_buy_partial_fill():
    eng = MatchingEngine()
    s = make_state()
    o = Order(100, Side.BID, OrderType.MARKET, None, 100.0, 0)
    mr = eng.execute_market_order(s, o, 0)
    assert mr.unfilled_qty > 0
    assert mr.total_filled == pytest.approx(7.0)


def test_market_buy_empty_book():
    eng = MatchingEngine()
    s = LOBState(bids=[], asks=[], mid_price=100.0, timestamp=0, max_depth=3)
    o = Order(100, Side.BID, OrderType.MARKET, None, 5.0, 0)
    mr = eng.execute_market_order(s, o, 0)
    assert mr.unfilled_qty == 5.0
    assert mr.trades == []


def test_limit_order_placement_bid():
    eng = MatchingEngine()
    s = make_state()
    o = Order(200, Side.BID, OrderType.LIMIT, 99.99, 1.0, 0)
    new_s, trades = eng.place_limit_order(s, o, 0)
    assert trades == []
    lvl = new_s.get_level_for_price(Side.BID, 99.99)
    assert lvl.orders[-1].order_id == 200  # FIFO: appended to back


def test_limit_order_depth_cap():
    eng = MatchingEngine()
    s = make_state()  # bids already has 2 levels, max_depth=3
    # Add a level below, then another below that to force drop
    o1 = Order(201, Side.BID, OrderType.LIMIT, 99.97, 1.0, 0)
    s, _ = eng.place_limit_order(s, o1, 0)
    o2 = Order(202, Side.BID, OrderType.LIMIT, 99.96, 1.0, 0)
    s, _ = eng.place_limit_order(s, o2, 0)
    assert len(s.bids) == 3
    assert s.bids[-1].price == pytest.approx(99.97)  # 99.96 dropped (worst)
    # order 202 should be EXPIRED - can't easily inspect; just ensure not in book
    assert s.get_level_for_price(Side.BID, 99.96) is None


def test_cancel_order_found():
    eng = MatchingEngine()
    s = make_state()
    new_s, ok = eng.cancel_order(s, 1, Side.BID)
    assert ok
    lvl = new_s.get_level_for_price(Side.BID, 99.99)
    assert all(o.order_id != 1 for o in lvl.orders)


def test_cancel_order_not_found():
    eng = MatchingEngine()
    s = make_state()
    snap = deepcopy(s)
    new_s, ok = eng.cancel_order(s, 9999, Side.BID)
    assert not ok
    assert len(new_s.bids) == len(snap.bids)


def test_price_impact_shifts_mid():
    eng = MatchingEngine()
    s = make_state()
    new_s = eng.apply_price_impact(s, net_signed_flow=1.0, impact_coeff=0.01, tick_size=0.01)
    # impact = 0.01 shift; clamp within [99.99, 100.01] → 100.01
    assert new_s.mid_price == pytest.approx(100.01)
    assert new_s.timestamp == 1


def test_engine_never_mutates_state():
    eng = MatchingEngine()
    s = make_state()
    snap = deepcopy(s)
    eng.execute_market_order(s, Order(100, Side.BID, OrderType.MARKET, None, 3.0, 0), 0)
    eng.place_limit_order(s, Order(101, Side.BID, OrderType.LIMIT, 99.97, 1.0, 0), 0)
    eng.cancel_order(s, 1, Side.BID)
    eng.apply_price_impact(s, 1.0, 0.001, 0.01)
    assert s.mid_price == snap.mid_price
    assert len(s.bids) == len(snap.bids)
    assert s.bids[0].orders[0].quantity == snap.bids[0].orders[0].quantity


def test_initialize_lob_valid():
    eng = MatchingEngine()
    spec = SimulatorSpec(T=10, seed=1, regime="regime_A")
    regime = {
        "spread_ticks": 1,
        "lambda_bid": 5.0,
        "lambda_ask": 5.0,
        "lambda_market": 1.0,
        "impact_coeff": 0.001,
        "cancel_prob": 0.05,
        "vol_per_order": 1.0,
    }
    rng = np.random.default_rng(1)
    state = eng.initialize_lob(regime, spec, rng)
    check_book_invariants(state)
    assert len(state.bids) == spec.max_depth
    assert len(state.asks) == spec.max_depth
    assert state.mid_price == 100.0