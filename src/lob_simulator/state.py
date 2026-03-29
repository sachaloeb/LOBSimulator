"""Core state representations for the limit order book simulator."""

from __future__ import annotations

from dataclasses import dataclass, field

from .types import OrderStatus, OrderType, Side


@dataclass
class Order:
    """
    A single order submitted to the book.

    Attributes:
        order_id:  Unique identifier for this order.
        side:      BID or ASK.
        order_type: MARKET, LIMIT, or CANCEL.
        price:     Limit price; None for market orders.
        quantity:  Remaining unfilled quantity (>= 0).
        timestamp: Tick of arrival.
        status:    Current lifecycle state.
    """

    order_id: int
    side: Side
    order_type: OrderType
    price: float | None  # None for market orders
    quantity: float       # remaining unfilled quantity (>= 0)
    timestamp: int        # tick of arrival
    status: OrderStatus = OrderStatus.ACTIVE


@dataclass
class PriceLevel:
    """
    A single price point on one side of the book.

    Orders within a level are served FIFO (first-arrived, first-filled).
    """

    price: float
    orders: list[Order] = field(default_factory=list)

    @property
    def total_volume(self) -> float:
        """Sum of remaining quantity across all active orders at this level."""
        return sum(o.quantity for o in self.orders)

    @property
    def is_empty(self) -> bool:
        """True if no orders rest at this price level."""
        return len(self.orders) == 0


@dataclass
class LOBState:
    """
    Complete snapshot of the limit order book at a single tick.

    bids: sorted DESCENDING by price  (index 0 = best bid)
    asks: sorted ASCENDING  by price  (index 0 = best ask)
    max_depth: maximum price levels retained per side
    """

    bids: list[PriceLevel]
    asks: list[PriceLevel]
    mid_price: float
    timestamp: int
    max_depth: int = 3

    # TODO(week-3): implement FIFO matching engine hook
    # TODO(week-3): implement metrics snapshot collection

    @property
    def best_bid(self) -> float | None:
        """Best (highest) bid price, or None if bid side is empty."""
        return self.bids[0].price if self.bids else None

    @property
    def best_ask(self) -> float | None:
        """Best (lowest) ask price, or None if ask side is empty."""
        return self.asks[0].price if self.asks else None

    @property
    def spread(self) -> float | None:
        """Best ask minus best bid. None if either side is empty."""
        if self.best_bid is not None and self.best_ask is not None:
            return self.best_ask - self.best_bid
        return None

    @property
    def bid_volume(self) -> float:
        """Total volume resting on the bid side."""
        return sum(lvl.total_volume for lvl in self.bids)

    @property
    def ask_volume(self) -> float:
        """Total volume resting on the ask side."""
        return sum(lvl.total_volume for lvl in self.asks)


@dataclass(frozen=True)
class SimulatorSpec:
    """
    Frozen configuration for the LOB simulator.

    ── DESIGN DECISION: TIME-SLICED APPROACH ──────────────────────────────────
    The simulator advances in fixed discrete ticks t = 0, 1, …, T.
    At each tick the following phases execute IN ORDER:
        1. Order generation  — Poisson arrivals parameterised by lambda_bid,
                               lambda_ask, lambda_market from the regime config.
        2. Order processing  — matching engine consumes market orders against
                               resting book (Week 3 TODO).
        3. Price impact      — mid_price drifts by impact_coeff × signed flow
                               (Week 3 TODO).
        4. Cancellations     — each resting order cancels independently with
                               probability cancel_prob.
        5. State snapshot    — LOBState recorded for metrics (Week 3 TODO).

    WHY TIME-SLICED (not event-driven)?
    ✔ Simpler state machine — no priority-queue heap to manage.
    ✔ Uniform tick granularity maps cleanly to Poisson arrival batches.
    ✔ Easier to reason about regime parameters (rates per tick).
    ✔ Sufficient for toy-model accuracy: we are not calibrating to real data.

    LIMITATIONS OF TIME-SLICED:
    ✘ Cannot represent intra-tick ordering of events (all arrivals in a tick
      are treated as simultaneous before matching begins).
    ✘ Δt is artificial — results depend on tick length choice.
    ✘ Not suitable for HFT-style microsecond analysis.

    These limitations are explicitly acknowledged in README.md §Limitations.
    ──────────────────────────────────────────────────────────────────────────
    """

    # --- Core simulation parameters ---
    approach: str = "time-sliced"    # FROZEN — do not change
    T: int = 1_000                   # total number of ticks per run
    tick_size: float = 0.01          # minimum price increment
    max_depth: int = 3               # max price levels per side retained
    queue_model: str = "FIFO"        # queue priority within a level

    # --- Reproducibility ---
    seed: int = 42          # master RNG seed; all randomness derived from this
    regime: str = "regime_A"  # must match a key in configs/regimes.yaml

    # TODO(week-3): implement simulation loop: run(spec) -> list[LOBState]
    # TODO(week-5): implement game-theory payoff model (LP vs LT)

    def __post_init__(self) -> None:
        """Validate frozen configuration invariants."""
        if self.approach != "time-sliced":
            raise ValueError("approach must be 'time-sliced'")
        if self.queue_model != "FIFO":
            raise ValueError("only 'FIFO' queue model is supported in this version")
        if self.max_depth < 1 or self.max_depth > 10:
            raise ValueError("max_depth must be in [1, 10]")
        if self.T < 1:
            raise ValueError("T must be >= 1")
