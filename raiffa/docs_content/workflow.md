# Decision Analysis Workflow

Raiffa implements Howard Raiffa's decision analysis method as a structured sequence of phases. Each phase builds on the previous; skipping a phase leads to incomplete or unreliable results.

## Phase Overview

```
frame → build → parameterize → solve → scenario → sensitivity → voi → export
```

---

## Phase 0: Decision Framing

Before touching the CLI, articulate the decision clearly.

**A well-framed decision question answers:**
- What action is the decision-maker choosing? (Specific and actionable)
- When must the decision be made? (Timing determines what information is available)
- What uncertainties resolve after the decision? (The structure of chance nodes)
- What values matter? (The basis for terminal utilities)

**Signs the framing is off:**
- "What is the best strategy?" — too broad; this is a planning question, not a decision. Use `kahn` instead.
- "Which vendor is better on cost, reliability, and support?" — multi-criteria. Use `mcda` instead.
- "How should we respond to this situation?" — not actionable. Narrow to a specific choice.

**Good framing examples:**
- "Should we settle this lawsuit now for $2M or take it to trial?"
- "Should we launch the product in Q3 or delay to Q4 for a feature enhancement?"
- "Should we invest $500K in capacity expansion given uncertain demand?"

**Initialize:**

```bash
raiffa init <project_id> --description "<decision question>"
```

---

## Phase 1: Tree Construction

Model the decision as a tree. Each root-to-leaf path represents one possible sequence of choices and chance outcomes.

### Node Type Rules

| Node type | Who controls it | Has probabilities | Has utility | Min children |
|---|---|---|---|---|
| Decision | Decision-maker | No | No | 2 |
| Chance | Nature | Yes (sum to 1.0) | No | 2 |
| Terminal | — | No | Yes (scalar) | 0 |

### Structural Guidelines

- The root is always a decision node — the choice being analyzed.
- Decision nodes appear where the decision-maker acts; chance nodes where nature resolves uncertainty.
- Keep trees to ≤4 levels when possible. Deeper trees are harder to validate and more sensitive to parameter errors.
- 2-4 branches per chance node is ideal. More than 5 makes probability elicitation unreliable.
- Every leaf must be a terminal node.

### Build Commands

```bash
# Create the tree record
raiffa --project <dir> tree add <tree_id> '<Decision title>'

# Add root decision node
raiffa --project <dir> node add-decision <tree_id> root_node '<What should we do?>'

# Add chance node for each action branch
raiffa --project <dir> node add-chance <tree_id> <chance_id> '<Uncertainty name>' \
  --parent root_node --branch-label '<action label>'

# Add terminal nodes (--utility is optional; can be set later)
raiffa --project <dir> node add-terminal <tree_id> <terminal_id> '<outcome name>' \
  --parent <chance_id> --branch-label '<outcome label>' [--utility <value>]

# Validate before proceeding
raiffa --project <dir> tree validate <tree_id>
```

`tree validate` checks: root exists, all chance nodes have ≥2 children, all terminal nodes have utility, no orphaned nodes. If you build the tree skeleton first and parameterize later, expect `tree validate` to flag the missing utilities until you set them with `raiffa utility set`.

---

## Phase 2: Parameterization

Two types of parameters must be set: **probabilities** on every chance node and **utilities** on every terminal node.

### Setting Probabilities

```bash
raiffa --project <dir> prob set <tree_id> <chance_node_id> \
  <child1_id>=<prob1> <child2_id>=<prob2>
```

Probabilities must sum to 1.0 (tolerance: 1e-9). If they don't sum exactly:

```bash
raiffa --project <dir> prob normalize <tree_id> <chance_node_id>
```

**Sources for probabilities:**
- Published base rates (historical data, industry reports)
- Expert judgment (elicit carefully — see Best Practices)
- Structured EDSL surveys deployed via humanize or run against AI agent panels

Do not invent probabilities without a basis. Uncertain parameters are candidates for VOI analysis.

### Setting Utilities

Use the VNM elicitation method:
1. Assign utility 0 to the worst terminal outcome and utility 1 to the best.
2. For each intermediate outcome, find the probability p at which the decision-maker is indifferent between the certain intermediate outcome and a lottery between best and worst.
3. Assign utility p to that outcome.

For financial decisions with approximately risk-neutral preferences, utility ≈ normalized monetary value is acceptable.

```bash
# Set utility directly
raiffa --project <dir> utility set <tree_id> <terminal_id> --utility <value>

# Record the monetary payoff alongside utility
raiffa --project <dir> utility payoff <tree_id> <terminal_id> --amount <value> --currency USD

# Review all terminal utilities
raiffa --project <dir> utility list <tree_id>
```

**Editing existing values.** There is no `node update` command. To change a value
after a node has been created, use the value-specific setter for that field:

| To change… | Use |
|---|---|
| A terminal's utility | `raiffa utility set <tree> <terminal> --utility <new>` |
| A chance node's probabilities | `raiffa prob set <tree> <chance> <child>=<p> ...` |
| A node's display label | `raiffa node rename <tree> <node> '<new label>'` |
| A node's parent / branch label | `raiffa node move <tree> <node> --parent <p> --branch-label '<l>'` |

The same setters work for both the initial value and any later edit. The value
argument is always passed as a flag (e.g. `--utility 0.10`), never as a
positional, and IDs use underscores not hyphens (`t_pod_flop`, not `t-pod-flop`).

---

## Phase 3: Base Solve

Once parameterized and validated, solve for the optimal policy.

```bash
raiffa --project <dir> solve <tree_id>
raiffa --project <dir> solve <tree_id> --show-policy --explain
```

**Output fields:**
- `recommended_branch_label` — the optimal first action
- `root_value` — expected utility of the optimal policy
- `rollback` — map of node_id → expected utility (or chosen EU for decision nodes)
- `policy` — full policy: optimal action at every decision node (with `--show-policy`)

**Interpretation:**
- If root-value differences between actions are < 0.05 on a [0,1] scale, the decision is close — proceed to sensitivity analysis before concluding.
- If one action clearly dominates (difference > 0.15), verify the parameters are reasonable.
- Use `dominance` to check whether any action is weakly dominated:

```bash
raiffa --project <dir> dominance <tree_id>
```

- Use `regret` as a minimax-regret alternative when probability estimates are highly uncertain:

```bash
raiffa --project <dir> regret <tree_id>
```

---

## Phase 4: Scenario Analysis

Scenarios modify probabilities or utilities without changing the tree structure. They answer "what if our assumptions were different?"

```bash
# Create a named scenario
raiffa --project <dir> scenario add <tree_id> <scenario_id> '<name>'

# Override probabilities in this scenario
raiffa --project <dir> scenario set-prob <tree_id> <scenario_id> <chance_id> \
  <child1>=<prob1> <child2>=<prob2>

# Override a terminal utility in this scenario
raiffa --project <dir> scenario set-utility <tree_id> <scenario_id> <terminal_id> \
  --utility <new_value>

# Solve under the scenario
raiffa --project <dir> solve <tree_id> --scenario <scenario_id>

# Compare two scenarios' overrides
raiffa --project <dir> scenario diff <tree_id> <scenario_a> <scenario_b>
```

**Useful scenario types:**
- **Pessimistic** — lower all favorable probabilities by 20-30%
- **Optimistic** — raise all favorable probabilities by 20-30%
- **Alternative stakeholder** — use a different utility function
- **Post-information** — set the uncertain outcome to a specific resolved state (P=1) to compute the regret-free value

---

## Phase 5: Sensitivity Analysis

One-way sensitivity shows how the expected utility of each action responds as a single parameter varies.

```bash
raiffa --project <dir> sensitivity one-way <tree_id> \
  --param probability:<chance_node_id>.<child_id> \
  --from 0.0 --to 1.0 --steps 21
```

**Output includes:**
- `samples` — list of {value, root_value, recommended_action, recommended_branch_label} across the range
- `thresholds` — parameter values at which the optimal action switches

Find a specific crossover:

```bash
raiffa --project <dir> sensitivity threshold <tree_id> \
  --param probability:<chance_node_id>.<child_id> \
  --between "<action_a_label>" "<action_b_label>"
```

`--between` is order-insensitive. Empty `thresholds: []` means no transition
between those two actions occurs in the swept range — widen `--from` /
`--to`, or run `sensitivity one-way` to see the full curve.

**What to test:**
- Any probability where your base-case estimate could plausibly shift ±10-20%
- Terminal utilities for outcomes you're uncertain how to value
- If the threshold is far from your base-case estimate, the recommendation is robust to that parameter

---

## Phase 6: Value of Information

VOI analysis answers: "Is it worth gathering more information before deciding?"

**EVPPI** — Expected Value of Perfect Partial Information for a specific chance node:

```bash
raiffa --project <dir> voi evppi <tree_id> --chance <chance_node_id>
```

**EVPI** — Expected Value of Perfect Information (all uncertainties combined):

```bash
raiffa --project <dir> voi evpi <tree_id>
```

**Interpretation:**
- If EVPPI for a node is near zero, that uncertainty doesn't drive the decision — don't invest in resolving it.
- If EVPPI > the cost of an information-gathering activity (survey, pilot, study), gathering information is economically justified.
- Comparing EVPPI values across chance nodes reveals which uncertainty to prioritize.

EVPI is the theoretical upper bound on what any information source could be worth. A real information source can never be worth more than EVPI.

---

## Phase 7: Export and Reporting

`raiffa export` commands write the rendered artifact (raw Mermaid markdown,
the JSON envelope, or a self-contained HTML explorer) to **stdout** by
default. Routing is the caller's responsibility — there is no implicit
filesystem default. Redirect into the right place for whatever workflow
you're in:

```bash
# Mermaid diagram for visualization
raiffa --project <dir> export mermaid <tree_id> > writeup/tree.mmd

# Full JSON export (unwrapped tree+nodes if --output is given;
# the standard envelope on stdout otherwise)
raiffa --project <dir> export json <tree_id> > data/tree.json

# Self-contained interactive HTML explorer
raiffa --project <dir> export explorer <tree_id> > writeup/tree_explorer.html
```

Both forms accept `--output <path>` if you'd rather have the command write
the file directly; stdout then gets a confirmation envelope
`{"output_path": "...", "tree_id": "..."}` rather than the artifact body.

```bash
# Review analysis history (these stay in `.raiffa/analyses/` — internal state)
raiffa --project <dir> analysis list <tree_id>
raiffa --project <dir> analysis show <analysis_id>
```

---

## Next Steps

- `raiffa docs show best-practices` — quality standards, elicitation guidance, common pitfalls
- `raiffa docs show cli-reference` — full command syntax reference
