"""Tests for metrics computation."""

from __future__ import annotations

from lob_simulator.engine import TradeRecord
from lob_simulator.metrics import aggregate_metrics, compute_metrics, ExecutionMetrics
from lob_simulator.simulation import ExecutionResult
from lob_simulator.state import SimulatorSpec
from lob_simulator.types import Side


def _result(avg_fill: float | None, target: float, filled: float, ttf: int | None = 5) -> ExecutionResult:
    return ExecutionResult(
        arrival_mid_price=100.0,
        target_qty=target,
        side=Side.BID,
        strategy_name="x",
        regime_name="regime_A",
        spec=SimulatorSpec(T=10, seed=1),
        filled_qty=filled,
        agent_trades=[],
        tick_log=[],
        avg_fill_price=avg_fill,
        ticks_to_complete=ttf,
    )


def test_compute_metrics_perfect_fill():
    m = compute_metrics(_result(avg_fill=100.0, target=5.0, filled=5.0))
    assert m.slippage_bps == 0.0
    assert m.fill_rate == 1.0
    assert m.is_complete_fill


def test_compute_metrics_above_mid():
    m = compute_metrics(_result(avg_fill=100.05, target=5.0, filled=5.0))
    assert m.implementation_shortfall > 0
    assert m.slippage_bps > 0


def test_aggregate_metrics_shape():
    metrics = [
        ExecutionMetrics(0.0, 0.0, 1.0, True, 5.0, 100.0, 100.0),
        ExecutionMetrics(0.05, 5.0, 1.0, True, 7.0, 100.05, 100.0),
    ]
    agg = aggregate_metrics(metrics)
    for k in [
        "n_runs", "IS_mean", "slippage_bps_mean", "slippage_bps_p25",
        "slippage_bps_p75", "fill_rate_mean", "fill_prob", "ttf_mean",
    ]:
        assert k in agg
    assert agg["n_runs"] == 2


def test_aggregate_metrics_ttf_excludes_none():
    metrics = [
        ExecutionMetrics(0.0, 0.0, 1.0, True, 5.0, 100.0, 100.0),
        ExecutionMetrics(0.0, 0.0, 0.5, False, None, 100.0, 100.0),
    ]
    agg = aggregate_metrics(metrics)
    assert agg["ttf_mean"] == 5.0