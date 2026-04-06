"""LOB Simulator — toy limit order book for market microstructure research."""

from __future__ import annotations

from .types import OrderStatus, OrderType, Side
from .state import LOBState, Order, PriceLevel, SimulatorSpec
from .invariants import BookInvariantError, check_book_invariants
from .engine import MatchingEngine, MatchResult, TradeRecord
from .strategies import ExecutionStrategy, Hybrid, PureLimit, PureMarket
from .simulation import ExecutionResult, SimulationError, TickLog, run_simulation
from .metrics import ExecutionMetrics, aggregate_metrics, compute_metrics
from .runner import STRATEGY_REGISTRY, SweepConfig, load_regimes, run_sweep

__all__ = [
    "MatchingEngine",
    "MatchResult",
    "TradeRecord",
    "ExecutionStrategy",
    "PureMarket",
    "PureLimit",
    "Hybrid",
    "ExecutionResult",
    "SimulationError",
    "TickLog",
    "run_simulation",
    "ExecutionMetrics",
    "compute_metrics",
    "aggregate_metrics",
    "SweepConfig",
    "run_sweep",
    "load_regimes",
    "STRATEGY_REGISTRY",
    "Side",
    "OrderType",
    "OrderStatus",
    "Order",
    "PriceLevel",
    "LOBState",
    "SimulatorSpec",
    "BookInvariantError",
    "check_book_invariants",
]
