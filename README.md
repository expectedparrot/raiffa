# Raiffa

**Turn sourced beliefs into an auditable decision policy.**

Raiffa models choices, uncertain outcomes, payoffs, and what is known when each
choice is made. It compares admissible policies, identifies assumptions that
could reverse the recommendation, and prices explicitly modeled research.
Everything runs locally, with frozen inputs and replayable analyses.

Version **0.2.0** implements finite discrete influence diagrams, risk-neutral
monetary evaluation, parameter provenance, switching thresholds for affine
policy values, exact risk profiles, and finite value-of-information models.
Start with the [browser tutorial](docs/index.html): settle or litigate, find the
switching threshold, price a study, and explain a changed recommendation.
It includes copyable commands, an interactive preview, and a saved decision memo.
See also the [worked lawsuit example](examples/leg01/README.md),
[implementation notes](docs/finite-models.md), and [changelog](CHANGELOG.md).

## Install

Python 3.11 or newer on macOS or Linux is required. The revision store uses POSIX
file locking. No account, API key, EDSL installation, or network service is needed
for the finite decision workflow.

```bash
uv tool install 'git+https://github.com/expectedparrot/raiffa.git'
raiffa version
raiffa guide
```

For this checkout, including changes not yet published to GitHub:

```bash
python -m pip install -e '.[dev]'
raiffa version
python -m pytest -q
```

You can also run the CLI as `python -m raiffa.cli` after installing dependencies.
An installed wheel includes the synthetic fixtures: run
`raiffa model example --output model.json` (or add `--sequential`).

## Copy into a coding agent

```text
Help me analyze this decision with Raiffa in this checkout.
Install the local package with python -m pip install -e . and run raiffa guide.
Establish the decision maker, choices, horizon, payoff basis, and what can be
observed before each decision. Inspect raiffa model schema and the LEG-01 example.
Build the smallest supported finite model that represents the decision.
Every belief and payoff needs provenance, or a named assumption with an owner
and rationale. Do not invent sources or treat simulated responses as human ones.
Use raiffa next after each material step and follow its action until the selected
workflow is complete or input or unsupported capabilities prevent progress.
Keep the versioned JSON output for parsing. Review switching conditions and the
value of any declared study; do not assign study effectiveness without evidence
or an explicit assumption. Write the local decision memo and retain its model
revision and analysis ID. A model recommendation does not record my approval.
```

## A complete example

From the repository root:

```bash
raiffa init lawsuit
raiffa --project lawsuit model import --file examples/leg01/model.json
raiffa --project lawsuit solve leg01
raiffa --project lawsuit sensitivity one-way leg01 --param p_win --from 0 --to 1
raiffa --project lawsuit voi perfect leg01 --targets win
raiffa --project lawsuit research agenda leg01
raiffa --project lawsuit next
```

`next` supplies the report command with the concrete analysis ID. The synthetic
case recommends settling at a cost of $400,000 instead of litigating at expected
cost $630,000. The immediate decision switches at a win probability of 19/24.
A declared $10,000 study has gross information value $44,000 and net value
$34,000. These are validation inputs and outputs, not a real legal assessment.

The [sequential fixture](examples/leg01/sequential.json) explicitly models
“purchase research, observe its signal, then decide.” Its optimal expected
payoff is -$366,000, including the study cost. Hidden trial outcomes never become
available to the decision policy merely because the solver enumerates them.

## Workflow and commands

Global `--project PATH` goes **before** the subcommand. JSON is the default;
`--human` changes presentation.

| Task | Commands |
| --- | --- |
| Start and resume | `init`, `guide`, `next [MODEL]`, `status [MODEL]`, `version`, `doctor` |
| Define a model | `model schema`, `model import --file PATH`, `model show MODEL`, `model validate MODEL --strict` |
| Revise and compile | `model revise MODEL --file PATH --reason TEXT`, `model compile MODEL --output PATH` |
| Evaluate | `solve MODEL`, `risk MODEL`, `dominance MODEL` |
| Challenge | `sensitivity one-way MODEL --param ID --from X --to Y` |
| Price information | `voi perfect MODEL [--targets IDS] [--before DECISION]`, `voi sample MODEL --study ID`, `research agenda MODEL` |
| Inspect evidence and history | `provenance check MODEL`, `history`, `analysis list`, `analysis show ID`, `analysis compare BEFORE AFTER`, `analysis replay ID` |
| Deliver | `report ANALYSIS --format html\|svg\|json --output PATH`, `handoff ANALYSIS --target treffen\|vorhersage --output PATH` |

Normal solves reject missing or unaccepted provenance. Complete named assumptions
are allowed and disclosed. `solve --exploratory` evaluates draft provenance with
warnings and cannot complete the normal agent workflow.

## State and output contract

`.raiffa/` contains immutable model revisions, copied source artifacts, frozen
analyses, and derived reports. Revisions are hash-linked and serialized with a
workspace lock. A new accepted revision invalidates the previous revision's
completion state. Analyses retain their original inputs and engine version.

Commands return a versioned envelope:

```json
{
  "schema_version": "raiffa.cli/1.0",
  "ok": true,
  "command": ["next"],
  "project_revision": null,
  "data": {},
  "warnings": [],
  "artifacts": [],
  "next_actions": []
}
```

Failures use structured `error` instead of `data` on stderr and exit nonzero.
The `next` action includes argv, project context, missing inputs, and mutation
metadata. Reports write to an explicit output path and are deterministic for the
same frozen analysis, challenge artifacts, and renderer version.

## Scope and compatibility

The solver deliberately bounds enumeration and rejects models exceeding its
policy/world budget. It currently supports one valuation date, additive scalar
payoffs, risk neutrality, finite CPTs, and perfect recall. Unsupported memory,
distributions, nonlinear utility, and non-affine threshold problems fail rather
than being approximated silently.

Source references preserve artifact bytes and hashes. They do not authenticate
an upstream claim or establish that an assumption is empirically justified.
Named adapters for Helmer, Flyvbjerg, Vorhersage, Burr, Kahn, Premortem, Dewey,
Epiq, and Treffen are **not implemented**. Handoffs are proposed local JSON
contracts; they do not modify other packages. EDSL instrument generation,
continuous Monte Carlo, and general nonlinear sensitivity remain future work.

The older `tree`, `node`, `prob`, `utility`, and `scenario` commands still operate
on legacy tree projects. Those commands do not acquire provenance automatically.
Their bundled documentation is labeled as legacy; use `model` for new auditable
work. The [successor specification](docs/spec-v2.md) describes the longer-term
direction and the implemented subset is documented separately.
