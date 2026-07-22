# Raiffa Overview

Raiffa is a JSON-first CLI for decision tree analysis implementing Howard Raiffa's decision analysis methodology. It models decisions as trees with explicit probabilistic outcomes, rolls back expected utilities to find the optimal action, and quantifies the value of gathering more information.

## When to Use Raiffa

Use raiffa when the decision has:
- A small number of discrete actions (2-5 options at decision nodes)
- Uncertain outcomes that can be represented as probability distributions
- Outcomes whose desirability can be expressed as a scalar utility

| Decision type | Tool |
|---|---|
| Choose among alternatives on explicit criteria with stakeholder weights | `mcda` |
| Explore plausible future scenarios; stress-test strategic options | `kahn` |
| **Model a decision with explicit probabilistic outcomes; compute expected utility** | **raiffa** |

Key distinguisher: raiffa is for decisions where you can enumerate the actions, enumerate the chance outcomes, and assign probability and utility to each path through the tree.

## Core Concepts

### Node Types

A decision tree is a directed acyclic tree with three node types:

- **Decision node** (`type: decision`) — the decision-maker chooses one branch. The solver selects the branch with the highest expected utility.
- **Chance node** (`type: chance`) — nature resolves uncertainty. Each child has an assigned probability; probabilities must sum to 1.0.
- **Terminal node** (`type: terminal`) — the end of a path. Has an assigned utility (or payoff that converts to utility).

### Expected Utility Rollback

The solver walks the tree from leaves to root:
- At a terminal node: value = its utility.
- At a chance node: value = Σ (probability × child value) for each branch.
- At a decision node: value = max(child values); the argmax is the recommended action.

The output of `raiffa solve` is the root expected utility and the recommended first action (the policy).

### VNM Utility Scale

Terminal utilities should follow the von Neumann-Morgenstern (VNM) utility scale. The simplest approach:
1. Assign utility 0 to the worst outcome and utility 1 to the best.
2. For each intermediate outcome, elicit the probability p at which the decision-maker is indifferent between the certain intermediate outcome and a lottery [p × best, (1-p) × worst].
3. Assign utility p to that outcome.

For financial decisions where the decision-maker is approximately risk-neutral over the relevant range, utility ≈ normalized monetary value is a reasonable approximation.

### Project Layout

All state lives in a `.raiffa/` subdirectory within the project root:

```
<project_root>/
  .raiffa/
    meta.json
    trees/          # one JSON file per tree
    nodes/          # one JSON file per node
    scenarios/      # probability/utility overrides
    analyses/       # timestamped solve/sensitivity/voi results
    exports/
```

## Output Format

All commands emit JSON by default:

```json
{"data": {...}, "warnings": [...]}
```

Errors are emitted to stderr:

```json
{"error": {"code": "...", "message": "...", "details": {...}}}
```

Pass `--human` (as a global flag before the subcommand) for rich terminal output.

## ID Rules

All IDs (project IDs, tree IDs, node IDs, scenario IDs) must match `^[a-zA-Z_][a-zA-Z0-9_]*$`:
- Letters, digits, underscores only
- Must start with a letter or underscore
- No hyphens, no spaces, no leading digits

Good: `product_launch`, `settle_t1`, `high_demand`
Bad: `product-launch`, `2026_option`, `settle t1`

## The `--project` Flag

`--project` is a **global flag** that must appear **before** the subcommand:

```bash
raiffa --project path/to/dir solve main_decision   # correct
raiffa solve main_decision --project path/to/dir   # wrong — flag is ignored
```

## Next Steps

- `raiffa docs show getting-started` — complete worked example
- `raiffa docs show workflow` — phase-by-phase guide
- `raiffa docs show cli-reference` — all commands and flags
- `raiffa docs show best-practices` — quality standards and common pitfalls
