# Architecture

## Overview

The LOB Simulator is a time-sliced, single-asset limit order book simulator that compares execution strategies (market, limit, hybrid) across four spread/impact regimes, then maps outcomes to a 2-player game-theory payoff model to find Nash equilibria.

## Dataflow

```
configs/regimes.yaml
        │
        ▼
  ┌─────────────┐
  │ SimulatorSpec│  (frozen config: seed, T, regime, tick_size)
  └──────┬──────┘
         │
         ▼
  ┌──────────────┐     ┌──────────────────┐
  │MatchingEngine│◄────│ ExecutionStrategy │
  │  (engine.py) │     │ (strategies.py)  │
  └──────┬───────┘     └──────────────────┘
         │
         ▼
  ┌────────────────┐
  │ run_simulation │  (simulation.py — tick loop)
  │                │
  │  → LOBState    │
  │  → TradeRecord │
  │  → TickLog     │
  └──────┬─────────┘
         │
         ▼
  ┌──────────────────┐
  │ ExecutionMetrics  │  (metrics.py)
  │  compute_metrics  │
  │  aggregate_metrics│
  └──────┬────────────┘
         │
         ▼
  ┌──────────┐
  │ run_sweep│  (runner.py — full factorial)
  └──┬───┬───┘
     │   │
     │   ▼
     │  results/sweep_results.csv
     │
     ▼
  ┌─────────────────────┐
  │ build_payoff_matrix  │  (game_theory.py)
  │ find_best_responses  │
  │ find_equilibrium     │
  └──────┬──────────────┘
         │
         ▼
  results/strategic_regimes_table.csv
  charts/*.png
  showcase/*.png
```

## Module Reference

| Module | Purpose |
|--------|---------|
| `types.py` | Domain enums: `Side`, `OrderType`, `OrderStatus` |
| `state.py` | Core data structures: `Order`, `PriceLevel`, `LOBState`, `SimulatorSpec` |
| `invariants.py` | Book structural invariant checks (7 invariants); `BookInvariantError` |
| `engine.py` | Stateless `MatchingEngine`: market/limit execution, cancellation, price impact, LOB initialization |
| `strategies.py` | Agent execution strategies: `PureMarket`, `PureLimit`, `Hybrid` (protocol-based) |
| `simulation.py` | Tick-by-tick simulation loop (`run_simulation`); produces `ExecutionResult` |
| `metrics.py` | Per-run `ExecutionMetrics` and cross-run `aggregate_metrics` |
| `runner.py` | Full factorial sweep (`run_sweep`); regime loading from YAML |
| `game_theory.py` | 2-player payoff model, best-response logic, Nash equilibrium identification |
| `charts.py` | Matplotlib chart generation (slippage panels, fill-rate panels) |