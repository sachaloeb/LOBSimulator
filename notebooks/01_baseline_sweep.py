#!/usr/bin/env python
"""
01_baseline_sweep.py
Runs the full regime × strategy × order_size sweep and produces:
  results/sweep_results.csv
  charts/slippage_vs_size.png
  charts/slippage_vs_size_fill_rate.png

Usage:
    uv run python notebooks/01_baseline_sweep.py
    uv run python notebooks/01_baseline_sweep.py --n-runs 5
"""

from __future__ import annotations

import argparse
from pathlib import Path

from lob_simulator.charts import plot_slippage_vs_size
from lob_simulator.runner import SweepConfig, load_regimes, run_sweep


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-runs", type=int, default=30)
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    regimes = load_regimes()
    cfg = SweepConfig(n_runs=args.n_runs, validate=args.validate)
    df = run_sweep(cfg, regimes, results_dir=Path("results"))
    print(df.to_string())
    plot_slippage_vs_size(df, output_path=Path("charts/slippage_vs_size.png"))
    print("Sweep complete. Results: results/sweep_results.csv")


if __name__ == "__main__":
    main()