Limit orders save 2.5 bps vs market orders in a tight-spread regime — but the advantage shrinks under high price impact.

I built a toy limit order book simulator from scratch: 4 spread/impact regimes, 3 execution strategies (market, limit, hybrid), 1,000-tick simulations with Poisson order flow, seeded for full reproducibility.

Key finding: in the tight-spread/low-impact regime (Regime A), limit orders earn a negative slippage of -1.3 bps while market orders cost 1.2 bps. Under high impact (Regime D), the gap narrows to <1 bp at small sizes.

The game-theory layer maps this to a 2-player payoff matrix (LP vs LT). Nash equilibrium strategy: pure limit under low impact, pure limit under high impact — payoff magnitudes shift by 10x across regimes.

Honest caveat: this is a toy model with linear impact, no empirical calibration, and a single strategic agent. See the repo's 10-point limitations section.

Code + notebook + full reproducibility: [GitHub link] #quant #marketmicrostructure #gametheory #python
