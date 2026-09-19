from __future__ import annotations

import typer

from raiffa.commands.common import ctx_project, output
from raiffa.core.model import load_tree_model, solve_model


def command(ctx: typer.Context, tree_id: str) -> None:
    from raiffa.decision.cli import is_decision_model, store_for
    from raiffa.decision.engine import dominance, solve
    if is_decision_model(ctx, tree_id):
        entry, model = store_for(ctx).load(tree_id, strict=True)
        output(ctx, {"model_revision": entry["revision"], **dominance(solve(model))})
        return
    result = solve_model(load_tree_model(ctx_project(ctx), tree_id))
    zero_probability = []
    model = load_tree_model(ctx_project(ctx), tree_id)
    for node_id, node in model.nodes.items():
        if node.get("type") == "chance":
            zero_probability.extend({"node_id": node_id, "child_id": child_id} for child_id, p in node.get("probabilities", {}).items() if p == 0)
    output(ctx, {"tree_id": tree_id, "dominated_branches": result["dominated_branches"], "zero_probability_branches": zero_probability})
