#!/usr/bin/env python
"""Generate the strategic-regimes payoff table and heatmap chart.

Usage:
    python notebooks/02_game_theory.py [--order-size 5.0] [--urgency 0.0] [--inventory 0.0]

Outputs:
    results/strategic_regimes_table.csv
    charts/strategic_regimes_table.png
"""

from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # non-interactive backend

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import yaml

# Ensure the package is importable when running from repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lob_simulator.game_theory import (
    IMPACT_LEVELS,
    LP_ACTIONS,
    LT_STRATEGIES,
    PayoffParams,
    build_payoff_matrix,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Game-theory analysis of sweep results")
    parser.add_argument("--order-size", type=float, default=5.0)
    parser.add_argument("--urgency", type=float, default=0.0)
    parser.add_argument("--inventory", type=float, default=0.0)
    args = parser.parse_args()

    # ── Load data ────────────────────────────────────────────────────
    sweep_path = Path("results/sweep_results.csv")
    if not sweep_path.exists():
        print("ERROR: results/sweep_results.csv not found. Run `make sweep-quick` first.")
        sys.exit(1)

    df = pd.read_csv(sweep_path)

    with open("configs/regimes.yaml") as f:
        cfg = yaml.safe_load(f)
    regimes = cfg["regimes"]

    params = PayoffParams(
        lambda_time=args.urgency,
        inventory_penalty=args.inventory,
        tick_size=cfg.get("experiment_defaults", {}).get("tick_size", 0.01),
    )

    # ── Build matrix ─────────────────────────────────────────────────
    matrix = build_payoff_matrix(df, regimes, order_size=args.order_size, params=params)

    # ── Save CSV ─────────────────────────────────────────────────────
    out_csv = Path("results/strategic_regimes_table.csv")
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    matrix.to_csv(out_csv, index=False)
    print(f"Wrote {out_csv}")

    # ── Render chart ─────────────────────────────────────────────────
    out_png = Path("charts/strategic_regimes_table.png")
    out_png.parent.mkdir(parents=True, exist_ok=True)
    _render_heatmaps(matrix, out_png, args.order_size, params)
    print(f"Wrote {out_png}")

    # ── Narrative summary ────────────────────────────────────────────
    _print_narrative(matrix)


def _render_heatmaps(
    matrix: pd.DataFrame,
    out_path: Path,
    order_size: float,
    params: PayoffParams,
) -> None:
    """Side-by-side 2×3 heatmap tables, one per impact level."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle(
        f"Strategic Regimes — Payoff Matrix  |  "
        f"order_size={order_size}  |  urgency={params.lambda_time}  |  inventory={params.inventory_penalty}",
        fontsize=13,
        fontweight="bold",
    )

    lp_labels = {"tight_quote": "LP: tight (1 tick)", "wide_quote": "LP: wide (5 ticks)"}
    lt_labels = {"pure_market": "Market", "pure_limit": "Limit", "hybrid": "Hybrid"}

    for idx, impact in enumerate(IMPACT_LEVELS):
        ax = axes[idx]
        sub = matrix.loc[matrix["impact_level"] == impact]

        # Build 2×3 grids for U_LT and U_LP
        u_lt_grid = np.full((len(LP_ACTIONS), len(LT_STRATEGIES)), np.nan)
        u_lp_grid = np.full((len(LP_ACTIONS), len(LT_STRATEGIES)), np.nan)
        eq_grid = np.full((len(LP_ACTIONS), len(LT_STRATEGIES)), False)

        for _, row in sub.iterrows():
            r = LP_ACTIONS.index(row["lp_action"])
            c = LT_STRATEGIES.index(row["lt_strategy"])
            u_lt_grid[r, c] = row["U_LT"]
            u_lp_grid[r, c] = row["U_LP"]
            eq_grid[r, c] = row["is_equilibrium"]

        # Colour by U_LT (taker cost is the primary metric)
        im = ax.imshow(u_lt_grid, cmap="RdYlGn", aspect="auto")

        # Annotate each cell
        for r in range(len(LP_ACTIONS)):
            for c in range(len(LT_STRATEGIES)):
                lt_val = u_lt_grid[r, c]
                lp_val = u_lp_grid[r, c]
                if np.isnan(lt_val):
                    continue
                text = f"LT: {lt_val:+.4f}\nLP: {lp_val:+.4f}"
                ax.text(c, r, text, ha="center", va="center", fontsize=8)

                # Highlight equilibrium with a thick border
                if eq_grid[r, c]:
                    rect = mpatches.FancyBboxPatch(
                        (c - 0.48, r - 0.48), 0.96, 0.96,
                        linewidth=3,
                        edgecolor="blue",
                        facecolor="none",
                        boxstyle="round,pad=0.02",
                    )
                    ax.add_patch(rect)

        ax.set_xticks(range(len(LT_STRATEGIES)))
        ax.set_xticklabels([lt_labels[s] for s in LT_STRATEGIES], fontsize=9)
        ax.set_yticks(range(len(LP_ACTIONS)))
        ax.set_yticklabels([lp_labels[a] for a in LP_ACTIONS], fontsize=9)
        ax.set_title(f"Impact: {impact}", fontsize=12)
        ax.set_xlabel("LT Strategy")
        ax.set_ylabel("LP Action")

    plt.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _print_narrative(matrix: pd.DataFrame) -> None:
    """Print ≤ 5 line plain-English equilibrium narrative."""
    print("\n--- Equilibrium Narrative ---")
    for impact in IMPACT_LEVELS:
        eq = matrix.loc[(matrix["impact_level"] == impact) & matrix["is_equilibrium"]]
        if eq.empty:
            print(f"  {impact.upper()} impact: No pure-strategy Nash equilibrium found.")
        else:
            for _, row in eq.iterrows():
                print(
                    f"  {impact.upper()} impact: NE at LP={row['lp_action']}, "
                    f"LT={row['lt_strategy']} "
                    f"(U_LT={row['U_LT']:+.4f}, U_LP={row['U_LP']:+.4f})"
                )

    low_eq = matrix.loc[(matrix["impact_level"] == "low") & matrix["is_equilibrium"]]
    high_eq = matrix.loc[(matrix["impact_level"] == "high") & matrix["is_equilibrium"]]
    if not low_eq.empty and not high_eq.empty:
        low_strats = set(low_eq["lt_strategy"])
        high_strats = set(high_eq["lt_strategy"])
        if low_strats != high_strats:
            print("  => Equilibrium SHIFTS across impact levels (strategy flip confirmed).")
        else:
            print("  => Same LT strategy in equilibrium across impact levels; "
                  "payoff magnitudes differ due to higher execution costs under high impact.")
    print()


if __name__ == "__main__":
    main()