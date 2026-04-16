from __future__ import annotations

import json
import os
from pathlib import Path

from typer.testing import CliRunner

from raiffa.cli import app

runner = CliRunner()


def invoke(args: list[str], cwd: Path, exit_code: int = 0) -> dict:
    previous = os.getcwd()
    os.chdir(cwd)
    try:
        result = runner.invoke(app, args)
    finally:
        os.chdir(previous)
    assert result.exit_code == exit_code, result.output
    stream = result.stdout if exit_code == 0 else result.stderr
    return json.loads(stream)


def data(args: list[str], cwd: Path) -> dict:
    return invoke(args, cwd)["data"]


def build_lawsuit(tmp_path: Path) -> Path:
    data(["init", "lawsuit_analysis", "--title", "Lawsuit Analysis"], tmp_path)
    project = tmp_path / "lawsuit_analysis"
    data(["tree", "add", "lawsuit", "Settle or Litigate"], project)
    data(["node", "add-decision", "lawsuit", "root", "Choose action"], project)
    data(["node", "add-terminal", "lawsuit", "settle_outcome", "Accept settlement", "--parent", "root", "--branch-label", "settle", "--utility", "42"], project)
    data(["node", "add-chance", "lawsuit", "trial_result", "Trial result", "--parent", "root", "--branch-label", "litigate"], project)
    data(["node", "add-terminal", "lawsuit", "win_big", "Win big", "--parent", "trial_result", "--branch-label", "major win", "--utility", "90"], project)
    data(["node", "add-terminal", "lawsuit", "partial_win", "Partial win", "--parent", "trial_result", "--branch-label", "partial win", "--utility", "45"], project)
    data(["node", "add-terminal", "lawsuit", "lose", "Lose", "--parent", "trial_result", "--branch-label", "lose", "--utility", "-40"], project)
    data(["prob", "set", "lawsuit", "trial_result", "win_big=0.25", "partial_win=0.35", "lose=0.40"], project)
    return project


def test_lawsuit_solve_validate_export(tmp_path: Path) -> None:
    project = build_lawsuit(tmp_path)
    validated = data(["tree", "validate", "lawsuit"], project)
    assert validated["valid"] is True
    solved = data(["solve", "lawsuit", "--show-policy", "--no-write"], project)
    assert solved["root_value"] == 42.0
    assert solved["recommended_action"] == "settle_outcome"
    assert solved["recommended_branch_label"] == "settle"
    assert solved["policy_branch_labels"] == {"root": ["settle"]}
    assert solved["dominated_branches"][0]["branch_label"] == "litigate"
    assert solved["node_values"]["trial_result"] == 22.25
    exported = data(["export", "mermaid", "lawsuit"], project)
    assert "root -->|litigate| trial_result" in exported["mermaid"]


def test_invalid_probability_sum(tmp_path: Path) -> None:
    project = build_lawsuit(tmp_path)
    data(["prob", "set", "lawsuit", "trial_result", "win_big=0.25", "partial_win=0.35", "lose=0.30"], project)
    error = invoke(["tree", "validate", "lawsuit"], project, exit_code=3)["error"]
    assert error["code"] == "validation_error"
    assert error["details"]["errors"][0]["code"] == "probability_sum"


def test_scenario_override_changes_choice(tmp_path: Path) -> None:
    project = build_lawsuit(tmp_path)
    data(["scenario", "add", "lawsuit", "optimistic", "Optimistic"], project)
    data(["scenario", "set-prob", "lawsuit", "optimistic", "trial_result", "win_big=0.65", "partial_win=0.25", "lose=0.10"], project)
    solved = data(["solve", "lawsuit", "--scenario", "optimistic", "--show-policy", "--no-write"], project)
    assert solved["recommended_action"] == "trial_result"
    assert solved["recommended_branch_label"] == "litigate"
    assert solved["root_value"] == 65.75


def test_sensitivity_and_evppi(tmp_path: Path) -> None:
    project = build_lawsuit(tmp_path)
    sens = data(["sensitivity", "one-way", "lawsuit", "--param", "probability:trial_result.win_big", "--from", "0.1", "--to", "0.6", "--steps", "6", "--no-write"], project)
    assert len(sens["samples"]) == 6
    assert sens["samples"][0]["recommended_action"] == "settle_outcome"
    assert sens["samples"][0]["recommended_branch_label"] == "settle"
    assert sens["samples"][-1]["recommended_action"] == "trial_result"
    assert sens["samples"][-1]["recommended_branch_label"] == "litigate"
    voi = data(["voi", "evppi", "lawsuit", "--chance", "trial_result", "--no-write"], project)
    assert round(voi["expected_value_of_information"], 2) == 13.05
    assert voi["states"][0]["best_action_branch_label"] in {"settle", "litigate"}


def test_analysis_snapshot_written(tmp_path: Path) -> None:
    project = build_lawsuit(tmp_path)
    solved = data(["solve", "lawsuit"], project)
    assert "analysis_id" in solved
    analyses = data(["analysis", "list", "lawsuit"], project)
    assert len(analyses) == 1
    assert analyses[0]["id"] == solved["analysis_id"]
