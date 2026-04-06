"""Chart generation for sweep results."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

STRATEGY_STYLES = {
    "pure_market": {"color": "#c0392b", "linestyle": "-", "label": "Pure Market", "marker": "o"},
    "pure_limit": {"color": "#2980b9", "linestyle": "--", "label": "Pure Limit", "marker": "s"},
    "hybrid": {"color": "#27ae60", "linestyle": "-.", "label": "Hybrid (20%)", "marker": "^"},
}

REGIME_TITLES = {
    "regime_A": "A — Tight spread / Low impact",
    "regime_B": "B — Wide spread / Low impact",
    "regime_C": "C — Tight spread / High impact",
    "regime_D": "D — Wide spread / High impact",
}


def _plot_panel_grid(
    df: pd.DataFrame,
    output_path: Path,
    metric_col: str,
    title: str,
    y_label: str,
    ci_lo_col: str | None = None,
    ci_hi_col: str | None = None,
    y_range: tuple[float, float] | None = None,
    x_col: str = "order_size",
) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, axes = plt.subplots(2, 2, figsize=(12, 9), sharey=True)
    regimes_order = ["regime_A", "regime_B", "regime_C", "regime_D"]
    use_log_x = False
    if df[x_col].max() / max(df[x_col].min(), 1e-9) > 10:
        use_log_x = True

    for ax, regime in zip(axes.flatten(), regimes_order):
        sub = df[df["regime"] == regime]
        for strat, style in STRATEGY_STYLES.items():
            s = sub[sub["strategy"] == strat].sort_values(x_col)
            if s.empty:
                continue
            ax.plot(s[x_col], s[metric_col], **style)
            if ci_lo_col and ci_hi_col:
                ax.fill_between(
                    s[x_col],
                    s[ci_lo_col],
                    s[ci_hi_col],
                    color=style["color"],
                    alpha=0.15,
                )
        ax.set_title(REGIME_TITLES.get(regime, regime))
        ax.set_xlabel("Order Size (units)")
        ax.set_ylabel(y_label)
        if use_log_x:
            ax.set_xscale("log")
        if y_range is not None:
            ax.set_ylim(*y_range)

    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", bbox_to_anchor=(0.995, 0.995))
    fig.suptitle(title)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300)
    plt.close(fig)


def plot_slippage_vs_size(
    df: pd.DataFrame,
    output_path: Path = Path("charts/slippage_vs_size.png"),
    metric_col: str = "slippage_bps_mean",
    ci_lo_col: str = "slippage_bps_p25",
    ci_hi_col: str = "slippage_bps_p75",
    x_col: str = "order_size",
) -> None:
    _plot_panel_grid(
        df,
        output_path=output_path,
        metric_col=metric_col,
        ci_lo_col=ci_lo_col,
        ci_hi_col=ci_hi_col,
        title="Slippage vs Order Size — Baseline Sweep (n=30 runs/cell)",
        y_label="Slippage (bps)",
        x_col=x_col,
    )
    # companion fill-rate chart
    fr_path = output_path.parent / (output_path.stem + "_fill_rate.png")
    _plot_panel_grid(
        df,
        output_path=fr_path,
        metric_col="fill_rate_mean",
        title="Fill Rate vs Order Size — Baseline Sweep",
        y_label="Fill Rate",
        y_range=(0.0, 1.05),
        x_col=x_col,
    )