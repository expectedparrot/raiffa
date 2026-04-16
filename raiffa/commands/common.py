from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer

from raiffa.core.ids import local_iso_now
from raiffa.core.project import Project, find_project
from raiffa.core.store import append_record


def ctx_project(ctx: typer.Context) -> Project:
    override: Path | None = ctx.obj.project if ctx.obj else None
    return find_project(override=override)


def output(ctx: typer.Context, data: Any, warnings: list[dict] | None = None, human_message: str | None = None) -> None:
    if ctx.obj and ctx.obj.human:
        typer.echo(human_message or json.dumps(data, indent=2, sort_keys=True))
        return
    typer.echo(json.dumps({"data": data, "warnings": warnings or []}, indent=2, sort_keys=True))


def write_analysis(project: Project, analysis_type: str, tree_id: str, result: dict, inputs: dict | None = None, warnings: list[dict] | None = None) -> str:
    analysis_id, _ = append_record(
        project,
        "analyses",
        [analysis_type, tree_id],
        {
            "type": analysis_type,
            "tree_id": tree_id,
            "scenario_id": result.get("scenario_id", "base"),
            "created_at": local_iso_now(),
            "inputs": inputs or {},
            "result": result,
            "warnings": warnings or [],
        },
    )
    return analysis_id
