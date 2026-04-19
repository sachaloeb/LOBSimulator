.PHONY: test install lint game-theory

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

lint:
	uv run python -m py_compile src/lob_simulator/types.py
	uv run python -m py_compile src/lob_simulator/state.py
	uv run python -m py_compile src/lob_simulator/invariants.py
	@echo "Syntax OK"
