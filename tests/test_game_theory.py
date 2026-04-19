"""Tests for the game-theory interpretation layer."""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import pytest

from lob_simulator.game_theory import (
    REGIME_MAP,
    PayoffParams,
    build_payoff_matrix,
    compute_lp_payoff,
    compute_lt_payoff,
    find_best_responses,
    find_equilibrium,
)

SWEEP_PATH = Path("results/sweep_results.csv")


# ── helpers ──────────────────────────────────────────────────────────────


def _make_row(**kwargs) -> pd.Series:
    """Create a minimal sweep-result row with sensible defaults."""
    defaults = {
        "regime": "regime_A",
        "strategy": "pure_market",
        "order_size": 5.0,
        "IS_mean": 0.01,
        "fill_rate_mean": 1.0,
        "ttf_mean": 0.0,
    }
    defaults.update(kwargs)
    return pd.Series(defaults)


# ── (a) LT payoff sign ──────────────────────────────────────────────────


def test_lt_payoff_sign_negative_for_positive_IS():
    """When IS_mean > 0, U_LT must be negative (cost to the taker)."""
    row = _make_row(IS_mean=0.05, ttf_mean=0.0)
    params = PayoffParams()
    assert compute_lt_payoff(row, params) < 0


# ── (b) LP payoff monotonic in spread ───────────────────────────────────


def test_lp_payoff_monotonic_in_spread():
    """Wider spread ⇒ higher LP payoff (holding impact and fill qty fixed)."""
    row = _make_row(order_size=5.0, fill_rate_mean=1.0, ttf_mean=0.0)
    params = PayoffParams(tick_size=0.01)

    regime_tight = {"spread_ticks": 1, "impact_coeff": 0.001}
    regime_wide = {"spread_ticks": 5, "impact_coeff": 0.001}

    u_tight = compute_lp_payoff(row, regime_tight, params)
    u_wide = compute_lp_payoff(row, regime_wide, params)

    assert u_wide > u_tight


# ── (c) LP payoff decreasing in impact ──────────────────────────────────


def test_lp_payoff_decreasing_in_impact():
    """Higher impact ⇒ lower LP payoff (holding spread and fill qty fixed)."""
    row = _make_row(order_size=5.0, fill_rate_mean=1.0, ttf_mean=0.0)
    params = PayoffParams(tick_size=0.01)

    regime_low = {"spread_ticks": 1, "impact_coeff": 0.001}
    regime_high = {"spread_ticks": 1, "impact_coeff": 0.01}

    u_low = compute_lp_payoff(row, regime_low, params)
    u_high = compute_lp_payoff(row, regime_high, params)

    assert u_low > u_high


# ── (d) Equilibrium on hand-crafted 2×2 ────────────────────────────────


def test_equilibrium_on_hand_crafted_2x2():
    """Dominant-strategy NE on a hand-crafted matrix.

    Payoff matrix (impact_level = 'low'):
        LP \\ LT  |  pure_market  |  pure_limit
        tight     | (3, 2)        | (1, 1)
        wide      | (2, 4)        | (4, 3)

    LT best response given tight: pure_market (3 > 1)
    LT best response given wide:  pure_limit  (4 > 2)
    LP best response given pure_market: wide   (4 > 2)
    LP best response given pure_limit:  wide   (3 > 1)

    NE = (wide, pure_limit) with payoffs (4, 3).
    """
    records = [
        {"regime": "regime_A", "lp_action": "tight_quote", "lt_strategy": "pure_market",
         "impact_level": "low", "U_LT": 3.0, "U_LP": 2.0,
         "is_LT_best_response": False, "is_LP_best_response": False, "is_equilibrium": False},
        {"regime": "regime_A", "lp_action": "tight_quote", "lt_strategy": "pure_limit",
         "impact_level": "low", "U_LT": 1.0, "U_LP": 1.0,
         "is_LT_best_response": False, "is_LP_best_response": False, "is_equilibrium": False},
        {"regime": "regime_B", "lp_action": "wide_quote", "lt_strategy": "pure_market",
         "impact_level": "low", "U_LT": 2.0, "U_LP": 4.0,
         "is_LT_best_response": False, "is_LP_best_response": False, "is_equilibrium": False},
        {"regime": "regime_B", "lp_action": "wide_quote", "lt_strategy": "pure_limit",
         "impact_level": "low", "U_LT": 4.0, "U_LP": 3.0,
         "is_LT_best_response": False, "is_LP_best_response": False, "is_equilibrium": False},
    ]
    matrix = pd.DataFrame(records)
    result = find_best_responses(matrix)
    result = find_equilibrium(result)

    eq_rows = result.loc[result["is_equilibrium"]]
    assert len(eq_rows) == 1
    eq = eq_rows.iloc[0]
    assert eq["lp_action"] == "wide_quote"
    assert eq["lt_strategy"] == "pure_limit"


# ── (e) Regime flip hypothesis (uses sweep data if available) ───────────


@pytest.mark.skipif(
    not SWEEP_PATH.exists(),
    reason="sweep_results.csv not found — run `make sweep-quick` first",
)
def test_regime_flip_hypothesis():
    """LT best response should differ between low-impact and high-impact.

    Specifically, we check that the set of equilibrium cells (or at minimum
    the LT best response under tight_quote) is NOT identical across impact
    levels, OR we document why it is.
    """
    import yaml

    df = pd.read_csv(SWEEP_PATH)
    with open("configs/regimes.yaml") as f:
        cfg = yaml.safe_load(f)
    regimes = cfg["regimes"]

    matrix = build_payoff_matrix(df, regimes, order_size=5.0)

    low_eq = matrix.loc[
        (matrix["impact_level"] == "low") & matrix["is_LT_best_response"]
        & (matrix["lp_action"] == "tight_quote")
    ]
    high_eq = matrix.loc[
        (matrix["impact_level"] == "high") & matrix["is_LT_best_response"]
        & (matrix["lp_action"] == "tight_quote")
    ]

    # We expect SOME difference — either in strategy or payoff magnitude
    if not low_eq.empty and not high_eq.empty:
        low_strat = low_eq.iloc[0]["lt_strategy"]
        high_strat = high_eq.iloc[0]["lt_strategy"]
        low_u = low_eq.iloc[0]["U_LT"]
        high_u = high_eq.iloc[0]["U_LT"]
        # Either strategy differs or payoff magnitude differs by > 10%
        assert (low_strat != high_strat) or not math.isclose(
            low_u, high_u, rel_tol=0.1
        ), "Expected regime flip or significant payoff shift between impact levels"