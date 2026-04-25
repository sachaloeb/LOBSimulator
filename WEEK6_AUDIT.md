# Week 6 Audit — Working Scratchpad

## Stale TODOs Found
- `src/lob_simulator/state.py:72-73` — `TODO(week-3)` re matching engine hook + metrics snapshot (both implemented)
- `src/lob_simulator/state.py:179` — `TODO(week-3)` re simulation loop (implemented in simulation.py)
- `src/lob_simulator/state.py:180` — `TODO(week-5)` re game-theory payoff model (implemented in game_theory.py)
- `README.md:77` — repo structure shows `TODO(week-4)` for notebooks (notebooks exist)

## Docstring Polish Needed
- `simulation.py` — `TickLog`, `ExecutionResult` missing docstrings
- `metrics.py` — `ExecutionMetrics`, `compute_metrics`, `aggregate_metrics` missing/incomplete docstrings
- `runner.py` — `SweepConfig`, `load_regimes`, `run_sweep` missing/incomplete docstrings
- `charts.py` — `plot_slippage_vs_size`, `_plot_panel_grid` missing/incomplete docstrings

## Missing Reproducibility Pieces
- No `make run` / `make all` targets
- No `make linkedin` target
- No `.python-version` file
- No `REPRODUCIBILITY.md`
- README lacks one-command instructions
- No notebook (`00_main_analysis.ipynb`)
- No `scripts/build_linkedin_assets.py`
- No `docs/architecture.md`

## Task Checklist
- [ ] Step 1: Cleanup pass (TODOs, docstrings, type hints, __init__.py)
- [ ] Step 2: Reproducibility (Makefile targets, .python-version, REPRODUCIBILITY.md)
- [ ] Step 3: Main notebook (00_main_analysis.ipynb)
- [ ] Step 4: LinkedIn assets script
- [ ] Step 5: README upgrade
- [ ] Step 6: Architecture doc
- [ ] Step 7: Clean-environment verification