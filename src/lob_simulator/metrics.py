"""Execution quality metrics."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .simulation import ExecutionResult
from .types import Side


@dataclass(frozen=True)
class ExecutionMetrics:
    implementation_shortfall: float
    slippage_bps: float
    fill_rate: float
    is_complete_fill: bool
    time_to_fill: float | None
    avg_fill_price: float | None
    arrival_mid_price: float


def compute_metrics(result: ExecutionResult) -> ExecutionMetrics:
    IS_val = 0.0
    slippage_bps = 0.0
    if result.avg_fill_price is not None and result.arrival_mid_price > 0:
        sign = 1 if result.side == Side.BID else -1
        IS_val = sign * (result.avg_fill_price - result.arrival_mid_price)
        slippage_bps = IS_val / result.arrival_mid_price * 10_000
    return ExecutionMetrics(
        implementation_shortfall=IS_val,
        slippage_bps=slippage_bps,
        fill_rate=result.filled_qty / result.target_qty if result.target_qty > 0 else 0.0,
        is_complete_fill=result.filled_qty >= result.target_qty - 1e-9,
        time_to_fill=float(result.ticks_to_complete)
        if result.ticks_to_complete is not None
        else None,
        avg_fill_price=result.avg_fill_price,
        arrival_mid_price=result.arrival_mid_price,
    )


def aggregate_metrics(metrics_list: list[ExecutionMetrics]) -> dict:
    slippages = np.array([m.slippage_bps for m in metrics_list])
    ISs = np.array([m.implementation_shortfall for m in metrics_list])
    fill_rates = np.array([m.fill_rate for m in metrics_list])
    ttfs = [m.time_to_fill for m in metrics_list if m.time_to_fill is not None]
    return {
        "n_runs": len(metrics_list),
        "IS_mean": float(np.mean(ISs)),
        "IS_median": float(np.median(ISs)),
        "IS_p95": float(np.percentile(ISs, 95)),
        "slippage_bps_mean": float(np.mean(slippages)),
        "slippage_bps_median": float(np.median(slippages)),
        "slippage_bps_p25": float(np.percentile(slippages, 25)),
        "slippage_bps_p75": float(np.percentile(slippages, 75)),
        "slippage_bps_p95": float(np.percentile(slippages, 95)),
        "fill_rate_mean": float(np.mean(fill_rates)),
        "fill_prob": float(np.mean([m.is_complete_fill for m in metrics_list])),
        "ttf_mean": float(np.mean(ttfs)) if ttfs else None,
        "ttf_p95": float(np.percentile(ttfs, 95)) if ttfs else None,
    }