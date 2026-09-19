from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer

from raiffa.core.ids import local_iso_now
from raiffa.core.project import Project, default_project_override, find_project
from raiffa.core.store import append_record


def ctx_project(ctx: typer.Context) -> Project:
    override: Path | None = ctx.obj.project if ctx.obj else None
    return find_project(override=override)


def resolve_project_root(ctx: typer.Context) -> Path:
    override: Path | None = ctx.obj.project if ctx.obj else None
    if override is not None:
        return override.resolve()
    default = default_project_override()
    if default is not None:
        return default.resolve()
    return Path.cwd().resolve()


def output(ctx: typer.Context, data: Any, warnings: list[dict] | None = None, human_message: str | None = None) -> None:
    if ctx.obj and ctx.obj.human:
        typer.echo(human_message or json.dumps(data, indent=2, sort_keys=True))
        return
    command = ctx.command_path.split()[1:]
    action = data.get("action") if isinstance(data, dict) else None
    revision = data.get("model_revision") if isinstance(data, dict) else None
    artifacts = []
    if isinstance(data, dict) and data.get("output_path"):
        artifacts = [{"path": data["output_path"], **({"sha256": data["sha256"]} if "sha256" in data else {})}]
    if warnings is None and isinstance(data, dict):
        warnings = data.get("warnings", [])
    typer.echo(json.dumps({"schema_version": "raiffa.cli/1.0", "ok": True, "command": command,
                          "project_revision": revision, "data": data, "warnings": warnings or [],
                          "artifacts": artifacts, "next_actions": [action] if action else []}, indent=2, sort_keys=True, allow_nan=False))


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
