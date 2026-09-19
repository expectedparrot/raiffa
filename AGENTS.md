# Working on Raiffa

Read README.md and docs/finite-models.md for implemented behavior. docs/spec-v2.md
is the longer-term design and must not be treated as a list of available commands.

Run `python -m pytest -q`, `python -m ruff check raiffa tests`, and
`python -m build --no-isolation` after implementation changes. Mathematical tests
must include independent numerical targets and information-timing cases.

For tutorial changes, run `python3 scripts/check_tutorial.py`. Its executable
blocks in docs/index.html are checked against the real CLI. Use `--write-assets`
to regenerate the saved memo and fixture diagrams after intentional changes.

The finite schema source is raiffa/decision/schema.py. Keep the packaged
raiffa/schemas/model-2.0.json in sync; the test suite checks equality.

Preserve legacy tests and project data. Never infer provenance for old naked
numbers. New analyses and revisions are immutable. The finite core must remain
offline and must not invoke EDSL inference or mutate other packages.

For decision work, use `raiffa guide` and `raiffa next` after each material change.
