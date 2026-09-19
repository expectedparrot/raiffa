# CLI Quick Reference

This page describes legacy tree commands. For provenance-aware finite models,
start with `raiffa guide`, `raiffa model schema`, and `raiffa next`.

> **Two things to remember before every command:**
>
> 1. **`--project` is a global flag — it goes BEFORE the subcommand.**
>    - Correct: `raiffa --project path/to/dir solve my_tree`
>    - Wrong: `raiffa solve my_tree --project path/to/dir`
>
> 2. **IDs must match `^[a-zA-Z_][a-zA-Z0-9_]*$`** — letters, digits, underscores only; must start with a letter or underscore.

---

## Global Options

These flags apply to every command and must appear before the subcommand:

```
--project PATH     Override the project root directory
--human            Rich human-readable output instead of JSON
--quiet            Suppress non-data output in human mode
```

---

## Project Commands

### `raiffa init <name>`

Initialize a new project.

```bash
raiffa init <project_id> [--here] [--title '<title>'] [--description '<text>']
```

Creates `.raiffa/` with the full directory layout.
Without `--here`, the project root is a new `<project_id>/` subdirectory.
With `--here`, `.raiffa/` is created in the current directory and `<project_id>` is used only as the internal project ID.

### `raiffa info`

Show project metadata and artifact counts.

```bash
raiffa --project <dir> info
```

### `raiffa next` / `raiffa status`

Inspect the finite model workflow and its next required action. Use `raiffa guide`
for operating rules; these commands do not infer provenance for legacy trees.

```bash
raiffa --project <dir> next [model_id]
```

---

## Tree Commands (`raiffa tree`)

### `raiffa tree add <tree_id> <name>`

Create a new tree record.

```bash
raiffa --project <dir> tree add <tree_id> '<name>' [--description '<text>']
```

### `raiffa tree list`

List all trees in the project.

```bash
raiffa --project <dir> tree list
```

### `raiffa tree show <tree_id>`

Show the tree and all its nodes.

```bash
raiffa --project <dir> tree show <tree_id>
```

### `raiffa tree validate <tree_id>`

Validate the tree structure (root exists, probabilities complete, terminals have utilities).

```bash
raiffa --project <dir> tree validate <tree_id> [--warnings-as-errors]
```

### `raiffa tree status <tree_id> <status>`

Set the tree lifecycle status: `draft`, `ready`, `locked`, `archived`.

```bash
raiffa --project <dir> tree status <tree_id> ready
```

### `raiffa tree delete <tree_id>`

Delete a tree record.

```bash
raiffa --project <dir> tree delete <tree_id>
```

---

## Node Commands (`raiffa node`)

### `raiffa node add-decision <tree_id> <node_id> <label>`

Add a decision node.

```bash
raiffa --project <dir> node add-decision <tree_id> <node_id> '<label>' \
  [--parent <parent_id>] [--branch-label '<label>']
```

Omit `--parent` only for the root node.

### `raiffa node add-chance <tree_id> <node_id> <label>`

Add a chance node.

```bash
raiffa --project <dir> node add-chance <tree_id> <node_id> '<label>' \
  --parent <parent_id> --branch-label '<label>'
```

### `raiffa node add-terminal <tree_id> <node_id> <label>`

Add a terminal (leaf) node.

```bash
raiffa --project <dir> node add-terminal <tree_id> <node_id> '<label>' \
  --parent <parent_id> --branch-label '<label>' [--utility <float>]
```

`--utility` is optional. If omitted, the terminal is created with a
null utility; set it later with `raiffa utility set <tree> <node> --utility <v>`.
Either way, `tree validate` and `solve` will surface any terminal that is
still missing a utility before they will run.

### `raiffa node list <tree_id>`

List nodes in a tree, optionally filtered by type.

```bash
raiffa --project <dir> node list <tree_id> [--type decision|chance|terminal]
```

### `raiffa node show <tree_id> <node_id>`

Show a specific node.

### `raiffa node rename <tree_id> <node_id> <new_label>`

Update a node's display label.

### `raiffa node annotate <tree_id> <node_id>`

Attach a freeform note to a node.

```bash
raiffa --project <dir> node annotate <tree_id> <node_id> --note '<text>'
```

### `raiffa node move <tree_id> <node_id>`

Re-parent a node.

```bash
raiffa --project <dir> node move <tree_id> <node_id> \
  --parent <new_parent_id> --branch-label '<new_label>'
```

### `raiffa node delete <tree_id> <node_id>`

Delete a node. Use `--cascade` to also delete its subtree.

```bash
raiffa --project <dir> node delete <tree_id> <node_id> [--cascade]
```

---

## Probability Commands (`raiffa prob`)

### `raiffa prob set <tree_id> <chance_node_id> [assignments...]`

Set probabilities on a chance node. Each assignment is `child_id=probability`.

```bash
raiffa --project <dir> prob set <tree_id> <chance_id> t_high=0.4 t_low=0.6
```

Probabilities are stored as-is; they must sum to 1.0 (tolerance 1e-9) for solve to succeed.

### `raiffa prob normalize <tree_id> <chance_node_id>`

Rescale stored probabilities to sum to 1.0.

### `raiffa prob show <tree_id> <chance_node_id>`

Show current probability assignments.

### `raiffa prob clear <tree_id> <chance_node_id>`

Clear all probability assignments on a chance node.

---

## Utility Commands (`raiffa utility`)

### `raiffa utility set <tree_id> <terminal_node_id>`

Set the utility of a terminal node.

```bash
raiffa --project <dir> utility set <tree_id> <terminal_id> --utility 0.75
```

### `raiffa utility payoff <tree_id> <terminal_node_id>`

Record a monetary payoff alongside the utility.

```bash
raiffa --project <dir> utility payoff <tree_id> <terminal_id> --amount 2500000 --currency USD
```

### `raiffa utility show <tree_id> <terminal_node_id>`

Show utility and payoff for a terminal node.

### `raiffa utility list <tree_id>`

List all terminal nodes with their utility and payoff values.

---

## Solve and Analysis Commands

### `raiffa solve <tree_id>`

Compute the expected-utility rollback. Returns the recommended first action and root expected utility.

```bash
raiffa --project <dir> solve <tree_id> \
  [--scenario <scenario_id>] \
  [--show-policy] \
  [--explain] \
  [--no-write]
```

### `raiffa dominance <tree_id>`

Identify weakly dominated actions at the decision root.

```bash
raiffa --project <dir> dominance <tree_id>
```

### `raiffa regret <tree_id>`

Compute minimax-regret recommendation at the decision root.

```bash
raiffa --project <dir> regret <tree_id>
```

---

## Scenario Commands (`raiffa scenario`)

### `raiffa scenario add <tree_id> <scenario_id> <name>`

Create a named scenario (stores probability/utility overrides).

```bash
raiffa --project <dir> scenario add <tree_id> <scenario_id> '<name>' [--description '<text>']
```

### `raiffa scenario list <tree_id>`

List all scenarios for a tree.

### `raiffa scenario show <tree_id> <scenario_id>`

Show a scenario's overrides.

### `raiffa scenario set-prob <tree_id> <scenario_id> <chance_node_id> [assignments...]`

Override probabilities in a scenario.

```bash
raiffa --project <dir> scenario set-prob <tree_id> pessimistic market_chance \
  t_high=0.2 t_low=0.8
```

### `raiffa scenario set-utility <tree_id> <scenario_id> <terminal_node_id>`

Override a terminal utility in a scenario.

```bash
raiffa --project <dir> scenario set-utility <tree_id> pessimistic t_win --utility 0.7
```

### `raiffa scenario diff <tree_id> <scenario_a> <scenario_b>`

Show the difference between two scenarios' overrides.

### `raiffa scenario delete <tree_id> <scenario_id>`

Delete a scenario.

---

## Sensitivity Commands (`raiffa sensitivity`)

### `raiffa sensitivity one-way <tree_id>`

Sweep one parameter over a range and compute action expected utilities at each step.

```bash
raiffa --project <dir> sensitivity one-way <tree_id> \
  --param probability:<chance_node_id>.<child_id> \
  --from <float> --to <float> \
  [--steps <int>]           # default 11
  [--no-write]
```

Output includes `samples` (sampled values plus the current recommendation) and `thresholds` (crossover points between actions).

### `raiffa sensitivity threshold <tree_id>`

Find the exact threshold between two specific actions.

```bash
raiffa --project <dir> sensitivity threshold <tree_id> \
  --param probability:<chance_node_id>.<child_id> \
  --between "<action_a_branch_label>" "<action_b_branch_label>" \
  [--from 0.0] [--to 1.0] [--steps 101]
```

`--between` is **order-insensitive**: it matches any transition whose two
endpoints equal the two named branch labels, regardless of which way the
recommendation flips. Empty `thresholds: []` means *no such transition occurs
within `[--from, --to]`* — try widening the range, or run
`sensitivity one-way` to see the full curve and confirm the recommendation
never changes across the swept range.

---

## Value of Information Commands (`raiffa voi`)

### `raiffa voi evppi <tree_id>`

Expected Value of Perfect Partial Information for a specific chance node.

```bash
raiffa --project <dir> voi evppi <tree_id> --chance <chance_node_id> [--no-write]
```

Output includes `expected_value_of_information` (in utility units).

### `raiffa voi evpi <tree_id>`

Expected Value of Perfect Information across all chance nodes.

```bash
raiffa --project <dir> voi evpi <tree_id> [--chance <chance_node_id>] [--no-write]
```

---

## Analysis Commands (`raiffa analysis`)

### `raiffa analysis list [tree_id]`

List stored analysis results, optionally filtered by tree.

```bash
raiffa --project <dir> analysis list [<tree_id>]
```

### `raiffa analysis show <analysis_id>`

Show a specific analysis result.

### `raiffa analysis delete <analysis_id>`

Delete a stored analysis result.

---

## Export Commands (`raiffa export`)

> **Convention.** All `raiffa export` commands write the rendered artifact
> to **stdout** when `--output` is omitted, so the caller can redirect
> (`> path/to/file`) or pipe to another tool. When `--output <path>` *is*
> given, the artifact is written to that file and a small JSON envelope
> `{"data": {"output_path": "...", "tree_id": "..."}}` confirms the write
> on stdout. Errors continue to go to stderr as JSON.
>
> There is no implicit default filesystem location: routing is the caller's
> responsibility. When running inside a macaw task scaffold, redirect into
> the task's `writeup/` directory; standalone, redirect anywhere you like.
>
> ```bash
> raiffa --project . export mermaid  podcast > writeup/podcast_tree.mmd
> raiffa --project . export explorer podcast > writeup/podcast_explorer.html
> raiffa --project . export json     podcast > data/podcast_tree.json
> ```

### `raiffa export json <tree_id>`

Export the tree and nodes as JSON. With no `--output`, the standard
`{"data": {tree, nodes}, "warnings": []}` envelope is written to stdout
(consistent with other raiffa commands). With `--output`, the *unwrapped*
`{tree, nodes}` body is written to the file and a confirmation envelope
goes to stdout.

```bash
raiffa --project <dir> export json <tree_id> [--output <path>]
```

### `raiffa export mermaid <tree_id>`

Export the tree as a Mermaid diagram. Raw Mermaid markdown is written
to stdout when `--output` is omitted; with `--output`, written to the
file and a confirmation envelope goes to stdout.

```bash
raiffa --project <dir> export mermaid <tree_id> [--output <path.mmd>]
```

### `raiffa export explorer <tree_id>`

Generate a self-contained interactive HTML explorer. Opens in any browser
— sliders let you adjust every probability and utility in real time, the
decision tree diagram updates live, and a rankings panel shows the
expected utility of each root-level option.

Raw HTML is written to stdout when `--output` is omitted; with `--output`,
written to the file and a confirmation envelope goes to stdout.

```bash
raiffa --project <dir> export explorer <tree_id> [--output <path.html>]
```

---

## Docs Commands (`raiffa docs`)

### `raiffa docs list`

List available documentation topics.

### `raiffa docs show <topic>`

Show a documentation topic as markdown (JSON) or rendered (--human).

```bash
raiffa docs show overview
raiffa docs show getting-started
raiffa docs show workflow
raiffa docs show cli-reference
raiffa docs show best-practices
```

### `raiffa docs search <query>`

Search documentation for a keyword or phrase.

```bash
raiffa docs search "sensitivity analysis"
raiffa docs search "probability elicitation"
```
