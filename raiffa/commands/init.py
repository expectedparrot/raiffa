from __future__ import annotations

from pathlib import Path

import typer

from raiffa.commands.common import output
from raiffa.core.ids import local_iso_now, validate_id
from raiffa.core.project import create_project
from raiffa.core.store import write_json


def command(
    ctx: typer.Context,
    name: str = typer.Argument(...),
    title: str | None = typer.Option(None, "--title"),
    description: str = typer.Option("", "--description"),
) -> None:
    project_id = validate_id(Path(name).name, "project id")
    project = create_project(Path(name))
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
