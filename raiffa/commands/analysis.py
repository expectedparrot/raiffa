from __future__ import annotations

import typer

from raiffa.commands.common import ctx_project, output
from raiffa.core.store import delete_entity, list_entities, read_entity

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command("list")
def list_cmd(ctx: typer.Context, tree_id: str | None = typer.Argument(None)) -> None:
    analyses = list_entities(ctx_project(ctx), "analyses")
    if tree_id:
        analyses = [item for item in analyses if item.get("tree_id") == tree_id]
    from raiffa.decision.cli import store_for
    for a in store_for(ctx).analyses():
        if tree_id is None or a["model"]["id"] == tree_id:
            analyses.append({"id": a["analysis_id"], "model_id": a["model"]["id"], "model_revision": a["model_revision"], "type": a["kind"]})
    output(ctx, analyses)


@app.command("show")
def show(ctx: typer.Context, analysis_id: str) -> None:
    if analysis_id.startswith("a_"):
        from raiffa.decision.cli import store_for
        output(ctx, store_for(ctx).analysis(analysis_id))
        return
    output(ctx, read_entity(ctx_project(ctx), "analyses", analysis_id))


@app.command("delete")
def delete(ctx: typer.Context, analysis_id: str) -> None:
    if analysis_id.startswith("a_"):
        from raiffa.core.errors import UserError
        raise UserError("Decision analyses are immutable and cannot be deleted through the CLI.")
    delete_entity(ctx_project(ctx), "analyses", analysis_id)
    output(ctx, {"deleted": analysis_id})
