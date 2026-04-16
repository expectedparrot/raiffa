from __future__ import annotations

import typer

from raiffa.commands.common import ctx_project, output
from raiffa.commands.prob import parse_assignments
from raiffa.core.errors import UserError
from raiffa.core.ids import local_iso_now, validate_id
from raiffa.core.store import delete_entity, list_entities, read_entity, write_entity, write_json

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command("add")
def add(ctx: typer.Context, tree_id: str, scenario_id: str, name: str, description: str = typer.Option("", "--description")) -> None:
    validate_id(scenario_id, "scenario id")
    read_entity(ctx_project(ctx), "trees", tree_id)
    data = {"id": scenario_id, "tree_id": tree_id, "name": name, "description": description, "created_at": local_iso_now(), "overrides": {"probabilities": {}, "utilities": {}}}
    write_entity(ctx_project(ctx), "scenarios", scenario_id, data)
    output(ctx, data)


@app.command("list")
def list_cmd(ctx: typer.Context, tree_id: str) -> None:
    output(ctx, [item for item in list_entities(ctx_project(ctx), "scenarios") if item.get("tree_id") == tree_id])


@app.command("show")
def show(ctx: typer.Context, tree_id: str, scenario_id: str) -> None:
    scenario = read_entity(ctx_project(ctx), "scenarios", scenario_id)
    if scenario.get("tree_id") != tree_id:
        raise UserError("Scenario does not belong to tree.", {"tree_id": tree_id, "scenario_id": scenario_id})
    output(ctx, scenario)


@app.command("set-prob")
def set_prob(ctx: typer.Context, tree_id: str, scenario_id: str, chance_node_id: str, assignments: list[str] = typer.Argument(...)) -> None:
    project = ctx_project(ctx)
    scenario = read_entity(project, "scenarios", scenario_id)
    if scenario.get("tree_id") != tree_id:
        raise UserError("Scenario does not belong to tree.", {"tree_id": tree_id, "scenario_id": scenario_id})
    scenario.setdefault("overrides", {}).setdefault("probabilities", {})[chance_node_id] = parse_assignments(assignments)
    write_json(project.path("scenarios", f"{scenario_id}.json"), scenario)
    output(ctx, scenario)


@app.command("set-utility")
def set_utility(ctx: typer.Context, tree_id: str, scenario_id: str, terminal_node_id: str, utility: float = typer.Option(..., "--utility")) -> None:
    project = ctx_project(ctx)
    scenario = read_entity(project, "scenarios", scenario_id)
    if scenario.get("tree_id") != tree_id:
        raise UserError("Scenario does not belong to tree.", {"tree_id": tree_id, "scenario_id": scenario_id})
    scenario.setdefault("overrides", {}).setdefault("utilities", {})[terminal_node_id] = utility
    write_json(project.path("scenarios", f"{scenario_id}.json"), scenario)
    output(ctx, scenario)


@app.command("diff")
def diff(ctx: typer.Context, tree_id: str, left_scenario_id: str, right_scenario_id: str) -> None:
    project = ctx_project(ctx)
    left = read_entity(project, "scenarios", left_scenario_id)
    right = read_entity(project, "scenarios", right_scenario_id)
    if left.get("tree_id") != tree_id or right.get("tree_id") != tree_id:
        raise UserError("Both scenarios must belong to tree.", {"tree_id": tree_id})
    output(ctx, {"left": left_scenario_id, "right": right_scenario_id, "left_overrides": left.get("overrides", {}), "right_overrides": right.get("overrides", {})})


@app.command("delete")
def delete(ctx: typer.Context, tree_id: str, scenario_id: str) -> None:
    scenario = read_entity(ctx_project(ctx), "scenarios", scenario_id)
    if scenario.get("tree_id") != tree_id:
        raise UserError("Scenario does not belong to tree.", {"tree_id": tree_id, "scenario_id": scenario_id})
    delete_entity(ctx_project(ctx), "scenarios", scenario_id)
    output(ctx, {"deleted": scenario_id})
