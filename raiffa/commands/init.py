from __future__ import annotations

from pathlib import Path

import typer

from raiffa.commands.common import output
from raiffa.core.ids import local_iso_now, validate_id
from raiffa.core.project import create_project
from raiffa.core.store import write_json


def command(
    ctx: typer.Context,
    name: str = typer.Argument("."),
    here: bool = typer.Option(False, "--here", help="Initialize .raiffa in the current directory."),
    title: str | None = typer.Option(None, "--title"),
    description: str = typer.Option("", "--description"),
) -> None:
    override = ctx.obj.project if ctx.obj else None
    target = (override or Path.cwd()) if here else Path(name)
    project_id_source = name if here else Path(name).name
    if project_id_source in ("", "."):
        project_id_source = target.resolve().name
    project_id = validate_id(project_id_source, "project id")
    project = create_project(target)
    meta = {
        "id": project_id,
        "title": title or project_id.replace("_", " ").title(),
        "description": description,
        "created_at": local_iso_now(),
        "settings": {
            "default_probability_tolerance": 1e-9,
            "default_criterion": "expected_utility",
            "default_utility_scale": "vnm",
            "analysis_snapshots": True,
        },
    }
    write_json(project.path("meta.json"), meta)
    output(ctx, {"project": str(project.root), "data_dir": str(project.data_dir), "meta": meta}, human_message=f"Created {project.data_dir}")
