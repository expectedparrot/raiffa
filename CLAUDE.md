# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
pip install -e .          # install (editable)
pytest -q                 # run all tests
raiffa --help             # CLI entry point
```

Run without installing: `python -m raiffa.cli`.

## Architecture

Raiffa is a JSON-first CLI for decision analysis (decision trees, expected-utility rollback, sensitivity, EVPI). All commands default to JSON stdout; `--human` enables rich readable output.

**Layers:**

- `raiffa/cli.py` — Typer app root; `CliContext` carries `--project`, `--human`, `--quiet` across commands; catches `RaiffaError` and emits structured JSON to stderr.
- `raiffa/commands/` — One module per command group (`tree`, `node`, `prob`, `utility`, `solve`, `sensitivity`, `voi`, `regret`, `dominance`, `scenario`, `export`). Pattern: load project → validate → analyse → write snapshot → output.
- `raiffa/core/model.py` — The core. `TreeModel` dataclass + `load_tree_model()`, `validate_model()`, `solve_model()` (depth-first EU rollback), `one_way_sensitivity()`, `evppi()`, `mermaid()`. Most analytical work lives here.
- `raiffa/core/project.py` — `Project` dataclass; `find_project()` walks upward to locate `.raiffa/meta.json`; `create_project()` initialises the directory layout.
- `raiffa/core/store.py` — Flat JSON file I/O: `read_entity`, `write_entity`, `list_entities`, `append_record` (timestamped snapshot ids).
- `raiffa/core/errors.py` — `RaiffaError` hierarchy with typed exit codes (1–4); all errors serialise to `{code, message, details}`.

**Storage layout (`.raiffa/`):** flat JSON files per entity, one subdirectory per collection (`trees/`, `nodes/`, `scenarios/`, `analyses/`, …). Scenarios store only overrides; the base tree is never duplicated.

**Key invariants:**
- `deepcopy()` is used throughout so the loaded model is never mutated.
- Every solve/analysis writes a timestamped snapshot to `analyses/` unless `--no-write` is passed.
- Sibling probabilities are rescaled proportionally when sensitivity sweeps adjust one branch.
- `branch_label` (human-facing) is separate from `id` (stable script key).

**Tests:** `tests/test_scenarios.py` runs end-to-end scenario workflows against a temp project directory.
