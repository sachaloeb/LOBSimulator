# Market Microstructure + Game-Theory Execution Toy Model

**Author:** Sacha Loeb

## Assumptions

- Single asset, discrete time (time-sliced, fixed Δt ticks)
- Poisson order arrivals; FIFO queue within each price level
- Max 3 price levels per side (configurable)
- Linear price impact model

## How to Run

```bash
uv pip install -e ".[dev]"
make test
```

## Limitations vs Real Microstructure

### 1. Single strategic agent (no endogenous LP response)

The model features one Liquidity Taker optimising against a fixed LP quoting policy. In real markets, multiple LPs compete dynamically, adjusting quotes in response to observed order flow and inventory. This simplification is acceptable because the research question focuses on the LT's strategy choice given a static environment, not on LP competition dynamics.

### 2. Time-sliced discretisation (Δt artifact; not HFT-scale)

The simulator advances in fixed discrete ticks. Real markets operate in continuous time with nanosecond-resolution event streams. Intra-tick event ordering is lost, meaning simultaneous arrivals within a tick are resolved in an arbitrary sequence. This is sufficient for studying order-type tradeoffs at the strategic level but unsuitable for latency-sensitive HFT analysis.

### 3. Linear memoryless impact (no Almgren–Chriss decomposition; no Hawkes)

Price impact is modelled as a linear, instantaneous function of net order flow with no memory. Real impact is concave, persistent, and decays over time (Almgren–Chriss temporary/permanent decomposition). Hawkes-process self-exciting dynamics, where trades beget trades, are also absent. The linear model suffices for qualitative regime comparisons but underestimates cost at large order sizes.

### 4. FIFO queue only (no pro-rata; no queue-position model)

Orders at each price level are matched strictly first-in-first-out. Many real venues (e.g., CME options) use pro-rata or hybrid allocation. Queue position — a critical variable for limit order strategies in practice — is not explicitly modelled. FIFO is the most common equity model and adequate for the toy setting.

### 5. No information asymmetry (adverse selection is a coefficient, not an endogenous mechanism)

Adverse selection enters as a fixed `impact_coeff` parameter rather than emerging from informed vs. uninformed trader interaction. Real adverse selection depends on the information content of order flow, time of day, and news arrivals. The coefficient-based approach isolates the mechanical effect of price impact without requiring a full information model.

### 6. Single venue, single asset (no SOR; no cross-venue)

All trading occurs on one venue with one asset. Real execution involves smart order routing across fragmented venues with varying fee structures, latencies, and queue depths. Cross-asset hedging is also absent. The single-venue assumption keeps the strategy space tractable.

### 7. Stationary regime parameters (no intraday regime-switching)

Regime parameters (spread, impact, arrival rates) are fixed for the duration of each simulation run. Real markets exhibit pronounced intraday patterns (wider spreads at open/close, regime shifts around news) and stochastic volatility. Stationarity is acceptable for studying the structural effect of regime differences in a controlled experiment.

### 8. No empirical calibration (parameters are qualitative)

Regime parameters are chosen to span a qualitative range (tight/wide spread × low/high impact) rather than calibrated to historical tick data from a specific instrument. Absolute magnitudes of IS and slippage are therefore not directly comparable to real-world values. The model is designed for relative comparisons across regimes and strategies.

### 9. IID Bernoulli cancellations (real cancels are bursty, state-dependent)

Resting order cancellations are modelled as independent Bernoulli draws each tick with a fixed probability. In practice, cancellation rates are highly state-dependent — spiking during price moves, news events, or when queue position deteriorates. The IID assumption underestimates the volatility of available liquidity but keeps the simulation tractable.

### 10. Closed-form LP payoff proxy (not from a simulated LP P&L process)

The LP's utility is computed via a closed-form formula (spread earned minus quadratic adverse selection cost) rather than tracking a simulated LP's actual inventory, hedging costs, and realised P&L. This proxy captures the first-order spread-vs-impact tradeoff but misses inventory management, hedging, and the option value of resting orders. It is documented as an explicit simplification (Assumption A9 in `payoff_model.md`).

## Repo Structure

```
lob-simulator/
├── pyproject.toml
├── Makefile
├── README.md
├── src/
│   └── lob_simulator/
│       ├── __init__.py
│       ├── types.py          ← enums: Side, OrderType, OrderStatus
│       ├── state.py          ← Order, PriceLevel, LOBState, SimulatorSpec
│       └── invariants.py     ← check_book_invariants(), BookInvariantError
├── configs/
│   ├── regimes.yaml          ← 4 regimes A–D with full parameters
│   └── experiment_plan.md    ← MVE experiment plan
├── notebooks/                ← TODO(week-4): analysis notebooks
└── tests/
    ├── __init__.py
    └── test_book_invariants.py
```
