# Payoff Model Specification (Week 5)

## Players

- **LT (Liquidity Taker):** A single strategic agent choosing an execution strategy.
- **LP (Liquidity Provider):** A representative market-maker choosing quote width.

## Action Spaces

- **LT actions:** {`pure_market`, `pure_limit`, `hybrid`} — the three execution strategies already implemented in the simulator.
- **LP actions:** {`tight_quote` (spread = 1 tick), `wide_quote` (spread = 5 ticks)} — corresponding to the spread_ticks parameter in `regimes.yaml`.

## Regime-to-Action Mapping

The LP's quoting action and the exogenous impact state jointly determine the market regime:

| LP Action \ Impact | Low (0.001) | High (0.01) |
|--------------------|-------------|-------------|
| tight_quote        | Regime A    | Regime C    |
| wide_quote         | Regime B    | Regime D    |

**Assumption A1 (Exogenous impact):** The impact coefficient is not a player action — it is an exogenous state variable representing information-driven price sensitivity.

**Assumption A2 (Regime = (LP action, impact state)):** Each regime is fully determined by the LP's spread choice and the impact level. All other regime parameters (lambda_bid, lambda_ask, cancel_prob) co-vary with spread as specified in `regimes.yaml`.

## LT Payoff

```
U_LT = -IS_mean - lambda_time * ttf_mean
```

Where:
- `IS_mean`: mean implementation shortfall from sweep results (price × qty units; positive = cost to LT).
- `lambda_time`: urgency penalty weight (default 0.0). When > 0, slower fills are penalized.
- `ttf_mean`: mean time-to-fill in ticks (0 for market orders).

**Assumption A3 (LT payoff = negative IS):** The LT's utility is the negative of execution cost. Lower IS is better for the LT.

**Assumption A4 (Linear urgency):** Time penalty enters linearly. This is a first-order approximation; real urgency is often convex.

**Assumption A5 (Missing ttf treated as zero penalty):** When ttf_mean is NaN (unfilled limit orders), we substitute 0.0 for the time penalty term. The fill failure is already captured in IS_mean.

## LP Payoff

```
U_LP = half_spread_earned * filled_qty - adverse_selection_coeff * filled_qty^2 - inventory_penalty * ttf_mean
```

Where:
- `half_spread_earned = 0.5 * spread_ticks * tick_size` — the LP earns half the spread on each filled unit (the other half goes to the opposite side).
- `filled_qty = order_size * fill_rate_mean` — proxy for the quantity the LP absorbs from the LT's execution. The LP is the passive counterparty to the LT's aggressive flow.
- `adverse_selection_coeff = impact_coeff` — from regime parameters. Higher impact means the LP is more likely to be adversely selected (the price moves against the LP's inventory after filling).
- `inventory_penalty = 0.0` (v0) — placeholder for future inventory risk cost. Documented as extension point.
- `ttf_mean`: mean time-to-fill (used only when inventory_penalty > 0).

**Assumption A6 (LP as passive counterparty):** The LP's filled quantity is proxied by the LT's fill rate × order size. In reality, the LP fills against many traders; here we model only the LP's exposure to the single LT.

**Assumption A7 (Quadratic adverse selection):** Adverse selection cost scales quadratically with filled quantity (larger fills move the price more against the LP). The coefficient is the regime's impact_coeff.

**Assumption A8 (Half-spread earning):** The LP earns exactly half the spread per unit filled. This assumes symmetric markets and ignores queue position.

**Assumption A9 (Closed-form proxy):** The LP payoff is a closed-form estimate, not derived from a simulated LP P&L process. It uses regime parameters and LT sweep outcomes as inputs.

**Assumption A10 (Zero inventory penalty in v0):** Inventory risk is not modeled. This is acceptable for a toy model focused on the spread-vs-adverse-selection tradeoff.

## Equilibrium Concept

**Iterated best response** on a 2×3 normal-form game (LP: 2 actions × LT: 3 actions), solved separately for each impact level (low, high).

1. For each impact level, construct the payoff matrix from sweep data at a given order_size.
2. For each LT strategy, find the LP's best response (argmax U_LP over LP actions).
3. For each LP action, find the LT's best response (argmax U_LT over LT strategies).
4. A cell is a **Nash equilibrium** if both the LT and LP strategies are mutual best responses.
5. **Tie-breaking:** lexicographic on (U_LT descending, U_LP descending).

**Assumption A11 (Simultaneous move):** Players choose simultaneously. In reality, LPs continuously adjust quotes in response to observed order flow.

**Assumption A12 (One-shot game per impact level):** The game is solved independently for each impact level. No cross-impact-level dynamics are modeled.