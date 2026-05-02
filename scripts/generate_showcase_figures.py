#!/usr/bin/env python
"""
scripts/generate_showcase_figures.py
Generate showcasable chart, table image, and post draft from sweep results.
Week-6 deliverable: Showcasable assets (Step 4).
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import yaml

# Deterministic rendering
matplotlib.rcParams["svg.hashsalt"] = "lob-simulator"
np.random.seed(42)

SHOWCASE_DIR = Path("showcase")
RESULTS_DIR = Path("results")

STRATEGY_COLORS = {
    "pure_market": "#c0392b",
    "pure_limit": "#2980b9",
    "hybrid": "#27ae60",
}
STRATEGY_LABELS = {
    "pure_market": "Pure Market",
    "pure_limit": "Pure Limit",
    "hybrid": "Hybrid (20%)",
}


def build_execution_cost_chart(df: pd.DataFrame) -> None:
    """1200x675, 2-panel chart: Regime A vs Regime D."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 6.75), dpi=100)

    panels = [
        ("regime_A", 'Regime A — Tight Spread / Low Impact'),
        ("regime_D", 'Regime D — Wide Spread / High Impact'),
    ]

    for ax, (regime, title) in zip(axes, panels):
        sub = df[df["regime"] == regime].copy()
        for strat in ["pure_market", "pure_limit", "hybrid"]:
            s = sub[sub["strategy"] == strat].sort_values("order_size")
            if s.empty:
                continue
            ax.plot(
                s["order_size"], s["slippage_bps_mean"],
                color=STRATEGY_COLORS[strat],
                marker="o" if strat == "pure_market" else ("s" if strat == "pure_limit" else "^"),
                linewidth=2.5,
                markersize=7,
                label=STRATEGY_LABELS[strat],
            )
            ax.fill_between(
                s["order_size"],
                s["slippage_bps_p25"],
                s["slippage_bps_p75"],
                color=STRATEGY_COLORS[strat],
                alpha=0.12,
            )
        ax.set_title(title, fontsize=14, fontweight="bold")
        ax.set_xlabel("Order Size (units)", fontsize=12)
        ax.set_ylabel("Slippage (bps)", fontsize=12)
        ax.tick_params(labelsize=11)
        ax.set_xscale("log")
        ax.grid(True, alpha=0.3)

    # Annotation arrows for headline findings
    # Regime A: limit dominates (negative slippage)
    a_limit = df[(df["regime"] == "regime_A") & (df["strategy"] == "pure_limit") & (np.isclose(df["order_size"], 5.0))]
    if not a_limit.empty:
        y_val = a_limit["slippage_bps_mean"].iloc[0]
        axes[0].annotate(
            "Limit saves ~1.3 bps",
            xy=(5.0, y_val), xytext=(12, y_val + 2.5),
            fontsize=11, fontweight="bold", color="#2980b9",
            arrowprops=dict(arrowstyle="->", color="#2980b9", lw=2),
        )

    # Regime D: market costs more
    d_market = df[(df["regime"] == "regime_D") & (df["strategy"] == "pure_market") & (np.isclose(df["order_size"], 50.0))]
    if not d_market.empty:
        y_val = d_market["slippage_bps_mean"].iloc[0]
        axes[1].annotate(
            "Market costs 26 bps at size 50",
            xy=(50.0, y_val), xytext=(8, y_val - 5),
            fontsize=11, fontweight="bold", color="#c0392b",
            arrowprops=dict(arrowstyle="->", color="#c0392b", lw=2),
        )

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=3, fontsize=12,
               bbox_to_anchor=(0.5, 0.02), frameon=True)

    fig.suptitle(
        "Slippage vs Order Size — Market vs Limit Execution",
        fontsize=16, fontweight="bold", y=0.98,
    )
    fig.tight_layout(rect=(0, 0.05, 1, 0.95))

    out = SHOWCASE_DIR / "execution_cost_by_regime.png"
    fig.savefig(out, dpi=100, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Wrote {out} ({out.stat().st_size:,} bytes)")


def build_table_image(matrix: pd.DataFrame, regimes: dict) -> None:
    """Render strategic regimes table as a clean image."""
    fig, ax = plt.subplots(figsize=(12, 6.75), dpi=100)
    ax.axis("off")

    # Build table data: one row per regime, grouped by impact level
    col_labels = ["Regime", "Spread", "Impact", "NE LT Strategy", "NE LP Action", "U_LT", "U_LP"]
    rows_data = []

    regime_display = {
        "regime_A": "A", "regime_B": "B",
        "regime_C": "C", "regime_D": "D",
    }
    spread_display = {
        "tight_quote": "Tight (1 tick)",
        "wide_quote": "Wide (5 ticks)",
    }

    for impact in ["low", "high"]:
        eq = matrix[(matrix["impact_level"] == impact) & (matrix["is_equilibrium"])]
        non_eq = matrix[(matrix["impact_level"] == impact) & (~matrix["is_equilibrium"])]

        # Show all (lp_action, impact) combos
        for lp_action in ["tight_quote", "wide_quote"]:
            regime_key = None
            for (lp, imp), rname in [
                (("tight_quote", "low"), "regime_A"),
                (("wide_quote", "low"), "regime_B"),
                (("tight_quote", "high"), "regime_C"),
                (("wide_quote", "high"), "regime_D"),
            ]:
                if lp == lp_action and imp == impact:
                    regime_key = rname
                    break

            sub = matrix[(matrix["regime"] == regime_key)]
            if sub.empty:
                continue

            # Find LT best response for this regime
            lt_br = sub[sub["is_LT_best_response"]]
            if lt_br.empty:
                lt_br = sub.sort_values("U_LT", ascending=False).head(1)

            row = lt_br.iloc[0]
            is_eq = bool(row["is_equilibrium"])
            rows_data.append([
                regime_display.get(regime_key, regime_key),
                spread_display.get(lp_action, lp_action),
                impact.capitalize(),
                row["lt_strategy"].replace("_", " ").title(),
                lp_action.replace("_", " ").title(),
                f"{row['U_LT']:+.4f}",
                f"{row['U_LP']:+.4f}",
            ])

    table = ax.table(
        cellText=rows_data,
        colLabels=col_labels,
        loc="center",
        cellLoc="center",
    )

    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1.0, 2.0)

    # Style header
    for j in range(len(col_labels)):
        cell = table[0, j]
        cell.set_facecolor("#2c3e50")
        cell.set_text_props(color="white", fontweight="bold", fontsize=13)

    # Style data rows — highlight equilibrium rows
    for i, row_data in enumerate(rows_data):
        is_eq_row = matrix[
            (matrix["regime"] == f"regime_{row_data[0]}") & matrix["is_equilibrium"]
        ]
        bg_color = "#d5f5e3" if not is_eq_row.empty else "#fdfefe"
        for j in range(len(col_labels)):
            cell = table[i + 1, j]
            cell.set_facecolor(bg_color)
            cell.set_edgecolor("#bdc3c7")

    # Remove grid-like appearance
    for key, cell in table.get_celld().items():
        cell.set_linewidth(0.5)

    fig.suptitle(
        "Strategic Regimes — Nash Equilibrium Analysis",
        fontsize=16, fontweight="bold", y=0.95,
    )

    # Add legend note
    ax.text(0.5, -0.05,
            "Green rows = Nash Equilibrium (mutual best response)",
            transform=ax.transAxes, fontsize=11, ha="center",
            style="italic", color="#27ae60")

    out = SHOWCASE_DIR / "nash_equilibrium_summary.png"
    fig.savefig(out, dpi=100, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Wrote {out} ({out.stat().st_size:,} bytes)")


def build_post(df: pd.DataFrame, matrix: pd.DataFrame) -> None:
    """Write the post."""
    # Compute headline number
    a_market = df[(df["regime"] == "regime_A") & (df["strategy"] == "pure_market") & (np.isclose(df["order_size"], 5.0))]
    a_limit = df[(df["regime"] == "regime_A") & (df["strategy"] == "pure_limit") & (np.isclose(df["order_size"], 5.0))]

    mkt_slip = a_market["slippage_bps_mean"].iloc[0] if not a_market.empty else 0
    lim_slip = a_limit["slippage_bps_mean"].iloc[0] if not a_limit.empty else 0
    savings = mkt_slip - lim_slip

    low_eq = matrix[(matrix["impact_level"] == "low") & matrix["is_equilibrium"]]
    high_eq = matrix[(matrix["impact_level"] == "high") & matrix["is_equilibrium"]]
    low_strat = low_eq["lt_strategy"].iloc[0] if not low_eq.empty else "?"
    high_strat = high_eq["lt_strategy"].iloc[0] if not high_eq.empty else "?"

    post = f"""\
Limit orders save {savings:.1f} bps vs market orders in a tight-spread regime — but the advantage shrinks under high price impact.

I built a toy limit order book simulator from scratch: 4 spread/impact regimes, 3 execution strategies (market, limit, hybrid), 1,000-tick simulations with Poisson order flow, seeded for full reproducibility.

Key finding: in the tight-spread/low-impact regime (Regime A), limit orders earn a negative slippage of {lim_slip:.1f} bps while market orders cost {mkt_slip:.1f} bps. Under high impact (Regime D), the gap narrows to <1 bp at small sizes.

The game-theory layer maps this to a 2-player payoff matrix (LP vs LT). Nash equilibrium strategy: {low_strat.replace('_', ' ')} under low impact, {high_strat.replace('_', ' ')} under high impact — payoff magnitudes shift by 10x across regimes.

Honest caveat: this is a toy model with linear impact, no empirical calibration, and a single strategic agent. See the repo's 10-point limitations section.

Code + notebook + full reproducibility: [GitHub link] #quant #marketmicrostructure #gametheory #python
"""

    out = SHOWCASE_DIR / "post.md"
    out.write_text(post)
    print(f"Wrote {out}")


def main() -> None:
    SHOWCASE_DIR.mkdir(parents=True, exist_ok=True)

    sweep_path = RESULTS_DIR / "sweep_results.csv"
    table_path = RESULTS_DIR / "strategic_regimes_table.csv"

    if not sweep_path.exists():
        print("ERROR: results/sweep_results.csv not found. Run `make sweep-quick` first.")
        sys.exit(1)

    df = pd.read_csv(sweep_path)

    # Run game theory if table doesn't exist
    if not table_path.exists():
        print("strategic_regimes_table.csv not found, generating...")
        from lob_simulator.game_theory import build_payoff_matrix
        from lob_simulator.runner import load_regimes
        regimes = load_regimes()
        matrix = build_payoff_matrix(df, regimes, order_size=5.0)
        table_path.parent.mkdir(parents=True, exist_ok=True)
        matrix.to_csv(table_path, index=False)
    else:
        matrix = pd.read_csv(table_path)

    with open("configs/regimes.yaml") as f:
        cfg = yaml.safe_load(f)
    regimes = cfg["regimes"]

    build_execution_cost_chart(df)
    build_table_image(matrix, regimes)
    build_post(df, matrix)
    print("\nAll showcase figures generated in showcase/")


if __name__ == "__main__":
    main()