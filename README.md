# Market Microstructure + Game-Theory Execution Toy Model

**Author:** Sacha Loeb | **Status:** Week 1–2 skeleton

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

## Limitations

- Intra-tick event ordering is not modelled
- No empirical calibration to real data
- FIFO only — no pro-rata or time-weighted queue models
- Results are sensitive to Δt choice (tick length is artificial)
- Not suitable for HFT-style microsecond analysis

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
