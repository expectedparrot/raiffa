from __future__ import annotations

import typer

from raiffa.commands.common import ctx_project, output, write_analysis
from raiffa.core.model import load_tree_model, one_way_sensitivity

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command("one-way")
def one_way(
    ctx: typer.Context,
    tree_id: str,
    param: str = typer.Option(..., "--param"),
    start: float = typer.Option(..., "--from"),
    stop: float = typer.Option(..., "--to"),
    steps: int = typer.Option(11, "--steps"),
    no_write: bool = typer.Option(False, "--no-write"),
) -> None:
    from raiffa.decision.cli import is_decision_model, sensitivity_command
    if is_decision_model(ctx, tree_id):
        sensitivity_command(ctx, tree_id, param, start, stop, no_write)
        return
    project = ctx_project(ctx)
    result = one_way_sensitivity(load_tree_model(project, tree_id), param, start, stop, steps)
    if not no_write:
        result["analysis_id"] = write_analysis(project, "sensitivity", tree_id, result, {"param": param, "from": start, "to": stop, "steps": steps})
    output(ctx, result)


@app.command("threshold")
def threshold(
    ctx: typer.Context,
    tree_id: str,
    param: str = typer.Option(..., "--param"),
    between: tuple[str, str] = typer.Option(..., "--between"),
    start: float = typer.Option(0.0, "--from"),
    stop: float = typer.Option(1.0, "--to"),
    steps: int = typer.Option(101, "--steps"),
) -> None:
    project = ctx_project(ctx)
    result = one_way_sensitivity(load_tree_model(project, tree_id), param, start, stop, steps)
    requested = {str(item) for item in between}
    filtered = [
        item
        for item in result["thresholds"]
        if {str(item["from"]), str(item["to"])} == requested
        or {str(item["from_branch_label"]), str(item["to_branch_label"])} == requested
    ]
    output(ctx, {"tree_id": tree_id, "param": param, "between": list(between), "thresholds": filtered})


@app.command("tornado")
def tornado(ctx: typer.Context, tree_id: str) -> None:
    output(ctx, {"tree_id": tree_id, "message": "Tornado analysis is planned after parameter registries are implemented."})
