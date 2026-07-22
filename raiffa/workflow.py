from __future__ import annotations

from pathlib import Path

CHECKLISTS: dict[str, list[str]] = {
    "init": [
        "Initialize a project: `raiffa init <project_id> --here --description '<decision question>'` when working in an existing task directory, or `raiffa init <project_id>` for a new subdirectory project.",
        "Then create a tree: `raiffa --project <dir> tree add <tree_id> '<Decision Title>'`.",
    ],
    "build": [
        "Add a root decision node: `raiffa --project <dir> node add-decision <tree_id> root_node '<What should we do?>'`.",
        "Add chance nodes per action: `raiffa --project <dir> node add-chance <tree_id> <id> '<Uncertainty>' --parent root_node --branch-label '<action>'`.",
        "Add terminal leaves: `raiffa --project <dir> node add-terminal <tree_id> <id> '<outcome>' --parent <chance_id> --branch-label '<label>' --utility <value>`.",
        "Validate: `raiffa --project <dir> tree validate <tree_id>`.",
    ],
    "parameterize": [
        "Set probabilities on each chance node: `raiffa --project <dir> prob set <tree_id> <chance_id> <child1>=<p1> <child2>=<p2>`.",
        "Verify utilities on terminal nodes: `raiffa --project <dir> utility list <tree_id>`.",
        "Validate: `raiffa --project <dir> tree validate <tree_id>`.",
    ],
    "solve": [
        "Solve for the optimal action: `raiffa --project <dir> solve <tree_id> --show-policy`.",
        "Check for dominated actions: `raiffa --project <dir> dominance <tree_id>`.",
        "Run one-way sensitivity on uncertain probabilities: `raiffa --project <dir> sensitivity one-way <tree_id> --param probability:<chance_id>.<child_id> --from 0.0 --to 1.0`.",
        "Create scenarios for what-if analysis: `raiffa --project <dir> scenario add <tree_id> <scenario_id> '<name>'`.",
    ],
    "complete": [
        "Run EVPPI to quantify the value of information: `raiffa --project <dir> voi evppi <tree_id> --chance <chance_id>`.",
        "Export a Mermaid diagram: `raiffa --project <dir> export mermaid <tree_id> --output tree.mmd`.",
        "Review analysis history: `raiffa --project <dir> analysis list <tree_id>`.",
    ],
}

_NEXT_STEPS: dict[str, list[dict]] = {
    "init": [
        {"label": "Initialize project", "command": "raiffa init <project_id> --here --description '<decision question>'"},
    ],
    "build": [
        {"label": "Add decision root", "command": "raiffa --project <dir> node add-decision <tree_id> root_node '<What should we do?>'"},
        {"label": "Add chance node", "command": "raiffa --project <dir> node add-chance <tree_id> <id> '<Uncertainty>' --parent root_node --branch-label '<action>'"},
        {"label": "Add terminal node", "command": "raiffa --project <dir> node add-terminal <tree_id> <id> '<outcome>' --parent <chance_id> --branch-label '<label>' --utility <value>"},
        {"label": "Validate tree", "command": "raiffa --project <dir> tree validate <tree_id>"},
    ],
    "parameterize": [
        {"label": "Set probabilities", "command": "raiffa --project <dir> prob set <tree_id> <chance_id> <child1>=0.6 <child2>=0.4"},
        {"label": "List terminal utilities", "command": "raiffa --project <dir> utility list <tree_id>"},
        {"label": "Validate tree", "command": "raiffa --project <dir> tree validate <tree_id>"},
    ],
    "solve": [
        {"label": "Solve the tree", "command": "raiffa --project <dir> solve <tree_id> --show-policy"},
        {"label": "One-way sensitivity", "command": "raiffa --project <dir> sensitivity one-way <tree_id> --param probability:<chance_id>.<child_id> --from 0.0 --to 1.0"},
        {"label": "Create a scenario", "command": "raiffa --project <dir> scenario add <tree_id> <scenario_id> '<scenario name>'"},
    ],
    "complete": [
        {"label": "EVPPI analysis", "command": "raiffa --project <dir> voi evppi <tree_id> --chance <chance_id>"},
        {"label": "Export Mermaid diagram", "command": "raiffa --project <dir> export mermaid <tree_id> --output tree.mmd"},
        {"label": "List analyses", "command": "raiffa --project <dir> analysis list <tree_id>"},
    ],
}


def infer_phase(project_root: Path) -> str:
    data_dir = project_root / ".raiffa"
    if not (data_dir / "meta.json").exists():
        return "init"
    trees = list((data_dir / "trees").glob("*.json"))
    if not trees:
        return "build"
    nodes = list((data_dir / "nodes").glob("*.json"))
    if not nodes:
        return "parameterize"
    analyses = list((data_dir / "analyses").glob("*.json"))
    if not analyses:
        return "solve"
    return "complete"


def next_steps(phase: str) -> list[dict]:
    return _NEXT_STEPS.get(phase, [])


def phase_state(project_root: Path) -> dict:
    data_dir = project_root / ".raiffa"
    if not (data_dir / "meta.json").exists():
        return {
            "phase": "init",
            "project_exists": False,
            "counts": {},
            "checklist": CHECKLISTS["init"],
            "recommended_next_steps": next_steps("init"),
        }
    trees = list((data_dir / "trees").glob("*.json"))
    nodes = list((data_dir / "nodes").glob("*.json"))
    scenarios = list((data_dir / "scenarios").glob("*.json"))
    analyses = list((data_dir / "analyses").glob("*.json"))
    phase = infer_phase(project_root)
    return {
        "phase": phase,
        "project_exists": True,
        "counts": {
            "trees": len(trees),
            "nodes": len(nodes),
            "scenarios": len(scenarios),
            "analyses": len(analyses),
        },
        "checklist": CHECKLISTS.get(phase, []),
        "recommended_next_steps": next_steps(phase),
    }
