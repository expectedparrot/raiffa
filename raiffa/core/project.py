from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .errors import InvalidProject, ProjectNotFound, UserError

DATA_DIR = ".raiffa"

SUBDIRS = [
    "trees",
    "nodes",
    "probabilities",
    "utilities",
    "scenarios",
    "analyses",
    "reports",
    "imports",
    "exports",
]


@dataclass(frozen=True)
class Project:
    root: Path

    @property
    def data_dir(self) -> Path:
        return self.root / DATA_DIR

    def path(self, *parts: str) -> Path:
        return self.data_dir.joinpath(*parts)


def default_project_override() -> Path | None:
    from os import getenv

    explicit = getenv("RAIFFA_PROJECT_DIR")
    if explicit:
        return Path(explicit)
    return None


def find_project(start: Path | None = None, override: Path | None = None) -> Project:
    if override is None:
        override = default_project_override()
    if override is not None:
        root = override.resolve()
        data_dir = root / DATA_DIR
        if not data_dir.exists():
            raise ProjectNotFound(f"No .raiffa directory found at {root}.", {"path": str(root)})
        if not (data_dir / "meta.json").exists():
            raise InvalidProject(f"Missing .raiffa/meta.json under {root}.", {"path": str(root)})
        return Project(root)

    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / DATA_DIR / "meta.json").exists():
            return Project(candidate)
    raise ProjectNotFound(
        "No Raiffa project found. Run `raiffa init <name>` to create one, or cd into an existing project directory."
    )


def create_project(path: Path) -> Project:
    root = path.resolve()
    data_dir = root / DATA_DIR
    if data_dir.exists():
        raise UserError(f"Raiffa project already exists at {data_dir}.", {"path": str(data_dir)})
    root.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir()
    for subdir in SUBDIRS:
        (data_dir / subdir).mkdir(parents=True, exist_ok=True)
    return Project(root)
