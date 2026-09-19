# Raiffa: auditable decisions from elicited beliefs

Status: successor design, September 19, 2026. Version 0.2.0 implements the first
finite slice; [finite-models.md](finite-models.md) describes exactly what is
available. This document includes additional target behavior and is not a claim
that the entire proposal is implemented.
[SPEC.md](../SPEC.md) remains the historical tree-CLI design. Implementation
should proceed through the release gates below, not treat this entire proposal
as one release. No downstream package has yet accepted the proposed interchange
contracts.

## Purpose and boundaries

Raiffa turns explicit choices, sourced beliefs, information timing, and a
decision maker's preferences into a reproducible policy, switching conditions,
and research priorities. A recommendation is conditional on the recorded model;
provenance coverage alone does not establish that its evidence is sound.

Raiffa owns decision evaluation and audit artifacts. It consumes forecasts,
reference classes, elicitation results, and payoff models. It does not invent
probabilities, execute model inference, host human studies, optimize external
LP/queueing models, or act as a general simulation framework. Bayesian updating
inside a declared study model is decision evaluation, not a new forecast service.
External optimizers contribute frozen payoff tables or sampled outputs, not
arbitrary executable callbacks.

The local core must work without EDSL, accounts, Epiq, or sibling installations.
Optional adapters prepare and validate artifacts. Upstream identifiers and
Epiq claim references supplement locally preserved evidence; they cannot replace
the data needed to replay an analysis offline.

## Current implementation and reuse constraints

The September 19 local checkout is version 0.1.0, with 12 passing scenario tests.
It implements finite trees, rollback, scenarios, one-way sweeps, limited VOI,
snapshots, and Mermaid/HTML exports. The README contains invalid commands, and
`workflow.py` is not connected to a public agent entry point.

Retain compatible tree import and useful rendering/storage concepts, but audit
the mathematics before reusing analytical functions:

- `commands/voi.py` computes `evpi` by summing individual information values.
  The successor must evaluate the joint information intervention explicitly.
- `core/model.py` labels every lower-EU branch as dominated. Preserve that result
  as `inferior_expected_utility`; stochastic dominance is a separate calculation.
- Existing EVPPI evaluates alternatives around a chance node's parent but
  subtracts the whole tree's root value. Nested decisions need evaluation on a
  consistent initial information state and payoff scale.
- `regret --criterion` must either implement its requested criterion or reject it;
  a label must not change without changing the calculation.

## Representation and information semantics

The authoritative representation is a finite, regular influence diagram, with
an explicit decision order and perfect recall. The compiler produces a decision
tree with information-set identifiers, source-node mappings, and a model hash.
The compiled tree is a derived artifact, never a second editable source of truth.

Node kinds:

| Kind | Required meaning |
| --- | --- |
| Decision | Available actions, decision maker, stage, observed variables, and any action-availability rule. |
| Chance | Named outcomes and a complete conditional probability table, or a supported distribution specification in a later release. |
| Value | A typed payoff table or restricted expression, unit, payment time, and preference aggregation rule. |

Arcs have separate types: `dependency` into a chance node, `information` into a
decision, and `value` into a payoff. A dependency encodes the declared conditional
model, not automatically a causal claim. Action-conditioned probabilities need
an explicit intervention rationale. Decision order alone must not imply that a
latent chance outcome has become observable.

Policies map information sets to actions. Histories that differ only in hidden
outcomes must share a decision rule. Ordinary backward maximization on a tree
that exposes every sampled outcome would give the decision maker forbidden
foresight; the compiler/solver must preserve and enforce these constraints.
Prior actions and observations remain available at later decisions under the
supported perfect-recall assumption. Unsupported memory or decision-order
structures fail explicitly. These choices follow the distinction between
information arcs and probability dependencies in
[Norsys's decision-network documentation](https://www.norsys.com/WebHelp/NETICA/X_No_Forgetting_Links.htm).

Waiting is an action with an observation schedule, elapsed time, costs, and
possible changes to available actions or payoffs. Observation followed by a
decision represents flexibility, but option value requires those economics;
inserting a chance node does not by itself price delay. Comparisons use the same
valuation date and initial information state.

Compilation reports estimated tree size and rejects expansions exceeding a
declared budget. The first compiler supports finite discrete states, totally
ordered decisions, table payoffs, and scalar risk-neutral value. More general
distribution and utility support must not be silently approximated.

## Proposed schema contract

Use versioned JSON documents. A published JSON Schema and parser conformance
tests are an implementation gate for release A; the field definitions here are
the proposed contract, not a claim that a validator exists today.

| Object | Required fields |
| --- | --- |
| Model | `schema_version: raiffa.model/2.0`, `id`, `title`, `decision_maker`, `objective`, `valuation_context`, `decision_order`, `nodes`, `arcs`, `parameters`, `sources`, `studies`. |
| Objective | `direction: maximize`, `value_nodes`, `aggregation`, `preference_ref`. Costs are negative payoffs; an explicit importer may convert a minimize-cost model. |
| Valuation context | Monetary models: currency, price basis, valuation date, payment horizon, and sourced discount rule when timing differs. Nonmonetary models: named scale and interpretation. |
| Decision node | `id`, `kind: decision`, `actions`, `stage`, `observes`; optional versioned action-availability expression. |
| Chance node | `id`, `kind: chance`, `outcomes`, `parents`, `cpt`; each CPT row has a complete parent assignment and outcome-to-parameter references. |
| Value node | `id`, `kind: value`, `parents`, `unit`, and exactly one of `table` or `expression`. Table entries reference parameters. |
| Parameter | `id`, `kind`, `unit`, exactly one of `value`, `distribution`, or `expression`, `provenance`, and optional bounds/context. |
| Provenance | `source_type`, `source_refs`, `owner`, `rationale`, `evidence_population`, `review_status`; derived parameters also declare input references and transformation. |
| Source | `id`, `package`, `object_type`, `object_id`, upstream revision or frozen-artifact identity, `artifact_sha256`, local artifact path, record locator, capture time, and optional Epiq claim references. |
| Study | `id`, target uncertainties, observation outcomes, likelihood table, observation stage, cost/delay parameter references, sample design, population, availability, and provenance. |

Every empirical or preference-bearing numeric leaf must reference a parameter.
Expression literals are limited to structural constants such as zero, one,
indices, and exact unit conversions; literals cannot bypass provenance. Derived
values inherit the transitive provenance of their inputs. Parameter expression
graphs must be acyclic. Use an allowlisted expression AST, never Python `eval`.

Common validation rejects unknown fields/versions, duplicate identifiers,
dangling references, booleans as numbers, nonfinite values, inconsistent units,
invalid timing, cyclic dependencies, and incomplete CPT/payoff tables. CPT rows
must sum to one within recorded tolerance with each probability in [0, 1].
No implicit normalization or uniform fallback is allowed. Deterministic outcomes
remain explicit. Information availability is validated separately from the DAG.

### Provenance types and policy

| `source_type` | Required source interpretation |
| --- | --- |
| `elicited` | Frozen Helmer study/round/item or EDSL Results artifact/record; instrument, respondent population, aggregation, and transformation retained. |
| `reference_class` | Frozen Flyvbjerg analysis/distribution, cohort and metric definitions, exclusions, missingness, dependence, and fit method. |
| `registered_forecast` | Vorhersage question plus exact issued forecast revision, event definition, horizon, and outcome mapping. |
| `modeled` | Frozen Burr or other model run, model/input versions, output selector, units, and transformation. |
| `literature` | Dewey citation plus source-located finding, population/context, and numerical extraction or transformation. A citation alone is insufficient. |
| `assumption` | Named owner and rationale, with context/bounds where applicable; external source references may be empty. |

`evidence_population` is `human`, `simulated`, `mixed`, or `not_applicable`.
Mixed evidence requires an explicit component breakdown; no silent pooling.
`review_status` is `proposed`, `accepted`, or `rejected`. An adapter must preserve
contested/missing evidence rather than turn it into a single supported number.

Draft models may omit provenance and still be inspected. Default `solve` fails
on missing provenance or unresolved/rejected inputs. A complete named assumption
is permitted and is disclosed in the recommendation. An explicit
`solve --exploratory` may evaluate missing/proposed provenance, emits structured
warnings and `recommendation_status: exploratory`, and cannot satisfy the final
workflow gate. Structural or mathematical errors always block evaluation.
An all-assumption model is source-complete, not empirically verified.

Live forecast references are watch specifications only. Refresh imports a new
candidate snapshot; accepting it creates a new model revision. A solve never
resolves a moving `latest` reference or fetches data behind the caller's back.

## Evaluation, risk, and sensitivity

Exact evaluation returns a contingent policy, expected payoff/utility, ties,
policy table, and outcome distribution/CDF for each explicitly compared policy.
Alternative initial actions are evaluated with their continuation-policy rule
stated. Reports distinguish an action from a full strategy.

Later distribution support distinguishes outcome randomness from epistemic
parameter uncertainty and records their joint dependence. Independent sampling
requires an explicit assumption. Monte Carlo runs record input hashes, engine
version, seed, RNG algorithm, sample count, stopping rule, numerical uncertainty,
and strategy comparison method. Approximate policy optimization and policy
evaluation use separate samples or disclose selection bias. Sampling future
variables never makes them observable to a policy.

Risk profiles include quantiles, probability of a specified loss, and CDFs in
named units. First-order stochastic dominance compares entire payoff CDFs;
second-order dominance declares its increasing-concave-utility assumptions.
Finite exact comparisons and sampling-based evidence have different result
statuses. Sampling uncertainty must not be presented as proven dominance.

Scalar utility functions must be monotone and explicitly sourced. Certainty
equivalents use an invertible utility mapping and declared wealth/outcome
context. Multiattribute aggregation requires sourced preferences and explicit
independence/interaction assumptions; arbitrary scores cannot be added by default.
Utility elicitation prepares certainty-equivalent lottery instruments, supports
a clearly labeled persona dry run, and uses actual decision-maker responses for
their fitted preferences. A persona response cannot become their utility curve.

Sensitivity results lead with machine-readable switching conditions:

- One-way: parameter, unit, domain, held-fixed assumptions, competing policies,
  crossing/tie intervals, root-finding method, and residual/tolerance.
- Two-way: decision regions and boundary data. A curved boundary must not be
  summarized as independent thresholds joined by “or.”
- Probabilistic: parameter distribution/dependence assumptions and probability
  that each policy is optimal, distinct from its outcome risk profile.

Find multiple switches and tangencies; report unresolved regions when numerical
methods cannot establish coverage. Never call a coarse sweep bracket an exact
threshold. Render human statements from the same conditions used by exports and
grading. A tornado is a supporting visualization, not the primary conclusion.

## Value of information and research agenda

All information comparisons specify what becomes known, when, and which future
decisions can use it. For a single decision with payoff `V(a, theta)` and current
evidence `I`, the risk-neutral monetary definitions are:

```text
baseline       = max_a E[V(a, theta) | I]
joint EVPI     = E[max_a V(a, theta) | I] - baseline
EVPPI(S)       = E_S[max_a E[V(a, theta) | S, I] | I] - baseline
EVSI(study)    = E_y[max_a E[V(a, theta) | y, I] | I] - baseline
net study value = EVSI - study cost - modeled delay/opportunity costs
```

Sequential models evaluate admissible policies under the modified information
schedule. Realized future events that cannot feasibly be learned in advance
must be distinguished from epistemic parameters that research can estimate.
EVPI is an ideal-information bound, not a promise about a feasible study.
Joint information value is not the sum of individual values. The old `evpi`
summation must not survive as the new implementation.

An EVSI study needs a predictive observation model `P(y | theta, design)`, with
sourced likelihood parameters, costs, timing, and posterior update semantics.
No likelihood means `not_evaluable`, not zero EVSI or invented study quality.
The need to model study design and the cost of nested estimation is also
discussed in [Heath et al., Calculating EVSI in Practice](https://arxiv.org/abs/1905.12013).

The agenda ranks independently evaluated feasible studies by net value, discloses
costs, time horizon, population/decision count, uncertainty, and probability of a
policy change, and distinguishes research from acting now. Aggregate values
must declare how many decisions benefit; there is no implicit multiplication by
a population. Under nonlinear utility, report expected utility improvement and
compute monetary willingness to pay by including the payment inside utility;
do not label utility differences as dollars.

For a study measuring only S, cost-free exact values must satisfy
`0 <= EVSI <= EVPPI(S) <= joint EVPI` under the same model and timing. Negative
net values are allowed. Approximation errors are reported, not hidden by clipping.
Independent ranks are not a portfolio optimum: overlapping or complementary
studies require joint/conditional evaluation before pruning or combining them.
The router consumes a recommendation artifact; Raiffa never cancels external
work automatically.

## State, revisions, and recommendation attribution

```text
.raiffa/
  project.json              # identity, schema, current revision pointer
  revisions/<id>.json        # immutable full model snapshots
  events/<sequence>.json     # append-only actor, reason, parent, hashes
  sources/<sha256>/          # frozen source artifacts and manifests
  candidates/               # unaccepted imports and refresh proposals
  analyses/<id>/             # frozen inputs, settings, outputs, diagnostics
  instruments/<id>/          # elicitation plans and exported job manifests
  reports/<id>/              # derived from specified analyses
  handoffs/<id>/             # export artifacts and recipient contract
```

Each mutation validates before committing, locks the workspace, atomically
publishes a revision/event, and checks the expected parent revision. Interrupted
transactions are recoverable. Identical retries use idempotency keys and cannot
duplicate ingestion or lose state. Failed validation leaves no accepted change.
`doctor` verifies references and content hashes. Local hashes expose accidental
drift; they are not third-party notarization or access control.

Analysis manifests pin the model revision, source artifacts, package/solver
version, criterion, numerical settings, and outputs. Input changes mark derived
artifacts stale; the existence of any old analysis never means “complete.”
Replaying a snapshot never silently upgrades a solver or replaces evidence.

`analysis compare` reports changed source revisions/parameters, before/after
policy and value, and counterfactual re-solves. For a single change, report
whether that change alone flips the policy. For multiple changes, show
one-at-a-time substitutions, joint effect, and interactions. Infeasible hybrids
are labeled unevaluable. Order-dependent or Shapley attribution must state its
method and cost; never assert one uniquely responsible parameter when only a
joint change causes the switch. This is attribution within the model, not proof
of causation in the world.

## CLI and agent contract

Proposed command surface; commands below are not available merely because they
appear in this document. Global `--project PATH` precedes the subcommand.

| Stage | Commands |
| --- | --- |
| Setup | `version`, `doctor`, `guide`, `next`, `status`, `init NAME [--here]` |
| Modeling | `model import --file PATH`, `model show ID`, `model validate ID`, `model compile ID`, `model revise ID --file PATH --reason TEXT` |
| Evidence | `source import --file PATH`, `source refresh --file PATH`, `source accept ID --reason TEXT`, `provenance check MODEL` |
| Evaluation | `solve MODEL [--exploratory]`, `risk MODEL --policies FILE`, `dominance MODEL --kind first-order\|second-order` |
| Sensitivity | `sensitivity one-way MODEL --param ID --from X --to Y`, `sensitivity two-way MODEL --spec FILE`, `sensitivity probabilistic MODEL --spec FILE` |
| Information | `study import MODEL --file PATH`, `voi perfect MODEL [--targets IDS]`, `voi sample MODEL --study ID`, `research agenda MODEL` |
| Elicitation | `elicitation plan --file PATH`, `elicitation make PLAN --output PATH`, `elicitation ingest PLAN --results PATH`, `utility fit PLAN` |
| Audit | `history`, `analysis show ID`, `analysis compare BEFORE AFTER`, `analysis replay ID` |
| Delivery | `report ANALYSIS --format html\|svg\|json --output PATH`, `handoff ANALYSIS --target treffen\|vorhersage --output PATH` |

`guide` supplies method, constraints, phase gates, and supported capabilities.
`next` works before initialization and returns one primary action derived from
validated current state, plus alternatives. Its action contains absolute argv,
working directory/project path, missing input schemas, prerequisites, reason,
expected state transition, mutation/external-execution/cost metadata, and the
revision on which it was based. User-controlled model choices appear as required
inputs, not guessed values. Caller-provided authorization is preserved; metadata
does not create an automatic requirement to ask again.

Every normal command emits one JSON envelope on stdout. Structured failures use
the same envelope on stderr and a nonzero exit code, including parser errors:

```json
{
  "schema_version": "raiffa.cli/1.0",
  "ok": true,
  "command": ["next"],
  "project_revision": null,
  "data": {"phase": "uninitialized", "completion": false},
  "warnings": [],
  "artifacts": [],
  "next_actions": []
}
```

The example shows the envelope shape; real nonterminal `next` responses must
populate an executable or input-request action. Failure replaces `data` with
`error: {code, message, details, recoverable}` and includes recovery actions when
available. JSON contains no NaN/Infinity. `--human` changes presentation only.
Reports normally write to `--output`; intentional raw stdout requires `--raw`.
Choose and document stable exit codes for usage, project, validation, unsupported
capability, analysis, and unexpected internal failures.

State gates are evaluated in order, with a reason and required inputs:

| Phase | Exit condition |
| --- | --- |
| Uninitialized | Project identity recorded. |
| Frame | Decision maker, objective, alternatives, horizon, and value basis defined. |
| Structure | Valid nodes, dependencies, decision order, and observation rules. |
| Source | Complete accepted parameter provenance or disclosed named assumptions. |
| Evaluate | Supported model compiles and a current valid analysis exists. |
| Challenge | Required threshold/risk/VOI checks complete, or omissions have an explicit scope rationale. |
| Deliver | Current decision memo and handoffs generated; outstanding limitations disclosed. |
| Complete | All selected deliverables refer to the accepted current revision. |

External research creates a `waiting_for_external` state with a handoff, never
a busy loop. Imported results or changed parameters invalidate the affected
gates. Unsupported requested analyses block their gate with an explanation;
they cannot be silently counted as completed.

## EDSL boundary and artifacts

The sequence is explicit: Raiffa plans and makes instruments/Jobs artifacts;
the external caller uses `ep` to inspect, cost, and run them or arrange human
administration; Raiffa ingests the resulting artifact. Native EDSL support is
an optional dependency and must be tested against a supported version.

Manifests bind instrument, plan, model selection, agent/respondent identities,
source population, artifact hashes, question IDs, and result completeness.
Ingestion rejects wrong-plan, duplicate/conflicting, partial, or malformed
results with actionable diagnostics. Human preferences come from the actual
decision maker. Persona dry runs test wording and execution only. Utility fits
retain raw response references, consistency checks, fit uncertainty, and review
status. A generated study model or fit remains a proposal until accepted.

## Integration contracts

Use a Raiffa-owned versioned local interchange manifest: producer package/schema,
object ID, frozen revision/artifact hash, locator, population, context/units,
parameter mapping, transformation, and import diagnostics. Capture immutable
inputs and present a candidate model revision before acceptance. The following
are adapter requirements, not claims that matching upstream endpoints exist.

| Package | Import/export meaning and guardrail |
| --- | --- |
| Helmer / EDSL | Import study/item/round or response records with documented aggregation. Expert disagreement is not automatically a calibrated probability distribution. |
| Flyvbjerg | Import an accepted reference-class output, metric and membership rules, missingness, and dependence; retain applicability judgment. |
| Vorhersage | Import a pinned issued probability with matching event/horizon. Export parameter predicates and a revisit instruction; do not overwrite a forecast. |
| Kahn | Import narratives as candidate scenario states. Chance-node conversion requires separately sourced probabilities and a mutually exclusive, collectively exhaustive mapping. |
| Premortem | Import failure/mitigation candidates. Scores are not probabilities; overlapping failure events need a joint model. Mitigation effects, costs, and decision timing require parameters. |
| Burr | Import frozen payoff outputs with scenario/input hashes, units, timing, and sampled-row alignment. Do not reconstruct dependence from unrelated marginal summaries. |
| Dewey | Import source-located findings with applicability and extraction method; retain contested findings as contested. |
| Epiq | Preserve optional claim/evidence/event references and unresolved evidence states. A local analysis remains replayable without its database. |
| Treffen | Export a proposed decision record: policy, assumptions, alternatives, dissent/limitations, owner, evidence, and triggers. A computed recommendation is not a recorded human approval. |

Handoffs contain `schema_version: raiffa.handoff/1.0`, recipient, model/analysis
hashes, recommendation status, policy, threshold predicates with units/domain
and held-fixed assumptions, source references, and limitations. Receiver import
support is negotiated and fixture-tested before advertising direct integration.
Writing a handoff file does not send messages or mutate another package.

## Reports

Generate self-contained HTML and SVG without network fonts/scripts or an LLM:
influence/tree diagram, policy table, switching conditions, tornado, policy risk
profiles, VOI/research table, provenance inventory, and a concise decision memo.
The memo states the decision, perspective, recommended policy, competing options,
expected outcomes, assumptions that could reverse it, valuable research, and
limits. It distinguishes model output from the decision owner's disposition.

The same frozen analysis and renderer version must produce byte-identical
artifacts. Stable ordering/layout, escaped user text, fixed numeric formatting,
and timestamps drawn from the snapshot make this testable. Interactive controls
may explore derived views, but exports identify the frozen authoritative result.

## Canonical worked example: LEG-01

The referenced 57-item dataset has not been supplied or identified. The example
below is a proposed synthetic LEG-01 fixture, not a claim to reproduce its exact
wording or evidence. It is distinct from the legacy README's inconsistent
illustration. All inputs carry `assumption` provenance owned by
`raiffa_example_author`, with rationale “synthetic validation fixture,” and
`evidence_population: not_applicable`. No fictitious Helmer or forecast IDs.

Perspective: defendant; maximize monetary payoff (negative costs), risk neutral,
one valuation date. Settlement costs S = $400,000. Litigation costs C = $150,000
regardless of outcome. Win probability p = 0.60; losing incurs damages
D = $1,200,000. There is no additional award for winning. Settlement remains
available after an optional study. All other timing costs are zero in the base
fixture and are explicit assumptions.

```text
EV(settle)   = -S                  = -400,000
EV(litigate) = -C - (1-p)D         = -630,000
Tie when p  = 1 - (S-C)/D         = 19/24
Tie when D  = (S-C)/(1-p)         = 625,000  (holding p = 0.60)
```

Recommend settle; litigate becomes preferable when p exceeds 19/24 with other
inputs fixed, or damages fall below $625,000 with p fixed at 0.60. These are
separate one-way statements; joint changes use the boundary `C + (1-p)D = S`.
The risk-neutral settlement reservation cost without further information is
$630,000 under these assumptions; it is not a bargaining prediction.

The exact risk profiles cross: settling always pays -$400,000; litigation pays
-$150,000 with probability 0.60 and -$1,350,000 with probability 0.40. This is a
regression fixture against equating higher EV with first-order dominance.

Perfect outcome information available before choosing gives value -$250,000:
litigate if a win is known, otherwise settle. EVPI is therefore $150,000. This
is an ideal bound, distinct from the feasible study below.

A synthetic study has `P(favorable | win) = 0.80` and
`P(favorable | lose) = 0.20`, costs $10,000, and reports before the decision:

| Quantity | Exact target |
| --- | --- |
| P(favorable) | 14/25 = 0.56 |
| P(win given favorable) | 6/7 |
| P(win given unfavorable) | 3/11 |
| Policy after study | Litigate after favorable, settle after unfavorable. |
| Expected payoff before study cost | -$356,000 |
| Gross EVSI | $44,000 |
| Net study value | $34,000 |

Add a first decision “study or act now” to test sequencing; the optimum is the
study-contingent policy with net payoff -$366,000. A zero-informativeness study
must have zero gross EVSI. A study whose signal arrives after the final decision
cannot improve that decision. A later p = 0.85 assumption revision changes the
no-study recommendation to litigate with EV -$330,000; attribution identifies p
while preserving the old result. Distinguish this no-study comparison from a
comparison of policies that also include purchasing the study.

## Release gates and validation

**A — finite auditable decisions.** Publish the schema, finite influence-diagram
compiler with information-set enforcement, exact policy evaluation, parameter
provenance, immutable revisions, versioned CLI envelopes, `guide`/`next`, exact
finite risk profiles, one-way thresholds, finite joint/partial perfect information,
finite likelihood-based EVSI, and deterministic basic HTML/SVG memo. Ship LEG-01
as a runnable offline fixture. Generic local import/handoff manifests precede
named adapters. This is the first useful release, not a cosmetic CLI refresh.

**B — integrations and elicitation.** Add fixture-tested Helmer/EDSL,
Flyvbjerg/Vorhersage, Burr, Kahn/Premortem, Dewey/Epiq, and Treffen contracts as
available; explicit make/run/ingest handoffs; utility elicitation/fitting;
counterfactual revision attribution; two-way boundaries; and receiver-tested
monitoring predicates. No adapter is declared supported based solely on its
proposed manifest.

**C — distributional decision models.** Add supported continuous distributions,
dependence models, Monte Carlo diagnostics, nonlinear/multiattribute preferences,
probabilistic sensitivity, stochastic-dominance inference, and approximate EVSI
with validated error behavior. Preserve exact finite cases as reference oracles.

Required behavioral tests include:

1. LEG-01 numerical targets, policy/tie semantics, CDFs, and late-information case.
2. Equivalent finite diagram/tree results, including decisions with hidden states;
   a policy cannot act on unavailable information or forget required prior actions.
3. Malformed structure/CPTs, nonfinite values, dimensional mistakes, unsupported
   capabilities, and expansion budgets fail without accepted mutations.
4. Missing provenance blocks normal solves; assumptions disclose their status;
   simulated evidence never becomes human evidence through ingestion.
5. Joint information values, overlapping and complementary information, and
   exact VOI bounds; a study with no possible decision effect has zero value.
6. Independent hand-calculated nested-decision examples, not just legacy solver
   agreement; expected-value ranking remains distinct from dominance and regret.
7. Multiple switching regions, no switch, ties, probability-simplex constraints,
   root residuals, and explicit numerical uncertainty.
8. Failed/duplicate ingestion, concurrent revisions, crash recovery, frozen-source
   replay, stale-analysis detection, parser-error envelopes, and agent termination.
9. Source refresh plus single/joint parameter changes explains a flip without
   rewriting history or claiming unsupported attribution.
10. Deterministic safe rendering and version-pinned adapter round trips.

For the proposed dataset expressiveness test, first register the actual dataset
artifact and hash, then create a 57-row coverage manifest: item ID, required
decision/information structure, parameter sources, representable/not-supported
status, release gate, and executable fixture. “About 30 of 57” remains an
unverified target until that work is done. Do not invent missing case IDs or
manufacture provenance to satisfy the count.

For objective grading, score schema/semantic validity, provenance completeness
and fidelity, information legality, policy/value correctness, threshold accuracy,
and reproducibility separately. Compare equivalent policies on reachable
information sets rather than requiring identical node names. Unsupported and
invalid submissions count explicitly; a fabricated ID earns no provenance credit.
Use held-out perturbed parameters and analytical fixtures to prevent hard-coded
LEG-01 answers. Free-text rationale may supplement these checks, not replace them.

## Compatibility and repository work

Do not overwrite existing `.raiffa/` projects on open. Add an explicit migration
preview, validation report, backup/export, and new revision import. Legacy numbers
have unknown provenance: request assumption ownership/rationale or preserve them
as incomplete draft inputs, never auto-label them as elicited. Record the legacy
information-timing interpretation and require review where it is ambiguous.

Retain documented tree commands through a compatibility layer where their
semantics remain valid. Explain renamed dominance/VOI behavior and the new
envelope version in a migration guide; do not preserve incorrect mathematics
for output compatibility. Repair current README examples independently of the
new release so published instructions stop advertising nonexistent commands.

Package work includes installable README/license/URL metadata, dependency
constraints tested against supported Python versions, an optional EDSL extra,
lint/test/build CI, package-data checks, and an agent quickstart linked to the
bundled guide. Layout choice is secondary to behavior; a `src/` move is not a
prerequisite. Report the implemented subset clearly in README and CLI capabilities.
