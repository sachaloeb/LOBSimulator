.PHONY: test install lint

install:
	uv pip install -e ".[dev]"

test:
	uv run pytest tests/ -v

lint:
	uv run python -m py_compile src/lob_simulator/types.py
	uv run python -m py_compile src/lob_simulator/state.py
	uv run python -m py_compile src/lob_simulator/invariants.py
	@echo "Syntax OK"
