# LEG-01: settle, litigate, or research first?

For the complete walkthrough with runnable commands, diagrams, and an interactive
threshold preview, open [the browser tutorial](../../docs/index.html).

This is a synthetic validation example, not a real case or an empirically sourced
legal recommendation. Every input is a named assumption. The original 57-item
benchmark dataset has not been supplied; the LEG-01 label follows the proposed
specification and does not claim fidelity to an unseen case description.

The defendant can settle for $400,000 or litigate. Litigation always costs
$150,000; losing adds $1,200,000 of damages. The win probability is 0.60. All
payoffs are on one valuation date, and the decision maker is risk neutral.

From a cloned checkout, install and run:

```bash
python -m pip install -e '.[dev]'
raiffa init lawsuit
raiffa --project lawsuit model import --file examples/leg01/model.json
raiffa --project lawsuit model validate leg01 --strict
raiffa --project lawsuit solve leg01
raiffa --project lawsuit sensitivity one-way leg01 --param p_win --from 0 --to 1
raiffa --project lawsuit voi perfect leg01 --targets win
raiffa --project lawsuit voi sample leg01 --study case_review
raiffa --project lawsuit research agenda leg01
raiffa --project lawsuit next
```

`next` returns the concrete `report` command containing the saved solve analysis
ID. Run that command to produce `lawsuit/leg01-decision.html`, then run `next`
again. The report contains diagrams, the policy, exact discrete risk profiles,
switching conditions, information values, and parameter provenance. Use
`--format svg` for the influence diagram or `--format json` for the frozen data.

| Check | Expected result |
| --- | --- |
| Expected payoff from settlement | -$400,000 |
| Expected payoff from litigation | -$630,000 |
| Recommended immediate action | Settle |
| Win probability at indifference | 19/24 ≈ 0.7916667 |
| Damages at indifference, holding p = 0.60 | $625,000 |
| Perfect outcome information, before deciding | $150,000 gross value |
| Synthetic case-review study | $44,000 gross value; $34,000 net value |

The switching boundary is `legal_cost + (1 - p_win) * damages = settlement`.
Separate one-way thresholds hold other literal parameters fixed. They are not
independent conditions that can safely be combined for simultaneous changes.

The study reports favorable with probability 0.80 when a win would occur and
0.20 when a loss would occur. Its cost is $10,000, it has no delay cost, and the
settlement offer remains available. After favorable results, litigate; after
unfavorable results, settle. These likelihoods are assumptions, not estimates
of how a real legal study performs.

## Explicit sequential decision

The second fixture includes a first decision to purchase the study or act now,
a signal that is uninformative when no study is purchased, and a later
settle/litigate decision. The hidden trial outcome never becomes observable.

```bash
raiffa --project lawsuit model import --file examples/leg01/sequential.json
raiffa --project lawsuit solve leg01_sequential
raiffa --project lawsuit model compile leg01_sequential --output lawsuit/sequential-tree.json
raiffa --project lawsuit next leg01_sequential
```

The optimal policy purchases the study, then acts on its signal, for expected
payoff **-$366,000**, including the study cost. Raising the study cost to $50,000
makes acting now preferable. The finite solver enforces identical actions at
indistinguishable histories, including in the exported compiled tree.

## Update a belief and explain the change

Copy `model.json`, change `p_win.value` from 0.60 to 0.85, and retain or revise its
provenance rationale. Then:

```bash
raiffa --project lawsuit model revise leg01 --file revised-model.json --reason "Updated win assessment"
raiffa --project lawsuit solve leg01
raiffa --project lawsuit analysis list leg01
raiffa --project lawsuit analysis compare BEFORE_ANALYSIS_ID AFTER_ANALYSIS_ID
raiffa --project lawsuit analysis replay BEFORE_ANALYSIS_ID
raiffa --project lawsuit doctor
```

The no-study recommendation flips to litigate, with expected payoff -$330,000.
The comparison reports the parameter change and a counterfactual re-solve.
The old analysis remains reproducible and the new revision requires new checks.

For a local proposed handoff, use:

```bash
raiffa --project lawsuit handoff ANALYSIS_ID --target vorhersage --output lawsuit/monitoring.json
```

The file records the policy and current threshold analyses. It does not contact
Vorhersage, publish a forecast, or imply that receiver-side import is implemented.
