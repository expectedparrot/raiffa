from __future__ import annotations

import typer

from raiffa.commands.common import ctx_project, output
from raiffa.core.errors import AnalysisError
from raiffa.core.model import branch_label, load_tree_model, subtree_model, solve_model


def command(ctx: typer.Context, tree_id: str, criterion: str = typer.Option("expected", "--criterion")) -> None:
    if criterion != "expected":
        raise AnalysisError("Only expected regret is implemented; minimax regret is not supported.", {"criterion": criterion})
    model = load_tree_model(ctx_project(ctx), tree_id)
    root_id = model.root_id
    if not root_id or model.nodes[root_id].get("type") != "decision":
        raise AnalysisError("V1 regret requires a decision root.", {"tree_id": tree_id})
    action_values = {child_id: solve_model(subtree_model(model, child_id))["root_value"] for child_id in model.children[root_id]}
    best = max(action_values.values())
    regrets = {action_id: best - value for action_id, value in action_values.items()}
    recommendation = min(regrets, key=regrets.get)
    output(
        ctx,
        {
            "tree_id": tree_id,
            "criterion": criterion,
            "action_values": action_values,
            "action_branch_labels": {action_id: branch_label(model, action_id) for action_id in action_values},
            "regrets": regrets,
            "recommendation": recommendation,
            "recommendation_branch_label": branch_label(model, recommendation),
        },
    )
