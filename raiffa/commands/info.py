from __future__ import annotations

import typer

from raiffa.commands.common import ctx_project, output
from raiffa.core.store import list_entities, read_json


def command(ctx: typer.Context) -> None:
    project = ctx_project(ctx)
    data = {
        "project": str(project.root),
        "data_dir": str(project.data_dir),
        "meta": read_json(project.path("meta.json")),
        "counts": {
            "trees": len(list_entities(project, "trees")),
            "nodes": len(list_entities(project, "nodes")),
            "scenarios": len(list_entities(project, "scenarios")),
            "analyses": len(list_entities(project, "analyses")),
        },
    }
    output(ctx, data)
