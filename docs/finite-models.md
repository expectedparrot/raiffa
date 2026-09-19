# Finite decision models in 0.2.0

This page describes implemented behavior. [spec-v2.md](spec-v2.md) is the broader
design, with additional capabilities that have not shipped.

## Model input

Use `raiffa model schema` to inspect the schema through the CLI. The standalone
[JSON Schema](../raiffa/schemas/model-2.0.json) is included in distributions.
[model.json](../examples/leg01/model.json) and
[sequential.json](../examples/leg01/sequential.json) are complete accepted inputs.
Both ship in the wheel: `model example --output model.json` writes the base
fixture; add `--sequential` for the study-purchase model.

The model specifies decision/chance/value nodes, decision order, explicit typed
arcs, parameters, sources, and optional studies. Decision nodes list `observes`;
chance and value nodes list `parents`. Arcs must exactly match those declarations.
Earlier observations and decisions are remembered automatically. Information
arcs into an earlier decision that create a cycle are rejected.

Chance nodes use complete conditional probability tables. Value nodes use
complete payoff tables. Every table entry references a named parameter.
Parameters carry a literal value or a restricted expression AST using `ref`,
`add`, `subtract`, `multiply`, `divide`, and `negate`. Only zero and one are
permitted as structural expression literals. Addition/subtraction require equal
units; multiplication supports a dimensionless scalar; division supports a
dimensionless denominator or cancellation of equal units. Units are exact
labels, not an implicit conversion service. Probabilities use unit `1`.

The objective sums every value node exactly once and references an explicitly
sourced dimensionless preference parameter equal to one, meaning risk-neutral
expected-value maximization. All values have the same declared unit and single
valuation date. Risk aversion, multiattribute preference functions, delayed
discounting, and distribution nodes are unsupported. Price basis and timing
must already be consistent in imported payoffs.

## Provenance and source artifacts

Each parameter has `source_type`, `source_refs`, `owner`, `rationale`,
`evidence_population`, and `review_status`. Supported source types are
`elicited`, `reference_class`, `registered_forecast`, `modeled`, `literature`,
and `assumption`. The finite schema supports human, simulated, or not-applicable
populations; mixed evidence must be separated before import.

Named assumptions may have no source references. Other types require references
to source entries containing an upstream identity, exact revision, local file,
SHA-256, and a locator. Source paths are resolved relative to the imported model
file. The importer verifies the bytes and copies them into `.raiffa/sources/`.
Later solves read those frozen copies and never fetch remote data. Generic
imports verify integrity, not the truth of the source or validity of an upstream
record ID; native producer-specific validation is future adapter work.

Draft imports may have missing or proposed provenance. `model validate --strict`
and normal `solve` reject it. `solve --exploratory` discloses incomplete provenance
and does not satisfy `next`'s evaluation gate. Named assumptions remain visible
even after acceptance. A valid schema and complete provenance are not evidence
that the assumptions describe the world accurately.

## Solver and limits

The reference solver enumerates deterministic policies indexed by observable
information, then evaluates their expected values over the finite outcome space.
Unreachable policy rows may be present; reports show their reach probabilities
and omit unreachable rows from the displayed recommendation. Ties are explicit;
counts include policies differing only on unreachable histories.

This prevents a common incorrect solution: independently optimizing each branch
of an expanded tree while using hidden states that the decision maker cannot
observe. `model compile` exports an information-set-constrained tree with a warning
that ordinary unconstrained rollback is invalid for such a tree.

Limits are explicit: 10,000 assignments per conditional table/information set,
100,000 policies, and a 2,000,000 policy × world × node work budget. Compilation
has a separate 10,000-node budget; report tree diagrams cap expansion at 150
nodes. Large cases fail with structured diagnostics rather than silently dropping
states. Finite enumeration is exact in structure, with floating-point arithmetic
and disclosed numerical tolerances; it is not symbolic arbitrary-precision math.

`risk` and `solve` return exact finite support/CDF tables. Initial action
comparisons optimize continuation policies separately. `dominance` compares
those CDFs for first-order dominance; it is not merely an expected-value ranking.

## Sensitivity and information value

One-way sensitivity certifies an affine degree bound from the parameter expression
graph and chance probabilities. It constructs the upper envelope of policy value
lines, including switching regions and tie boundaries. Other literal parameters
are held fixed; dependent expressions such as `1 - p_win` are recomputed. Input
bounds must remain valid across the sweep. Non-affine cases fail explicitly;
there is no claim of exhaustive nonlinear root finding.

`voi perfect` evaluates a single joint information intervention before a named
decision, defaulting to the first. It does not add separate information values.
If the requested observation would precede a decision on which that variable
depends, the cyclic intervention is rejected. Information supplied only after
an earlier payoff-determining decision cannot retrospectively change that choice.

`voi sample` requires a declared likelihood table, finite observations, target
chance variables, the decision before which the signal arrives, an explicit cost
parameter, and sourced study-design assumptions. Costs are paid on the single
valuation date. `research agenda` ranks net study values independently against
the no-study policy; it does not optimize a portfolio or cancel external work.
Timing conflicts yield `not_evaluable`, never fabricated zero information value.

## State and agent completion

The new records coexist with legacy project state:

```text
.raiffa/
  meta.json
  revisions/             # one atomic, full-model journal entry per mutation
  sources/               # content-addressed frozen evidence bytes
  decision_analyses/      # content-addressed frozen analysis records
  decision_reports/       # derived artifacts and integrity manifests
  handoffs/               # proposed local recipient contracts
```

Journal publication is the commit point. A file lock serializes writers; each
revision hashes its body and references the previous journal entry and previous
revision of that model. `model revise --expected-revision ID` detects stale
writers. Identical imports and analyses are idempotent. Interrupted writes may
leave unreferenced source blobs but cannot publish a partial revision.

`doctor` checks the journal chain, source bytes, analysis hashes, and report
artifacts. Hashes detect integrity problems, not adversarial rewriting of the
entire local history. Analysis replay requires the recorded engine version.

`next` selects the first incomplete gate: import/frame, provenance, solve,
sensitivity for literal parameters with declared bounds, a research agenda when
studies exist, and a current HTML memo. Without declared bounds or studies,
those checks are outside the selected workflow; the memo discloses missing
analyses. Completion refers to this finite workflow, not every capability in the
successor design. Multiple models require selection. A new revision invalidates
all earlier gate results. New challenge artifacts require regenerating the memo.

The `guide` command lists unsupported capabilities. Reports and handoffs carry
analysis/revision identifiers. A handoff does not mean the owner approved the
policy or that the receiving package can already import the proposed contract.

## Legacy compatibility

Legacy `tree`/`node` commands keep their existing layout and numeric inputs. No
automatic migration labels those numbers as elicited or accepted. Import a new
finite model with a distinct ID and explicit provenance when modernizing a case.
The JSON success envelope retains its old `data`/`warnings` fields and adds
version, status, command, artifacts, and next actions. Domain and argument errors
are versioned JSON on stderr.

Legacy `dominated_branches` remains an expected-utility ranking field for
compatibility. Multi-node legacy EVPI sums, nested legacy EVPPI, and unsupported
regret criteria are now rejected instead of returning misleading calculations.
