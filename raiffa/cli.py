from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import typer
from rich.console import Console

from raiffa.commands import analysis, docs, dominance, export, info, init, node, prob, regret, scenario, sensitivity, solve, tree, utility, voi
from raiffa.core.errors import RaiffaError

app = typer.Typer(no_args_is_help=True, add_completion=False)
console = Console()


class CliContext:
    def __init__(self, project: Path | None, human: bool, quiet: bool):
        self.project = project
        self.human = human
        self.quiet = quiet


def emit(data: Any = None, warnings: list[dict] | None = None) -> None:
    typer.echo(json.dumps({"data": data, "warnings": warnings or []}, indent=2, sort_keys=True))


@app.callback()
def callback(
    ctx: typer.Context,
    project: Path | None = typer.Option(None, "--project", help="Override project root."),
    human: bool = typer.Option(False, "--human", help="Use human-readable output."),
    quiet: bool = typer.Option(False, "--quiet", help="Suppress non-data human output."),
) -> None:
    ctx.obj = CliContext(project=project, human=human, quiet=quiet)


app.command("init")(init.command)
app.command("info")(info.command)
app.add_typer(tree.app, name="tree")
app.add_typer(node.app, name="node")
app.add_typer(prob.app, name="prob")
app.add_typer(utility.app, name="utility")
app.command("solve")(solve.command)
app.add_typer(scenario.app, name="scenario")
app.add_typer(sensitivity.app, name="sensitivity")
app.add_typer(voi.app, name="voi")
app.command("regret")(regret.command)
app.command("dominance")(dominance.command)
app.add_typer(export.app, name="export")
app.add_typer(analysis.app, name="analysis")
app.add_typer(docs.app, name="docs")


def main() -> None:
    try:
        app()
    except RaiffaError as exc:
        typer.echo(
            json.dumps({"error": {"code": exc.code, "message": exc.message, "details": exc.details}}, indent=2, sort_keys=True),
            err=True,
        )
        sys.exit(exc.exit_code)
    except Exception as exc:
        typer.echo(
            json.dumps({"error": {"code": "internal_error", "message": str(exc), "details": {}}}, indent=2, sort_keys=True),
            err=True,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
