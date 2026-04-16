from __future__ import annotations

import typer

from raiffa.commands.common import ctx_project, output
from raiffa.core.errors import UserError
from raiffa.core.store import list_entities, read_entity, write_json

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command("set")
def set_cmd(ctx: typer.Context, tree_id: str, terminal_node_id: str, utility: float = typer.Option(..., "--utility")) -> None:
    project = ctx_project(ctx)
    node = read_entity(project, "nodes", terminal_node_id)
    if node.get("tree_id") != tree_id or node.get("type") != "terminal":
        raise UserError("Terminal node not found.", {"tree_id": tree_id, "node_id": terminal_node_id})
    node["utility"] = utility
    write_json(project.path("nodes", f"{terminal_node_id}.json"), node)
    output(ctx, node)


@app.command("payoff")
def payoff(ctx: typer.Context, tree_id: str, terminal_node_id: str, amount: float = typer.Option(..., "--amount"), currency: str = typer.Option("USD", "--currency")) -> None:
    project = ctx_project(ctx)
    node = read_entity(project, "nodes", terminal_node_id)
    if node.get("tree_id") != tree_id or node.get("type") != "terminal":
        raise UserError("Terminal node not found.", {"tree_id": tree_id, "node_id": terminal_node_id})
    node["payoff"] = {"amount": amount, "currency": currency}
    write_json(project.path("nodes", f"{terminal_node_id}.json"), node)
    output(ctx, node)


@app.command("show")
def show(ctx: typer.Context, tree_id: str, terminal_node_id: str) -> None:
    node = read_entity(ctx_project(ctx), "nodes", terminal_node_id)
    if node.get("tree_id") != tree_id or node.get("type") != "terminal":
        raise UserError("Terminal node not found.", {"tree_id": tree_id, "node_id": terminal_node_id})
    output(ctx, {"tree_id": tree_id, "node_id": terminal_node_id, "utility": node.get("utility"), "payoff": node.get("payoff")})


@app.command("list")
def list_cmd(ctx: typer.Context, tree_id: str) -> None:
    nodes = [
        {"node_id": node["id"], "label": node.get("label"), "utility": node.get("utility"), "payoff": node.get("payoff")}
        for node in list_entities(ctx_project(ctx), "nodes")
        if node.get("tree_id") == tree_id and node.get("type") == "terminal"
    ]
    output(ctx, nodes)
