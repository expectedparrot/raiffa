from __future__ import annotations

import typer

from raiffa.commands.common import ctx_project, output
from raiffa.core.errors import UserError
from raiffa.core.model import load_tree_model
from raiffa.core.store import read_entity, write_json

app = typer.Typer(no_args_is_help=True, add_completion=False)


def parse_assignments(assignments: list[str]) -> dict[str, float]:
    parsed: dict[str, float] = {}
    for assignment in assignments:
        if "=" not in assignment:
            raise UserError("Expected probability assignment child=probability.", {"assignment": assignment})
        key, value = assignment.split("=", 1)
        try:
            parsed[key] = float(value)
        except ValueError as exc:
            raise UserError("Probability must be numeric.", {"assignment": assignment}) from exc
    return parsed


@app.command("set")
def set_cmd(ctx: typer.Context, tree_id: str, chance_node_id: str, assignments: list[str] = typer.Argument(...)) -> None:
    project = ctx_project(ctx)
    model = load_tree_model(project, tree_id)
    node = model.nodes.get(chance_node_id)
    if not node or node.get("type") != "chance":
        raise UserError("Chance node not found.", {"node_id": chance_node_id})
    probabilities = parse_assignments(assignments)
    node.update(read_entity(project, "nodes", chance_node_id))
    node["probabilities"] = probabilities
    write_json(project.path("nodes", f"{chance_node_id}.json"), node)
    output(ctx, node)


@app.command("clear")
def clear(ctx: typer.Context, tree_id: str, chance_node_id: str) -> None:
    project = ctx_project(ctx)
    node = read_entity(project, "nodes", chance_node_id)
    if node.get("tree_id") != tree_id or node.get("type") != "chance":
        raise UserError("Chance node not found.", {"tree_id": tree_id, "node_id": chance_node_id})
    node["probabilities"] = {}
    write_json(project.path("nodes", f"{chance_node_id}.json"), node)
    output(ctx, node)


@app.command("normalize")
def normalize(ctx: typer.Context, tree_id: str, chance_node_id: str) -> None:
    project = ctx_project(ctx)
    node = read_entity(project, "nodes", chance_node_id)
    if node.get("tree_id") != tree_id or node.get("type") != "chance":
        raise UserError("Chance node not found.", {"tree_id": tree_id, "node_id": chance_node_id})
    total = sum(float(value) for value in node.get("probabilities", {}).values())
    if total <= 0:
        raise UserError("Cannot normalize probabilities with nonpositive total.", {"node_id": chance_node_id, "sum": total})
    node["probabilities"] = {key: float(value) / total for key, value in node["probabilities"].items()}
    write_json(project.path("nodes", f"{chance_node_id}.json"), node)
    output(ctx, node)


@app.command("show")
def show(ctx: typer.Context, tree_id: str, chance_node_id: str) -> None:
    node = read_entity(ctx_project(ctx), "nodes", chance_node_id)
    if node.get("tree_id") != tree_id or node.get("type") != "chance":
        raise UserError("Chance node not found.", {"tree_id": tree_id, "node_id": chance_node_id})
    output(ctx, {"tree_id": tree_id, "node_id": chance_node_id, "probabilities": node.get("probabilities", {})})
