# raiffa — decision-tree analysis CLI for uncertainty, rollback, and value of information
<!-- id: raiffa/raiffa -->

raiffa builds and analyzes decision trees with decision nodes, chance nodes, terminal utilities, scenarios, sensitivity sweeps, regret/dominance checks, and value-of-information calculations. The agent uses it when a user faces staged choices under uncertainty and needs expected-utility rollback, policy extraction, and transparent assumptions about probabilities and outcomes.

## When to use this
<!-- id: raiffa/when-to-use -->

- The decision unfolds through choices, uncertain events, and terminal outcomes.
- Probabilities or probability ranges can be stated for chance events.
- Outcomes can be represented as utilities, monetary values, or a scalar preference measure.
- The user needs rollback, sensitivity, regret, dominance, scenario comparison, or value of information.

## When this is a stretch (and how to adapt)
<!-- id: raiffa/when-stretch -->

- The user has many non-commensurable criteria. Use [mcda](#mcda/mcda) to define utilities or compare terminal outcomes, then use raiffa only if staged uncertainty remains central.
- Probabilities are unknown. Use broad scenario/sensitivity ranges and report dependence on assumptions rather than inventing precision.
- The decision is a strategic futures exercise. Use [kahn](#kahn/kahn) for scenario narratives, then raiffa for a smaller probabilistic decision model.
- The outcome is primarily monetary cash flow. Use [dcf](#dcf/dcf) to estimate terminal values and raiffa to model staged decisions around them.
- The tree is too large. Collapse repeated subtrees, model only decision-relevant branches, or split the problem into phases.

## Decision rule for the calling agent
<!-- id: raiffa/decision-rule -->

Before dispatching to raiffa, confirm:

1. The decision includes at least one choice controlled by the decision maker.
2. At least one uncertain event affects the outcome.
3. Terminal outcomes can be assigned scalar utility or value.
4. The user wants a policy, sensitivity, regret, dominance, or information-value result.

If yes to the first three, raiffa is the right method.

## Inputs and elicitation
<!-- id: raiffa/inputs -->

### Decision structure
<!-- id: raiffa/inputs-structure -->

What it is: the sequence of decisions, chance events, and terminal outcomes.

How the agent elicits this:
- Ask: "What decision comes first, what can happen next, and what choices become available after that?"
- Separate actions controlled by the decision maker from uncertain events.
- Ask whether any branches are impossible or dominated before modeling.
- Give nodes stable IDs and human-readable branch labels.

Default to suggest: start with the smallest tree that captures the live decision, then add detail only where it can change the recommended policy.

Fallback: if the user thinks in scenarios, sketch a scenario table first and convert only actionable branches into the tree.

### Probabilities
<!-- id: raiffa/inputs-probabilities -->

What it is: probabilities on chance-node branches that sum to one at each chance node.

How the agent elicits this:
- Ask for best estimates and credible low/high ranges.
- Ask whether probabilities are subjective, empirical, market-implied, or expert-provided.
- Check that probabilities are conditional on the path to that chance node.

Default to suggest: use base-case probabilities plus sensitivity sweeps on the most uncertain branches.

Fallback: if probabilities are weak, run scenario analysis and value-of-information checks to show where better information matters.

### Utilities and outcomes
<!-- id: raiffa/inputs-utilities -->

What it is: scalar utility or value assigned to terminal nodes.

How the agent elicits this:
- Ask whether terminal outcomes are monetary, utility-scaled, or scored from another method.
- Ask whether risk neutrality is acceptable; if not, discuss utility transformation.
- Ask whether costs of information, delay, or implementation should be included.

Default to suggest: monetary value for financial decisions; normalized utility for mixed outcomes.

Fallback: use [mcda](#mcda/mcda) to score terminal outcomes when values are not naturally scalar.

## Outputs
<!-- id: raiffa/outputs -->

raiffa produces:

- `.raiffa/` project state with trees, nodes, probabilities, utilities, scenarios, and analysis snapshots.
- Expected-utility rollback results and optimal policy by decision node.
- Sensitivity sweeps over probability or utility parameters.
- Value-of-information calculations for chance events.
- Regret and dominance analysis across available actions.
- Exports such as JSON snapshots or diagram-friendly representations.

## Workflow
<!-- id: raiffa/workflow -->

Canonical sequence:

1. `raiffa init` — create the project.
2. `raiffa tree ...` — create or select the decision tree.
3. `raiffa node ...` — add decision, chance, and terminal nodes.
4. `raiffa prob ...` — assign probabilities to chance branches.
5. `raiffa utility ...` — assign terminal values.
6. `raiffa solve` — perform expected-utility rollback.
7. `raiffa sensitivity ...` — sweep key probabilities or utilities.
8. `raiffa voi ...` — compute value of information where relevant.
9. `raiffa regret` and `raiffa dominance` — inspect robustness of choices.
10. `raiffa scenario ...` and `raiffa analysis ...` — save and compare analysis states.
11. `raiffa export ...` — emit downstream artifacts.

Use `raiffa info` to recover current project state.

## Worked examples
<!-- id: raiffa/examples -->

### Settling or litigating
<!-- id: raiffa/example-settle-litigate -->

User: "Should we settle a dispute or litigate?"

Agent: "Raiffa fits because this is a choice under uncertainty. We need settlement cost, litigation win/loss probabilities, legal costs, and terminal payoffs. If the win probability is uncertain, I’ll run a sensitivity sweep."

User: "Settlement costs $400k. Litigation costs $150k. Win probability maybe 60%; winning saves $1M, losing costs $1.2M."

Agent: "I’ll build a decision node for settle vs litigate, a chance node for win/loss under litigation, solve expected value, then sweep win probability."

```bash
raiffa init dispute
raiffa tree create legal_dispute
raiffa node decision root --label "Settle or litigate"
raiffa node terminal settle --utility -400000
raiffa node chance trial --label "Trial outcome"
raiffa node terminal win --utility 850000
raiffa node terminal lose --utility -1350000
raiffa prob set trial win 0.60
raiffa prob set trial lose 0.40
raiffa solve
raiffa sensitivity run --parameter probability:trial.win --low 0.35 --high 0.80
```

Output: optimal policy, expected values, and a break-even probability view.

### Checking value of information
<!-- id: raiffa/example-voi -->

```bash
raiffa solve
raiffa voi run --chance-node demand
raiffa analysis list
```

Output: estimated value of learning the demand state before committing to a decision.

## Quick command reference
<!-- id: raiffa/commands -->

For full options, run `raiffa <subcommand> --help`.

| Command | Purpose |
|---|---|
| `raiffa init` / `info` | Initialize or summarize a project. |
| `raiffa tree ...` | Manage decision trees. |
| `raiffa node ...` | Add and inspect decision, chance, and terminal nodes. |
| `raiffa prob ...` | Set or inspect chance probabilities. |
| `raiffa utility ...` | Set terminal utilities or values. |
| `raiffa solve` | Run expected-utility rollback. |
| `raiffa sensitivity ...` | Sweep probability or utility parameters. |
| `raiffa voi ...` | Estimate value of information. |
| `raiffa regret` / `dominance` | Analyze robustness and dominated actions. |
| `raiffa scenario ...` | Manage scenario assumptions. |
| `raiffa analysis ...` | Inspect saved analysis snapshots. |
| `raiffa export ...` | Emit downstream artifacts. |
| `raiffa docs` | Read built-in guidance. |

## Common pitfalls
<!-- id: raiffa/pitfalls -->

- Probabilities at each chance node must be conditional on reaching that node and sum to one.
- Utilities should be comparable across terminal nodes; mixing dollars and ordinal scores breaks rollback.
- Large trees can obscure the live decision; model detail only where it can affect the optimal policy.
- Sensitivity is not optional when probabilities are subjective.
- Value of information must be compared to the cost and feasibility of acquiring that information.

## Cross-references
<!-- id: raiffa/xrefs -->

- Upstream: [dcf](#dcf/dcf) can provide monetary values for terminal outcomes; [kahn](#kahn/kahn) can identify plausible futures before probabilistic modeling.
- Adjacent methods: [mcda](#mcda/mcda) for non-commensurable criteria; [premortem](#premortem/premortem) for failure-mode discovery before modeling.
- Reporting: [gutenberg](#gutenberg/gutenberg), [herndon](#herndon/herndon), and [sonesta](#sonesta/sonesta) can package results.

## State contract
<!-- id: raiffa/state -->

`.raiffa/` stores project metadata, tree definitions, nodes, probabilities, utilities, scenarios, and analysis snapshots. Tree structure and assumptions are the source of truth; analysis outputs are reproducible from that state. Agents should modify tree state through CLI commands and rerun `raiffa solve` after assumption changes.

## JSON output and error codes
<!-- id: raiffa/json -->

raiffa uses structured output by default unless `--human` is requested. Common recoverable errors include invalid IDs, missing root/tree selection, incomplete probabilities, probabilities that do not sum to one, missing terminal utilities, unreachable nodes, and analysis precondition failures.
