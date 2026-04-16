from __future__ import annotations

import json
import typer

from raiffa.commands.common import ctx_project, output
from raiffa.core.errors import ValidationError
from raiffa.core.ids import local_iso_now, validate_id
from raiffa.core.model import load_tree_model, validate_model
from raiffa.core.store import delete_entity, list_entities, read_entity, write_entity, write_json

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command("add")
def add(ctx: typer.Context, tree_id: str, name: str, description: str = typer.Option("", "--description")) -> None:
    validate_id(tree_id, "tree id")
    data = {
        "id": tree_id,
        "name": name,
        "description": description,
        "created_at": local_iso_now(),
        "status": "draft",
        "root_node": None,
        "settings": {"criterion": "expected_utility", "probability_tolerance": 1e-9, "utility_scale": "vnm", "default_scenario": "base"},
        "metadata": {},
    }
    write_entity(ctx_project(ctx), "trees", tree_id, data)
    output(ctx, data, human_message=f"Added tree {tree_id}")


@app.command("list")
def list_cmd(ctx: typer.Context) -> None:
    output(ctx, list_entities(ctx_project(ctx), "trees"))


@app.command("show")
def show(ctx: typer.Context, tree_id: str) -> None:
    project = ctx_project(ctx)
    model = load_tree_model(project, tree_id)
    output(ctx, {"tree": model.tree, "nodes": list(model.nodes.values())})


@app.command("validate")
def validate(ctx: typer.Context, tree_id: str, warnings_as_errors: bool = typer.Option(False, "--warnings-as-errors")) -> None:
    project = ctx_project(ctx)
    try:
        result = validate_model(load_tree_model(project, tree_id), warnings_as_errors=warnings_as_errors)
    except ValidationError as exc:
        typer.echo(json.dumps({"error": {"code": exc.code, "message": exc.message, "details": exc.details}}, indent=2, sort_keys=True), err=True)
        raise typer.Exit(exc.exit_code) from exc
    output(ctx, result, warnings=result.pop("warnings", []), human_message=f"Tree {tree_id} is valid")


@app.command("status")
def status(ctx: typer.Context, tree_id: str, status: str) -> None:
    if status not in {"draft", "ready", "locked", "archived"}:
        raise typer.BadParameter("Status must be draft, ready, locked, or archived.")
    project = ctx_project(ctx)
    data = read_entity(project, "trees", tree_id)
    data["status"] = status
    data[f"{status}_at"] = local_iso_now()
    write_json(project.path("trees", f"{tree_id}.json"), data)
    output(ctx, data, human_message=f"Set {tree_id} to {status}")


@app.command("delete")
def delete(ctx: typer.Context, tree_id: str) -> None:
    project = ctx_project(ctx)
    delete_entity(project, "trees", tree_id)
    output(ctx, {"deleted": tree_id})
