from __future__ import annotations

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from raiffa.core.errors import UserError
from raiffa.docs import DOCS, load_doc, search_docs

from .common import output

app = typer.Typer(help="Read built-in documentation.")
console = Console()


@app.command("list")
def docs_list(ctx: typer.Context) -> None:
    topics = [{"topic": k, "title": v["title"], "summary": v["summary"]} for k, v in DOCS.items()]
    if ctx.obj and ctx.obj.human:
        tbl = Table(show_header=True, header_style="bold cyan")
        for col in ("Topic", "Title", "Summary"):
            tbl.add_column(col)
        for row in topics:
            tbl.add_row(row["topic"], row["title"], row["summary"])
        console.print(tbl)
        return
    output(ctx, {"topics": topics})


@app.command("show")
def docs_show(ctx: typer.Context, topic: str) -> None:
    if topic not in DOCS:
        raise UserError(
            f"No doc '{topic}'.",
            {"available": list(DOCS.keys()), "hint": "Run `raiffa docs list` to see available topics."},
        )
    text = load_doc(topic)
    if ctx.obj and ctx.obj.human:
        console.print(Markdown(text))
        return
    output(ctx, {"topic": topic, "title": DOCS[topic]["title"], "markdown": text})


@app.command("search")
def docs_search(ctx: typer.Context, query: str) -> None:
    matches = search_docs(query)
    if ctx.obj and ctx.obj.human:
        if not matches:
            console.print(f"[yellow]No results for '{query}'[/yellow]")
            return
        tbl = Table(show_header=True, header_style="bold cyan")
        for col in ("Topic", "Score", "Snippet"):
            tbl.add_column(col)
        for m in matches:
            tbl.add_row(m["topic"], str(m["score"]), (m.get("snippet") or "")[:80])
        console.print(tbl)
        return
    output(ctx, {"query": query, "matches": matches})
