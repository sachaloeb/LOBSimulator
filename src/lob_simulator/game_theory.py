"""Game-theory interpretation layer for LOB simulator sweep results.

Maps simulated execution outcomes to a 2-player normal-form game between
a Liquidity Taker (LT) and a Liquidity Provider (LP), then solves for
Nash equilibria via iterated best response.

See configs/payoff_model.md for the full specification and assumptions.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Regime ↔ (LP action, impact level) mapping
# ---------------------------------------------------------------------------

#: Maps (lp_action, impact_level) → regime name in regimes.yaml / sweep CSV.
REGIME_MAP: dict[tuple[str, str], str] = {
    ("tight_quote", "low"): "regime_A",
    ("wide_quote", "low"): "regime_B",
    ("tight_quote", "high"): "regime_C",
    ("wide_quote", "high"): "regime_D",
}

#: Inverse map: regime name → (lp_action, impact_level).
REGIME_INV: dict[str, tuple[str, str]] = {v: k for k, v in REGIME_MAP.items()}

LP_ACTIONS: list[str] = ["tight_quote", "wide_quote"]
LT_STRATEGIES: list[str] = ["pure_market", "pure_limit", "hybrid"]
IMPACT_LEVELS: list[str] = ["low", "high"]


# ---------------------------------------------------------------------------
# Parameter container
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PayoffParams:
    """Tunable parameters for payoff computation.

    Attributes:
        lambda_time: Urgency weight penalising slow fills in LT utility.
        inventory_penalty: LP inventory risk cost per tick of holding (v0 = 0).
        tick_size: Price increment in currency units.
    """

    lambda_time: float = 0.0
    inventory_penalty: float = 0.0
    tick_size: float = 0.01


# ---------------------------------------------------------------------------
# Payoff functions
# ---------------------------------------------------------------------------


def compute_lt_payoff(row: pd.Series, params: PayoffParams) -> float:
    """Compute the Liquidity Taker's utility for one sweep-result row.

    Formula (see payoff_model.md §LT Payoff):
        U_LT = -IS_mean - lambda_time * ttf_mean

    where ttf_mean defaults to 0 when missing (unfilled limit orders).

    Args:
        row: A single row from sweep_results.csv with at least
             ``IS_mean`` and ``ttf_mean`` columns.
        params: Tunable payoff parameters.

    Returns:
        LT utility (float, typically negative — lower cost is better).
    """
    is_mean: float = float(row["IS_mean"])
    ttf: float = 0.0 if pd.isna(row.get("ttf_mean")) else float(row["ttf_mean"])
    return -is_mean - params.lambda_time * ttf


def compute_lp_payoff(
    row: pd.Series,
    regime_params: dict,
    params: PayoffParams,
) -> float:
    """Compute the Liquidity Provider's utility for one sweep-result row.

    Formula (see payoff_model.md §LP Payoff):
        U_LP = half_spread * filled_qty
             - impact_coeff * filled_qty**2
             - inventory_penalty * ttf_mean

    where:
        half_spread = 0.5 * spread_ticks * tick_size
        filled_qty  = order_size * fill_rate_mean
        impact_coeff = regime_params["impact_coeff"]

    Args:
        row: A single row from sweep_results.csv.
        regime_params: Dict with keys ``spread_ticks`` and ``impact_coeff``
                       (from regimes.yaml).
        params: Tunable payoff parameters.

    Returns:
        LP utility (float).
    """
    spread_ticks: float = float(regime_params["spread_ticks"])
    impact_coeff: float = float(regime_params["impact_coeff"])

    half_spread: float = 0.5 * spread_ticks * params.tick_size
    order_size: float = float(row["order_size"])
    fill_rate: float = float(row["fill_rate_mean"])
    filled_qty: float = order_size * fill_rate

    ttf: float = 0.0 if pd.isna(row.get("ttf_mean")) else float(row["ttf_mean"])

    return (
        half_spread * filled_qty
        - impact_coeff * filled_qty**2
        - params.inventory_penalty * ttf
    )


# ---------------------------------------------------------------------------
# Payoff matrix construction
# ---------------------------------------------------------------------------


def build_payoff_matrix(
    df: pd.DataFrame,
    regimes: dict,
    order_size: float,
    params: PayoffParams | None = None,
) -> pd.DataFrame:
    """Build the full payoff matrix from sweep results.

    Returns a long-format DataFrame with one row per (lp_action, lt_strategy,
    impact_level) combination. Columns:

        regime, lp_action, lt_strategy, impact_level, U_LT, U_LP,
        is_LT_best_response, is_equilibrium

    The best-response and equilibrium flags are populated by calling
    :func:`find_best_responses` and :func:`find_equilibrium` internally.

    Args:
        df: Full sweep results (all regimes, strategies, sizes).
        regimes: Parsed regimes.yaml dict (top-level key ``"regimes"``
                 mapping to per-regime parameter dicts).
        order_size: The order size to slice on (must exist in sweep data).
        params: Payoff parameters; defaults to ``PayoffParams()`` if None.

    Returns:
        Long-format payoff matrix DataFrame.

    Raises:
        ValueError: If the requested order_size is not found in sweep data.
    """
    if params is None:
        params = PayoffParams()

    available_sizes = sorted(df["order_size"].unique())
    if order_size not in available_sizes:
        raise ValueError(
            f"order_size={order_size} not in sweep data. "
            f"Available: {available_sizes}"
        )

    records: list[dict] = []

    for (lp_action, impact_level), regime_name in REGIME_MAP.items():
        regime_cfg = regimes[regime_name]

        for lt_strategy in LT_STRATEGIES:
            mask = (
                (df["regime"] == regime_name)
                & (df["strategy"] == lt_strategy)
                & (np.isclose(df["order_size"], order_size))
            )
            matching = df.loc[mask]
            if matching.empty:
                continue

            row = matching.iloc[0]
            u_lt = compute_lt_payoff(row, params)
            u_lp = compute_lp_payoff(row, regime_cfg, params)

            records.append(
                {
                    "regime": regime_name,
                    "lp_action": lp_action,
                    "lt_strategy": lt_strategy,
                    "impact_level": impact_level,
                    "U_LT": u_lt,
                    "U_LP": u_lp,
                    "is_LT_best_response": False,
                    "is_LP_best_response": False,
                    "is_equilibrium": False,
                }
            )

    matrix = pd.DataFrame(records)
    matrix = find_best_responses(matrix)
    matrix = find_equilibrium(matrix)
    return matrix


# ---------------------------------------------------------------------------
# Best-response and equilibrium logic
# ---------------------------------------------------------------------------


def find_best_responses(matrix: pd.DataFrame) -> pd.DataFrame:
    """Flag best-response cells in the payoff matrix.

    For each impact level:
    - LT best response: for each lp_action, the lt_strategy maximising U_LT.
      Ties broken lexicographically by (U_LT desc, U_LP desc).
    - LP best response: for each lt_strategy, the lp_action maximising U_LP.
      Ties broken lexicographically by (U_LP desc, U_LT desc).

    Args:
        matrix: Long-format payoff matrix (must have columns
                ``impact_level``, ``lp_action``, ``lt_strategy``,
                ``U_LT``, ``U_LP``).

    Returns:
        A copy of *matrix* with ``is_LT_best_response`` and
        ``is_LP_best_response`` columns updated.
    """
    out = matrix.copy()
    out["is_LT_best_response"] = False
    out["is_LP_best_response"] = False

    for impact in IMPACT_LEVELS:
        impact_mask = out["impact_level"] == impact

        # LT best response per LP action
        for lp_act in LP_ACTIONS:
            sub = out.loc[impact_mask & (out["lp_action"] == lp_act)]
            if sub.empty:
                continue
            best_idx = sub.sort_values(
                ["U_LT", "U_LP"], ascending=[False, False]
            ).index[0]
            out.loc[best_idx, "is_LT_best_response"] = True

        # LP best response per LT strategy
        for lt_strat in LT_STRATEGIES:
            sub = out.loc[impact_mask & (out["lt_strategy"] == lt_strat)]
            if sub.empty:
                continue
            best_idx = sub.sort_values(
                ["U_LP", "U_LT"], ascending=[False, False]
            ).index[0]
            out.loc[best_idx, "is_LP_best_response"] = True

    return out


def find_equilibrium(matrix: pd.DataFrame) -> pd.DataFrame:
    """Identify Nash equilibrium cells (mutual best responses).

    A cell is a Nash equilibrium iff it is both the LT's best response
    (given the LP's action) and the LP's best response (given the LT's
    strategy).

    Args:
        matrix: Payoff matrix with ``is_LT_best_response`` and
                ``is_LP_best_response`` already computed.

    Returns:
        A copy with ``is_equilibrium`` updated.
    """
    out = matrix.copy()
    out["is_equilibrium"] = out["is_LT_best_response"] & out["is_LP_best_response"]
    return out