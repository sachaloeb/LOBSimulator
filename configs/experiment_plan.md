# Experiment Plan — LOB Simulator (Weeks 1–2 freeze)

## Objective

This simulator answers the question: **when should a trader use a market order vs a limit order, and how does that choice depend on market microstructure?** We compare execution quality (slippage, implementation shortfall, fill probability, time-to-fill) for market and limit orders across four regimes spanning tight/wide spreads and low/high price impact. The resulting analysis feeds into a 2-player game-theory model (LP vs LT) to find equilibrium execution strategies.

## Simulator Approach

**Time-sliced (fixed Δt ticks).** The simulator advances in discrete steps t = 0, 1, …, T. At each tick, order arrivals are sampled from Poisson processes, matched FIFO against the resting book, and the mid-price drifts by impact. This approach trades intra-tick fidelity for simplicity and reproducibility — sufficient for a toy model that is not calibrated to real tick data.

## Regimes

| Regime | Spread (ticks) | Impact Coeff | λ_bid | λ_ask | λ_market | Cancel Prob | Description |
|--------|----------------|-------------|-------|-------|----------|-------------|-------------|
| A      | 1              | 0.001       | 5.0   | 5.0   | 1.0      | 0.05        | Tight spread / Low impact (baseline) |
| B      | 5              | 0.001       | 3.0   | 3.0   | 1.0      | 0.05        | Wide spread / Low impact |
| C      | 1              | 0.01        | 5.0   | 5.0   | 1.0      | 0.10        | Tight spread / High impact |
| D      | 5              | 0.01        | 3.0   | 3.0   | 1.0      | 0.10        | Wide spread / High impact |

## Metrics (collected Weeks 3–4)

- **Implementation shortfall:** mean, median, 95th percentile — measured as difference between decision price (mid at arrival) and execution price, normalised by tick size.
- **Slippage vs order size curve:** primary output chart — how execution cost scales with order quantity.
- **Fill probability for limit orders:** fraction of limit orders that fill fully within the simulation horizon.
- **Expected time-to-fill for limit orders:** conditional on fill, mean ticks from submission to complete execution.
- **Seed sensitivity:** coefficient of variation of each metric across n_runs=30 independent replications.

## Experiment Matrix

| Regime | Order Type | Order Sizes (multiples of vol_per_order) |
|--------|-----------|------------------------------------------|
| A      | Market    | 1×, 2×, 5×, 10×                         |
| A      | Limit     | 1×, 2×, 5×, 10×                         |
| B      | Market    | 1×, 2×, 5×, 10×                         |
| B      | Limit     | 1×, 2×, 5×, 10×                         |
| C      | Market    | 1×, 2×, 5×, 10×                         |
| C      | Limit     | 1×, 2×, 5×, 10×                         |
| D      | Market    | 1×, 2×, 5×, 10×                         |
| D      | Limit     | 1×, 2×, 5×, 10×                         |

Total: 4 regimes × 2 order types × 4 sizes × 30 runs = **960 simulation runs**.

## Sensitivity Analyses

- **Urgency constraint:** sweep max_ticks_to_fill ∈ {10, 50, 100, 500, ∞} — if a limit order hasn't filled within the deadline, force a market order for the remainder. Measures the urgency-cost trade-off.
- **Adverse selection proxy:** sweep impact_coeff ∈ {0.0005, 0.001, 0.005, 0.01, 0.02} within Regime A to isolate the effect of price impact on limit order profitability.

## Game-Theory Mapping (Week 5)

- **Players:** Liquidity Provider (LP) and Liquidity Taker (LT).
- **LP strategy space:** quote width (spread markup), quote depth, cancellation aggressiveness.
- **LT strategy space:** market vs limit, order size, urgency deadline.
- **Payoffs:** LP profit = earned spread − adverse selection losses; LT cost = implementation shortfall.
- **Equilibrium concept:** Nash equilibrium in the simultaneous-move game; iterated best response across regimes.
- **Key hypothesis:** equilibrium shifts from LP-favorable (Regime A) to LT-favorable (Regime D) as spread and impact increase.

## Quality Bar

- [ ] Deterministic: fixed seed reproduces identical results
- [ ] ≥ 5 invariant-protecting tests passing
- [ ] One-command run: `make run`
- [ ] Metrics reproducible across platforms (numpy RNG with explicit seed)
- [ ] All results accompanied by confidence intervals from 30 replications
