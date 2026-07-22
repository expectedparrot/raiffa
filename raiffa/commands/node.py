from __future__ import annotations

import typer

from raiffa.commands.common import ctx_project, output
from raiffa.core.errors import UserError
from raiffa.core.ids import local_iso_now, validate_id
from raiffa.core.store import delete_entity, list_entities, read_entity, write_entity, write_json

app = typer.Typer(no_args_is_help=True, add_completion=False)


def _add_node(ctx: typer.Context, tree_id: str, node_id: str, label: str, node_type: str, parent: str | None, branch_label: str | None, utility: float | None = None) -> None:
    validate_id(tree_id, "tree id")
    validate_id(node_id, "node id")
    project = ctx_project(ctx)
    tree = read_entity(project, "trees", tree_id)
    if parent is not None:
        read_entity(project, "nodes", parent)
    elif tree.get("root_node"):
        raise UserError("Only one root node is allowed. Provide --parent for non-root nodes.", {"tree_id": tree_id, "root_node": tree["root_node"]})
    data = {
        "id": node_id,
        "tree_id": tree_id,
        "type": node_type,
        "label": label,
        "description": "",
        "created_at": local_iso_now(),
        "parent": parent,
        "branch_label": branch_label,
        "metadata": {},
    }
    if node_type == "chance":
        data["probabilities"] = {}
    if node_type == "terminal":
        data["utility"] = utility
        data["attributes"] = {}
    write_entity(project, "nodes", node_id, data)
    if parent is None:
        tree["root_node"] = node_id
        write_json(project.path("trees", f"{tree_id}.json"), tree)
    output(ctx, data, human_message=f"Added {node_type} node {node_id}")


@app.command("add-decision")
def add_decision(ctx: typer.Context, tree_id: str, node_id: str, label: str, parent: str | None = typer.Option(None, "--parent"), branch_label: str | None = typer.Option(None, "--branch-label")) -> None:
    _add_node(ctx, tree_id, node_id, label, "decision", parent, branch_label)


@app.command("add-chance")
def add_chance(ctx: typer.Context, tree_id: str, node_id: str, label: str, parent: str = typer.Option(..., "--parent"), branch_label: str = typer.Option(..., "--branch-label")) -> None:
    _add_node(ctx, tree_id, node_id, label, "chance", parent, branch_label)


@app.command("add-terminal")
def add_terminal(
    ctx: typer.Context,
    tree_id: str,
    node_id: str,
    label: str,
    parent: str = typer.Option(..., "--parent"),
    branch_label: str = typer.Option(..., "--branch-label"),
    utility: float | None = typer.Option(None, "--utility", help="Optional. If omitted, set later via `raiffa utility set`."),
) -> None:
    # Utility is optional at creation time — the tree can be built first and
    # parameterized later. `tree validate` and `solve` will surface any
    # terminal still missing a utility.
    _add_node(ctx, tree_id, node_id, label, "terminal", parent, branch_label, utility)


@app.command("list")
def list_cmd(ctx: typer.Context, tree_id: str, node_type: str | None = typer.Option(None, "--type")) -> None:
    nodes = [node for node in list_entities(ctx_project(ctx), "nodes") if node.get("tree_id") == tree_id and (node_type is None or node.get("type") == node_type)]
    output(ctx, nodes)


@app.command("show")
def show(ctx: typer.Context, tree_id: str, node_id: str) -> None:
    node = read_entity(ctx_project(ctx), "nodes", node_id)
    if node.get("tree_id") != tree_id:
        raise UserError("Node does not belong to tree.", {"tree_id": tree_id, "node_id": node_id})
    output(ctx, node)


@app.command("move")
def move(ctx: typer.Context, tree_id: str, node_id: str, parent: str = typer.Option(..., "--parent"), branch_label: str = typer.Option(..., "--branch-label")) -> None:
    project = ctx_project(ctx)
    node = read_entity(project, "nodes", node_id)
    if node.get("tree_id") != tree_id:
        raise UserError("Node does not belong to tree.", {"tree_id": tree_id, "node_id": node_id})
    read_entity(project, "nodes", parent)
    node["parent"] = parent
    node["branch_label"] = branch_label
    write_json(project.path("nodes", f"{node_id}.json"), node)
    output(ctx, node)


@app.command("rename")
def rename(ctx: typer.Context, tree_id: str, node_id: str, label: str) -> None:
    project = ctx_project(ctx)
    node = read_entity(project, "nodes", node_id)
    if node.get("tree_id") != tree_id:
        raise UserError("Node does not belong to tree.", {"tree_id": tree_id, "node_id": node_id})
    node["label"] = label
    write_json(project.path("nodes", f"{node_id}.json"), node)
    output(ctx, node)


@app.command("annotate")
def annotate(ctx: typer.Context, tree_id: str, node_id: str, note: str = typer.Option(..., "--note")) -> None:
    project = ctx_project(ctx)
    node = read_entity(project, "nodes", node_id)
    if node.get("tree_id") != tree_id:
        raise UserError("Node does not belong to tree.", {"tree_id": tree_id, "node_id": node_id})
    node.setdefault("metadata", {})["note"] = note
    write_json(project.path("nodes", f"{node_id}.json"), node)
    output(ctx, node)


@app.command("delete")
def delete(ctx: typer.Context, tree_id: str, node_id: str, cascade: bool = typer.Option(False, "--cascade")) -> None:
    project = ctx_project(ctx)
    node = read_entity(project, "nodes", node_id)
    if node.get("tree_id") != tree_id:
        raise UserError("Node does not belong to tree.", {"tree_id": tree_id, "node_id": node_id})
    children = [item for item in list_entities(project, "nodes") if item.get("parent") == node_id]
    if children and not cascade:
        raise UserError("Node has children. Use --cascade to delete subtree.", {"node_id": node_id})
    for child in children:
        delete(ctx, tree_id, child["id"], cascade=True)
    delete_entity(project, "nodes", node_id)
    output(ctx, {"deleted": node_id})
