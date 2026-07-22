# Getting Started with Raiffa

This guide walks through a complete decision tree analysis from initialization to solve and sensitivity analysis. We'll model the classic "settle vs. trial" lawsuit decision.

## Installation

```bash
pip install -e /path/to/raiffa
raiffa --help
```

Or run without installing:

```bash
python -m raiffa.cli --help
```

## Step 0: Bootstrap (for agents)

If you are an agent starting a new session, run this first:

```bash
raiffa --project <path> agent-start
```

This returns your operating rules, the current project state, and recommended next steps in a single JSON payload. If `--project` is omitted, it uses the current directory.

## Step 1: Initialize the Project

```bash
raiffa init lawsuit_decision \
  --description "Should we settle the lawsuit for 2M or take it to trial?"
```

This creates `lawsuit_decision/.raiffa/` with the full project layout.

Check state:

```bash
raiffa --project lawsuit_decision info
```

## Step 2: Create a Decision Tree

```bash
raiffa --project lawsuit_decision tree add lawsuit "Lawsuit Settlement Decision"
```

## Step 3: Build the Tree Structure

Add a decision root node — the choice the decision-maker faces:

```bash
raiffa --project lawsuit_decision node add-decision lawsuit root_node "Settle or go to trial?"
```

Add chance nodes — one per action branch. Under "Settle": guaranteed outcome. Under "Trial": uncertain verdict.

```bash
# Settle branch leads directly to a terminal (no uncertainty)
raiffa --project lawsuit_decision node add-terminal lawsuit t_settle "Settle: pay 2M" \
  --parent root_node --branch-label "Settle" --utility 0.6

# Trial branch: uncertain verdict
raiffa --project lawsuit_decision node add-chance lawsuit verdict "Verdict" \
  --parent root_node --branch-label "Go to trial"
```

Add terminal nodes under the chance node:

```bash
raiffa --project lawsuit_decision node add-terminal lawsuit t_win "Win trial: pay nothing" \
  --parent verdict --branch-label "Win" --utility 1.0

raiffa --project lawsuit_decision node add-terminal lawsuit t_lose "Lose trial: pay 5M" \
  --parent verdict --branch-label "Lose" --utility 0.0
```

Review the tree:

```bash
raiffa --project lawsuit_decision --human tree show lawsuit
```

## Step 4: Set Probabilities

Each chance node's children must sum to 1.0:

```bash
raiffa --project lawsuit_decision prob set lawsuit verdict \
  t_win=0.40 t_lose=0.60
```

Verify:

```bash
raiffa --project lawsuit_decision prob show lawsuit verdict
```

## Step 5: Validate and Solve

Validate the model:

```bash
raiffa --project lawsuit_decision tree validate lawsuit
```

Solve for the optimal action:

```bash
raiffa --project lawsuit_decision solve lawsuit --show-policy
```

The output shows `recommended_branch_label` (optimal first action) and `root_value` (expected utility). With utilities 1.0, 0.6, and 0.0:
- EU(Settle) = 0.6
- EU(Trial) = 0.40 × 1.0 + 0.60 × 0.0 = 0.40

So settling is optimal at these probabilities.

## Step 6: Sensitivity Analysis

At what win probability does going to trial become better than settling?

```bash
raiffa --project lawsuit_decision sensitivity one-way lawsuit \
  --param probability:verdict.t_win --from 0.0 --to 1.0 --steps 21
```

The `thresholds` in the output show the crossover point. In this model, trial beats settle when P(win) > 0.6.

Find the exact threshold:

```bash
raiffa --project lawsuit_decision sensitivity threshold lawsuit \
  --param probability:verdict.t_win --between Settle "Go to trial"
```

## Step 7: Value of Information

How much would it be worth to know the verdict in advance?

```bash
raiffa --project lawsuit_decision voi evppi lawsuit --chance verdict
```

`expected_value_of_information` is the maximum you would pay for a perfect forecast of the trial outcome (measured in utility units). If you have a dollar-utility conversion, this tells you whether commissioning a legal expert's prediction is worth the fee.

## Step 8: Scenario Analysis

Model a more favorable legal environment:

```bash
raiffa --project lawsuit_decision scenario add lawsuit optimistic "Optimistic legal view"

raiffa --project lawsuit_decision scenario set-prob lawsuit optimistic verdict \
  t_win=0.65 t_lose=0.35

raiffa --project lawsuit_decision solve lawsuit --scenario optimistic
```

## Step 9: Export

`raiffa export` writes the rendered artifact to **stdout** by default — the
caller decides where it lands by redirecting:

```bash
# Mermaid diagram
raiffa --project lawsuit_decision export mermaid lawsuit > lawsuit.mmd

# Self-contained interactive HTML explorer (sliders for every probability
# and utility, live EU rollback, ranked results panel)
raiffa --project lawsuit_decision export explorer lawsuit > lawsuit_explorer.html
```

Both also accept `--output <path>` if you'd rather have the command write
the file directly; in that case stdout receives a small JSON confirmation
`{"data": {"output_path": "...", "tree_id": "..."}}` instead of the
artifact itself.

Open the HTML file in any browser; no server needed.

## Next Steps

- `raiffa docs show workflow` — detailed phase-by-phase reference
- `raiffa docs show best-practices` — quality standards and elicitation guidance
- `raiffa docs show cli-reference` — full command syntax
