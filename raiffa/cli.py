from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import typer
from typer.core import TyperGroup

try:  # Typer >=0.26 vendors Click; use the exceptions its parser actually raises.
    from typer._click.exceptions import Exit as ClickExit, UsageError
except ImportError:
    from click.exceptions import Exit as ClickExit, UsageError
from rich.console import Console

from raiffa.commands import (
    analysis,
    docs,
    dominance,
    export,
    info,
    init,
    node,
    prob,
    regret,
    scenario,
    sensitivity,
    solve,
    tree,
    utility,
    voi,
)
from raiffa.core.errors import RaiffaError
from raiffa.decision import cli as decision


def emit_error(code, message, details=None, command=None):
    typer.echo(
        json.dumps(
            {
                "schema_version": "raiffa.cli/1.0",
                "ok": False,
                "command": command or [],
                "project_revision": None,
                "error": {
                    "code": code,
                    "message": message,
                    "details": details or {},
                    "recoverable": code != "internal_error",
                },
                "warnings": [],
                "artifacts": [],
                "next_actions": [],
            },
            sort_keys=True,
        ),
        err=True,
    )


class JsonGroup(TyperGroup):
    def parse_args(self, ctx, args):
        try:
            return super().parse_args(ctx, args)
        except UsageError as exc:
            emit_error("usage_error", exc.format_message())
            raise ClickExit(exc.exit_code) from exc

    def invoke(self, ctx):
        try:
            return super().invoke(ctx)
        except RaiffaError as exc:
            emit_error(exc.code, exc.message, exc.details)
            raise ClickExit(exc.exit_code) from exc
        except UsageError as exc:
            emit_error("usage_error", exc.format_message())
            raise ClickExit(exc.exit_code) from exc


app = typer.Typer(no_args_is_help=True, add_completion=False, cls=JsonGroup)
console = Console()


class CliContext:
    def __init__(self, project: Path | None, human: bool, quiet: bool):
        self.project = project
        self.human = human
        self.quiet = quiet


def emit(data: Any = None, warnings: list[dict] | None = None) -> None:
    typer.echo(
        json.dumps({"data": data, "warnings": warnings or []}, indent=2, sort_keys=True)
    )


@app.callback()
def callback(
    ctx: typer.Context,
    project: Path | None = typer.Option(
        None, "--project", help="Override project root."
    ),
    human: bool = typer.Option(False, "--human", help="Use human-readable output."),
    quiet: bool = typer.Option(
        False, "--quiet", help="Suppress non-data human output."
    ),
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
app.add_typer(decision.model_app, name="model")
app.add_typer(decision.research_app, name="research")
app.add_typer(decision.provenance_app, name="provenance")
app.command("version")(decision.version)
app.command("guide")(decision.guide)
app.command("next")(decision.next_command)
app.command("status")(decision.next_command)
app.command("doctor")(decision.doctor)
app.command("history")(decision.history)
app.command("report")(decision.report_command)
app.command("risk")(decision.risk_command)
app.command("handoff")(decision.handoff)
voi.app.command("perfect")(decision.perfect_command)
voi.app.command("sample")(decision.sample_command)
analysis.app.command("replay")(decision.replay)
analysis.app.command("compare")(decision.compare)


def main() -> None:
    try:
        app()
    except RaiffaError as exc:
        emit_error(exc.code, exc.message, exc.details)
        sys.exit(exc.exit_code)
    except Exception as exc:
        emit_error("internal_error", str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
