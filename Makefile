.PHONY: test install lint game-theory sweep sweep-quick chart showcase run all

install:
	uv pip install -e ".[dev]"

test:
	uv run pytest tests/ -v

sweep:
	uv run python notebooks/01_baseline_sweep.py

sweep-quick:
	uv run python notebooks/01_baseline_sweep.py --n-runs 3

chart:
	uv run python -c "import pandas as pd; from lob_simulator.charts import plot_slippage_vs_size; plot_slippage_vs_size(pd.read_csv('results/sweep_results.csv'))"

game-theory:
	uv run python notebooks/02_game_theory.py

showcase:
	uv run python scripts/generate_showcase_figures.py

lint:
	uv run python -m py_compile src/lob_simulator/types.py
	uv run python -m py_compile src/lob_simulator/state.py
	uv run python -m py_compile src/lob_simulator/invariants.py
	@echo "Syntax OK"

# Quick end-to-end: n_runs=3 for fast demo
run: install test sweep-quick game-theory showcase

# Full reproducibility: n_runs=30
all: install test sweep game-theory showcase