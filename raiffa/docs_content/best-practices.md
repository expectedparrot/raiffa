# Best Practices

Quality standards, elicitation guidance, and common pitfalls for raiffa decision analysis.

---

## Decision Framing

**Narrow the decision scope before building.** A vague question leads to a tree that tries to model everything and succeeds at nothing. Ask: "What specific action is being chosen, and by whom, by when?" If the answer spans multiple time periods or requires choosing from a continuously parameterized space, break it into separate analyses.

**One tree = one decision.** Model each distinct choice as a separate tree. Sequential decisions (where the second choice depends on the first choice's outcome) can be modeled in a single tree with multiple decision nodes, but only if you own both decisions.

**Separate pre-decision and post-decision uncertainty.** Chance nodes that precede the decision node should not appear in the tree — by definition, their outcome is already known when you decide. Only uncertainty that resolves *after* the decision belongs in the model.

---

## Tree Structure

**Keep depth ≤ 4.** Beyond 4 levels, probability errors compound and the tree becomes difficult to explain to stakeholders. If a deeper model is needed, consider folding sub-trees into aggregated utilities via certainty equivalents.

**2-4 branches per chance node.** Eliciting more than 5 probabilities for a single chance event reliably produces inconsistent estimates (probabilities don't reflect genuine beliefs). Collapse fine-grained outcomes into broader categories when building the model; you can use scenarios to explore finer distinctions.

**Every decision node needs ≥ 2 branches.** A decision node with one branch is not a decision.

**Validate early, validate often.** Run `tree validate` after every structural change. Do not set probabilities or solve until validation passes.

---

## Probability Elicitation

**Use structured elicitation, not casual estimation.** Asking "what probability would you assign?" directly produces anchored, poorly-calibrated estimates. Instead:
1. Ask the decision-maker to describe what a "high" outcome vs. a "low" outcome would look like.
2. Ask for the base rate from historical data or comparable cases.
3. Ask separately about factors that would push the probability up or down from the base rate.
4. Anchor to a reference class, then adjust.

**Consider EDSL surveys for systematic elicitation.** Build a `QuestionBudget` or `QuestionLinearScale` survey, deploy it via `.humanize()` for human respondents or run it against an AI agent panel for simulated stakeholders. Feed results into the model probabilities.

**Document probability sources.** Record whether each probability came from data, expert judgment, or a survey. Undocumented probabilities are the leading cause of model disputes during review.

**Test whether probabilities make intuitive sense.** After entering all probabilities, read the chance node's outcome description aloud with the assigned probability. If it feels wrong, investigate before solving.

---

## Utility Elicitation

**Use the VNM reference lottery method.** This is the only method guaranteed to produce utilities on a consistent interval scale. The shortcut of "rate on a 0-10 scale" produces ordinal preferences that can generate inconsistent rollback results.

**Assign 0 and 1 to actual outcomes, not to abstract endpoints.** If the worst outcome is "pay $5M and lose the case," utility 0 should correspond to that specific outcome. If the worst imaginable outcome is worse than anything in your tree, using it as the 0-anchor will compress your utility scale and make small differences invisible.

**Risk attitude matters.** A risk-neutral decision-maker can use normalized monetary values. A risk-averse decision-maker (common for large-stakes decisions) will assign higher utility to the certain middle outcome than its expected monetary value implies. If risk aversion is strong, elicit utilities explicitly rather than using monetary proxies.

**Be consistent across scenarios.** When you create scenario overrides for utilities, make sure the rationale is documented. A scenario that lowers the utility of "Win trial" because "winning doesn't really solve the reputation problem" should note that explicitly.

---

## ID Naming

All IDs must match `^[a-zA-Z_][a-zA-Z0-9_]*$`:
- Use short, descriptive snake_case names
- `verdict`, `market_reception`, `t_win`, `t_lose`, `pessimistic`
- Not: `2026-verdict`, `market-reception`, `T Win`

Tree IDs should describe the decision: `launch_timing`, `lawsuit`, `capacity_expansion`.

Node IDs should describe the node's role: `root_node`, `verdict`, `t_settle`, `t_win_high_damages`.

---

## Common Errors

**`prob set` fails with "Chance node not found"**
The node ID passed to `prob set` must be of type `chance`. Check: `raiffa --project <dir> node list <tree_id> --type chance`.

**Probabilities don't sum to 1.0**
If your source data gives you percentages that don't exactly sum to 100, use `prob normalize` to rescale proportionally.

**`solve` gives unexpected recommendation**
Before investigating the model, re-run `tree validate` — a structural error can produce nonsensical rollback values. If validation passes, check that utilities are on a consistent scale (not mixed: some normalized, some raw dollar amounts).

**`scenario set-prob` changes the wrong node**
The override key in a scenario is the chance node ID, not the tree ID. Verify with `scenario show <tree_id> <scenario_id>`.

**`--project` flag has no effect**
`--project` is a global flag that must appear before the subcommand. `raiffa --project ./dir solve ...` works; `raiffa solve ... --project ./dir` does not.

**`raiffa node update` says "No such command"**
There is no `node update`. Each kind of value has its own setter (see "Editing
existing values" below); the same setter is used both for the initial value
and for any later edit.

---

## Editing Existing Values

Raiffa has no generic `node update` / `node edit` command. Instead, each
kind of value has a dedicated setter, and the same setter is used both
for the initial value and for any later change:

| To change… | Use |
|---|---|
| A terminal's utility | `raiffa utility set <tree> <terminal> --utility <new>` |
| A terminal's monetary payoff | `raiffa utility payoff <tree> <terminal> --amount <v>` |
| A chance node's probabilities | `raiffa prob set <tree> <chance> <child>=<p> ...` |
| A node's display label | `raiffa node rename <tree> <node> '<new label>'` |
| A node's parent / branch label | `raiffa node move <tree> <node> --parent <p> --branch-label '<l>'` |
| A node's freeform note | `raiffa node annotate <tree> <node> --note '<text>'` |
| A scenario probability override | `raiffa scenario set-prob <tree> <scen> <chance> <c>=<p>` |
| A scenario utility override | `raiffa scenario set-utility <tree> <scen> <terminal> --utility <v>` |

The numeric value always goes through a flag (`--utility 0.10`,
`--amount 25000`), never as a positional. Probability assignments are the
only positional value-arguments, and they always use the `child_id=prob`
form.

If you need to remove a node entirely, use `raiffa node delete` (with
`--cascade` if it has descendants); there is no "set to nothing" affordance
for individual fields.

---

## Quality Checklist Before Reporting

- [ ] Every chance node has probabilities summing to 1.0 (`tree validate`)
- [ ] Every terminal node has a utility on a consistent scale
- [ ] The utility 0 and utility 1 anchors are explicitly documented
- [ ] `tree validate` passes with no warnings
- [ ] Sensitivity analysis run on the 2-3 most uncertain probabilities
- [ ] EVPPI computed for the key chance nodes
- [ ] At least one pessimistic scenario solved to test recommendation robustness
- [ ] Probability sources documented (data vs. judgment vs. survey)

---

## Next Steps

- `raiffa docs show workflow` — phase-by-phase guide
- `raiffa docs show cli-reference` — all commands and flags
