from __future__ import annotations

import typer

from raiffa.commands.common import ctx_project, output, write_analysis
from raiffa.core.model import evppi, load_tree_model

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command("evppi")
def evppi_cmd(ctx: typer.Context, tree_id: str, chance: str = typer.Option(..., "--chance"), no_write: bool = typer.Option(False, "--no-write")) -> None:
    project = ctx_project(ctx)
    result = evppi(load_tree_model(project, tree_id), chance)
    if not no_write:
        result["analysis_id"] = write_analysis(project, "evppi", tree_id, result, {"chance": chance})
    output(ctx, result)


@app.command("evpi")
def evpi_cmd(ctx: typer.Context, tree_id: str, chance: str | None = typer.Option(None, "--chance"), no_write: bool = typer.Option(False, "--no-write")) -> None:
    project = ctx_project(ctx)
    model = load_tree_model(project, tree_id)
    chance_nodes = [chance] if chance else [node_id for node_id, node in model.nodes.items() if node.get("type") == "chance"]
    if len(chance_nodes) != 1:
        from raiffa.core.errors import AnalysisError
        raise AnalysisError("Legacy EVPI cannot sum individual information values. Import a finite decision model and use voi perfect for joint information.")
    results = [evppi(model, node_id) for node_id in chance_nodes]
    result = {"tree_id": tree_id, "chance_nodes": chance_nodes, "components": results, "expected_value_of_information": sum(item["expected_value_of_information"] for item in results)}
    if not no_write:
        result["analysis_id"] = write_analysis(project, "evpi", tree_id, result, {"chance": chance})
    output(ctx, result)
