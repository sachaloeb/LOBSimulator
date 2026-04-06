"""Tests for execution strategies."""

from __future__ import annotations

import numpy as np

from lob_simulator.state import LOBState, Order, PriceLevel, SimulatorSpec
from lob_simulator.strategies import Hybrid, PureLimit, PureMarket
from lob_simulator.types import OrderType, Side


def _state() -> LOBState:
    bids = [PriceLevel(99.99, [Order(1, Side.BID, OrderType.LIMIT, 99.99, 1.0, 0)])]
    asks = [PriceLevel(100.01, [Order(2, Side.ASK, OrderType.LIMIT, 100.01, 1.0, 0)])]
    return LOBState(bids=bids, asks=asks, mid_price=100.0, timestamp=0, max_depth=3)


def test_pure_market_submits_on_first_tick():
    spec = SimulatorSpec(T=100, seed=1)
    rng = np.random.default_rng(1)
    ids = [-1]
    o = PureMarket().decide(_state(), 0, 5.0, 100, spec, rng, ids)
    assert o is not None
    assert o.order_type == OrderType.MARKET
    assert o.quantity == 5.0


def test_pure_market_skips_when_done():
    spec = SimulatorSpec(T=100, seed=1)
    rng = np.random.default_rng(1)
    assert PureMarket().decide(_state(), 0, 0.0, 100, spec, rng, [-1]) is None


def test_pure_limit_submits_limit_at_best_bid():
    spec = SimulatorSpec(T=100, seed=1)
    rng = np.random.default_rng(1)
    o = PureLimit().decide(_state(), 0, 5.0, 100, spec, rng, [-1])
    assert o.order_type == OrderType.LIMIT
    assert o.price == 99.99


def test_hybrid_switches_to_market_when_urgent():
    spec = SimulatorSpec(T=100, seed=1)
    rng = np.random.default_rng(1)
    # ticks_remaining = 10 = 0.1*T < 0.2*T → urgent
    o = Hybrid().decide(_state(), 90, 5.0, 10, spec, rng, [-1])
    assert o.order_type == OrderType.MARKET


def test_hybrid_last_tick_always_market():
    spec = SimulatorSpec(T=100, seed=1)
    rng = np.random.default_rng(1)
    o = Hybrid().decide(_state(), 99, 2.0, 1, spec, rng, [-1])
    assert o.order_type == OrderType.MARKET


def test_hybrid_passive_when_time_remains():
    spec = SimulatorSpec(T=100, seed=1)
    rng = np.random.default_rng(1)
    o = Hybrid().decide(_state(), 0, 5.0, 100, spec, rng, [-1])
    assert o.order_type == OrderType.LIMIT