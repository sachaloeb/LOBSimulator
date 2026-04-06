"""Sweep runner for regime × strategy × order_size experiments."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import yaml
from tqdm import tqdm

from .metrics import aggregate_metrics, compute_metrics
from .simulation import run_simulation
from .state import SimulatorSpec
from .strategies import ExecutionStrategy, Hybrid, PureLimit, PureMarket
from .types import Side

STRATEGY_REGISTRY: dict[str, ExecutionStrategy] = {
    "pure_market": PureMarket(),
    "pure_limit": PureLimit(),
    "hybrid": Hybrid(),
}


@dataclass
class SweepConfig:
    order_sizes: list[float] = field(
        default_factory=lambda: [1.0, 2.0, 5.0, 10.0, 20.0, 50.0]
    )
    n_runs: int = 30
    seed_base: int = 42
    strategies: list[str] = field(
        default_factory=lambda: ["pure_market", "pure_limit", "hybrid"]
    )
    regime_names: list[str] = field(
        default_factory=lambda: ["regime_A", "regime_B", "regime_C", "regime_D"]
    )
    side: Side = Side.BID
    T: int = 1_000
    tick_size: float = 0.01
    max_depth: int = 3
    validate: bool = False


def load_regimes(config_path: Path = Path("configs/regimes.yaml")) -> dict:
    with open(config_path) as f:
        data = yaml.safe_load(f)
    return data["regimes"]


def run_sweep(
    sweep_config: SweepConfig,
    regimes: dict,
    results_dir: Path = Path("results"),
) -> pd.DataFrame:
    results_dir.mkdir(parents=True, exist_ok=True)
    rows = []

    total = (
        len(sweep_config.regime_names)
        * len(sweep_config.strategies)
        * len(sweep_config.order_sizes)
        * sweep_config.n_runs
    )
    pbar = tqdm(total=total, desc="sweep")

    for regime_name in sweep_config.regime_names:
        regime_params = regimes[regime_name]
        for strat_name in sweep_config.strategies:
            strategy = STRATEGY_REGISTRY[strat_name]
            for size in sweep_config.order_sizes:
                metrics_list = []
                for run_idx in range(sweep_config.n_runs):
                    spec = SimulatorSpec(
                        T=sweep_config.T,
                        tick_size=sweep_config.tick_size,
                        max_depth=sweep_config.max_depth,
                        seed=sweep_config.seed_base + run_idx,
                        regime=regime_name,
                    )
                    result = run_simulation(
                        spec,
                        regime_params,
                        strategy,
                        target_qty=size,
                        side=sweep_config.side,
                        validate=sweep_config.validate,
                    )
                    metrics_list.append(compute_metrics(result))
                    pbar.set_description(
                        f"[{regime_name} | {strat_name} | size={size}] {run_idx+1}/{sweep_config.n_runs}"
                    )
                    pbar.update(1)
                agg = aggregate_metrics(metrics_list)
                rows.append(
                    {
                        "regime": regime_name,
                        "strategy": strat_name,
                        "order_size": size,
                        **agg,
                    }
                )
    pbar.close()

    df = pd.DataFrame(rows)
    df.to_csv(results_dir / "sweep_results.csv", index=False)
    return df