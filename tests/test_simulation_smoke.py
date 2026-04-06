"""Smoke tests for the simulation loop."""

from __future__ import annotations

from lob_simulator.runner import load_regimes
from lob_simulator.simulation import run_simulation
from lob_simulator.state import SimulatorSpec
from lob_simulator.strategies import PureMarket


def test_run_simulation_completes():
    regimes = load_regimes()
    spec = SimulatorSpec(T=50, seed=1, regime="regime_A")
    result = run_simulation(spec, regimes["regime_A"], PureMarket(), target_qty=2.0, validate=True)
    assert result.filled_qty >= 0


def test_run_simulation_deterministic():
    regimes = load_regimes()
    spec = SimulatorSpec(T=50, seed=7, regime="regime_A")
    r1 = run_simulation(spec, regimes["regime_A"], PureMarket(), target_qty=2.0)
    r2 = run_simulation(spec, regimes["regime_A"], PureMarket(), target_qty=2.0)
    assert r1.avg_fill_price == r2.avg_fill_price
    assert r1.filled_qty == r2.filled_qty