from __future__ import annotations

from pathlib import Path

import typer

from raiffa.commands.common import ctx_project, output
from raiffa.core.explorer import build_explorer_html
from raiffa.core.model import load_tree_model, mermaid
from raiffa.core.store import write_json

app = typer.Typer(no_args_is_help=True, add_completion=False)


# Convention for `raiffa export <kind>`:
#   - When `--output <path>` is given, write the rendered artifact to that
#     path and emit a small JSON envelope `{output_path, tree_id}` confirming
#     the write. Errors still go to stderr as JSON.
#   - When `--output` is omitted, write the rendered artifact (raw mermaid,
#     raw HTML, or pretty-printed JSON) to stdout. The caller is expected to
#     redirect (`> path/to/file`) or pipe it. There is no implicit default
#     filesystem location — the caller decides.
#
# `export json` is a special case because it already had a JSON-envelope
# convention; we keep that envelope on stdout so existing scripts that parse
# `{data: {...}}` still work, but `--output` writes the unwrapped tree+nodes
# JSON to the file (same as before).


@app.command("json")
def json_cmd(ctx: typer.Context, tree_id: str, output_path: Path | None = typer.Option(None, "--output")) -> None:
    model = load_tree_model(ctx_project(ctx), tree_id)
    data = {"tree": model.tree, "nodes": list(model.nodes.values())}
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        write_json(output_path, data)
        output(ctx, {"tree_id": tree_id, "output_path": str(output_path)})
        return
    output(ctx, data)


@app.command("mermaid")
def mermaid_cmd(ctx: typer.Context, tree_id: str, output_path: Path | None = typer.Option(None, "--output")) -> None:
    text = mermaid(load_tree_model(ctx_project(ctx), tree_id))
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")
        output(ctx, {"tree_id": tree_id, "output_path": str(output_path)})
        return
    typer.echo(text, nl=False)


@app.command("explorer")
def explorer_cmd(ctx: typer.Context, tree_id: str, output_path: Path | None = typer.Option(None, "--output")) -> None:
    project = ctx_project(ctx)
    model = load_tree_model(project, tree_id)
    html = build_explorer_html(model)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding="utf-8")
        output(ctx, {"tree_id": tree_id, "output_path": str(output_path)})
        return
    typer.echo(html, nl=False)
