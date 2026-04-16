from __future__ import annotations

from pathlib import Path

import typer

from raiffa.commands.common import ctx_project, output
from raiffa.core.model import load_tree_model, mermaid
from raiffa.core.store import write_json

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command("json")
def json_cmd(ctx: typer.Context, tree_id: str, output_path: Path | None = typer.Option(None, "--output")) -> None:
    model = load_tree_model(ctx_project(ctx), tree_id)
    data = {"tree": model.tree, "nodes": list(model.nodes.values())}
    if output_path:
        write_json(output_path, data)
    output(ctx, data)


@app.command("mermaid")
def mermaid_cmd(ctx: typer.Context, tree_id: str, output_path: Path | None = typer.Option(None, "--output")) -> None:
    text = mermaid(load_tree_model(ctx_project(ctx), tree_id))
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")
    if ctx.obj and ctx.obj.human:
        typer.echo(text)
    else:
        output(ctx, {"tree_id": tree_id, "mermaid": text})
