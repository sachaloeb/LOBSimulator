# Reproducibility Guide

## Prerequisites

- **Python 3.11+** (tested on 3.11 and 3.12)
- **[uv](https://docs.astral.sh/uv/)** package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

## Clone-to-Results (Quick — ~2 min)

```bash
git clone https://github.com/sachaloeb/LOBSimulator.git
cd LOBSimulator
make run
```

This runs: `install → test → sweep-quick (n_runs=3) → game-theory → showcase`.

## Full Reproducibility (~15 min)

```bash
make all
```

Uses `n_runs=30` for the sweep — matches the paper's confidence intervals.

## Expected Output Files

After `make run` or `make all`:

| File | Description | Approx Size |
|------|-------------|-------------|
| `results/sweep_results.csv` | Aggregate metrics per (regime, strategy, size) | 5–10 KB |
| `results/strategic_regimes_table.csv` | Game-theory payoff matrix | 1 KB |
| `charts/slippage_vs_size.png` | 4-panel slippage chart | 200–400 KB |
| `charts/slippage_vs_size_fill_rate.png` | 4-panel fill rate chart | 150–300 KB |
| `charts/strategic_regimes_table.png` | Payoff heatmap | 100–200 KB |
| `showcase/execution_cost_by_regime.png` | Execution cost 2-panel chart | 150–300 KB |
| `showcase/nash_equilibrium_summary.png` | Nash equilibrium summary table image | 100–200 KB |
| `showcase/post.md` | Draft post | <1 KB |

## Seed Logging & Determinism

All randomness is derived from a single seed chain:

- `SweepConfig.seed_base` (default: 42)
- Each run uses seed = `seed_base + run_idx` (run_idx ∈ 0..n_runs-1)
- NumPy's `default_rng(seed)` provides the generator per run

This guarantees:
1. **Within-run determinism**: Same seed → identical tick-by-tick simulation
2. **Cross-run independence**: Different seeds per replication
3. **Platform reproducibility**: NumPy's PCG64 generator is platform-independent

To verify determinism, run the sweep twice and diff the CSV:
```bash
make sweep-quick
cp results/sweep_results.csv /tmp/run1.csv
make sweep-quick
diff results/sweep_results.csv /tmp/run1.csv  # should be empty
```

## Expected Runtime

On a typical laptop (M1/M2 Mac or modern x86):

| Target | Time |
|--------|------|
| `make test` | ~1 s |
| `make sweep-quick` | ~30 s |
| `make sweep` (n=30) | ~5 min |
| `make game-theory` | ~1 s |
| `make showcase` | ~2 s |
| `make run` (full quick) | ~1 min |
| `make all` (full n=30) | ~8 min |