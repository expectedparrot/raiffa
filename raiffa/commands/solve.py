from __future__ import annotations

import typer

from raiffa.commands.common import ctx_project, output, write_analysis
from raiffa.core.model import load_tree_model, solve_model


def command(
    ctx: typer.Context,
    tree_id: str,
    scenario: str | None = typer.Option(None, "--scenario"),
    no_write: bool = typer.Option(False, "--no-write"),
    show_policy: bool = typer.Option(False, "--show-policy"),
    explain: bool = typer.Option(False, "--explain"),
) -> None:
    project = ctx_project(ctx)
    result = solve_model(load_tree_model(project, tree_id, scenario))
    if scenario:
        result["scenario_id"] = scenario
    if not show_policy:
        result.pop("policy", None)
    if explain:
        result["explanation"] = "Terminal utilities are rolled back through chance nodes by expectation and decision nodes by maximum value."
    if not no_write:
        result["analysis_id"] = write_analysis(project, "solve", tree_id, result, {"scenario": scenario})
    output(ctx, result, human_message=f"{result['recommended_branch_label']} with expected utility {result['root_value']}")
