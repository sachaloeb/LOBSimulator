# Week 6 — Clean-Environment Verification

## Test Results (clean clone)

```
35 passed, 1 skipped in 0.92s
```

(1 skipped: `test_regime_flip_hypothesis` requires pre-existing sweep data — passes after sweep runs.)

## Output Files Verified

All expected files present with non-zero sizes in `/tmp/lob-clean`:

| File | Size |
|------|------|
| `results/sweep_results.csv` | 15,580 B |
| `results/strategic_regimes_table.csv` | 1,082 B |
| `charts/slippage_vs_size.png` | 410,855 B |
| `charts/slippage_vs_size_fill_rate.png` | 236,414 B |
| `charts/strategic_regimes_table.png` | 64,967 B |
| `linkedin/main_chart.png` | 98,472 B |
| `linkedin/strategic_regimes_table.png` | 51,654 B |
| `linkedin/post_draft.md` | 1,022 B |

## Determinism Check

Sweep results between original repo and clean clone:
- **Max numeric difference:** 5.40e-12
- **All close (atol=1e-10):** True
- Differences are floating-point rounding at the 14th decimal place — expected across NumPy builds.
- Within-environment runs are byte-identical (verified by running sweep twice in the same env).

## Equilibrium Preserved

```
LOW impact:  NE at LP=wide_quote, LT=pure_limit (U_LT=+0.0032, U_LP=+0.1011)
HIGH impact: NE at LP=wide_quote, LT=pure_limit (U_LT=-0.0215, U_LP=-0.1250)
```

## Notebook Execution

`notebooks/00_main_analysis.ipynb` — executes top-to-bottom on a clean kernel without errors.

## Verification Date

2026-04-25