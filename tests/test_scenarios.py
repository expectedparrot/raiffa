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


def run_raw(args: list[str], cwd: Path, exit_code: int = 0) -> str:
    """Invoke the CLI and return raw stdout (for `export` commands that
    write the rendered artifact directly to stdout when --output is omitted)."""
    previous = os.getcwd()
    os.chdir(cwd)
    try:
        result = runner.invoke(app, args)
    finally:
        os.chdir(previous)
    assert result.exit_code == exit_code, result.output
    return result.stdout


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


def test_init_here_creates_project_in_current_directory(tmp_path: Path) -> None:
    project = tmp_path / "task_workspace"
    project.mkdir()
    created = data(["init", "boat_decision", "--here", "--description", "Should I buy the boat?"], project)
    assert created["project"] == str(project.resolve())
    assert (project / ".raiffa" / "meta.json").exists()
    assert created["meta"]["id"] == "boat_decision"


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
    # `export mermaid` with no --output writes raw Mermaid to stdout (not a
    # JSON envelope) — caller is expected to redirect.
    exported = run_raw(["export", "mermaid", "lawsuit"], project)
    assert exported.lstrip().startswith("flowchart TD")
    assert "root -->|litigate| trial_result" in exported


def test_export_mermaid_with_output_writes_file_and_envelope(tmp_path: Path) -> None:
    project = build_lawsuit(tmp_path)
    out = tmp_path / "scratch" / "lawsuit.mmd"
    envelope = data(["export", "mermaid", "lawsuit", "--output", str(out)], project)
    assert envelope["output_path"] == str(out)
    assert envelope["tree_id"] == "lawsuit"
    text = out.read_text(encoding="utf-8")
    assert text.lstrip().startswith("flowchart TD")
    assert "root -->|litigate| trial_result" in text


def test_export_explorer_writes_html_to_stdout(tmp_path: Path) -> None:
    project = build_lawsuit(tmp_path)
    html = run_raw(["export", "explorer", "lawsuit"], project)
    assert html.lstrip().startswith("<!DOCTYPE html>")
    # No implicit file is written into `.raiffa/exports/` when --output is
    # omitted. (The directory itself exists from `init`, but should be empty.)
    exports_dir = project / ".raiffa" / "exports"
    assert list(exports_dir.iterdir()) == []
    # Contrast pass: light color-scheme declared so OS dark-mode forced
    # inversion can't strand white text on grey backgrounds.
    assert 'name="color-scheme" content="light"' in html
    assert "color-scheme:light" in html


def test_export_explorer_with_output_writes_file_and_envelope(tmp_path: Path) -> None:
    project = build_lawsuit(tmp_path)
    out = tmp_path / "scratch" / "lawsuit_explorer.html"
    envelope = data(["export", "explorer", "lawsuit", "--output", str(out)], project)
    assert envelope["output_path"] == str(out)
    assert out.read_text(encoding="utf-8").lstrip().startswith("<!DOCTYPE html>")


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


def test_sensitivity_legacy_param_and_threshold_labels(tmp_path: Path) -> None:
    project = build_lawsuit(tmp_path)
    sens = data(["sensitivity", "one-way", "lawsuit", "--param", "trial_result/win_big", "--from", "0.1", "--to", "0.6", "--steps", "6", "--no-write"], project)
    assert len(sens["thresholds"]) == 1
    assert sens["thresholds"][0]["from_branch_label"] == "settle"
    assert sens["thresholds"][0]["to_branch_label"] == "litigate"

    threshold = data(
        ["sensitivity", "threshold", "lawsuit", "--param", "probability:trial_result.win_big", "--between", "settle", "litigate", "--from", "0.1", "--to", "0.6", "--steps", "6"],
        project,
    )
    assert threshold["between"] == ["settle", "litigate"]
    assert len(threshold["thresholds"]) == 1
    assert threshold["thresholds"][0]["between"] == [0.4, 0.5]


def test_add_terminal_without_utility_then_set(tmp_path: Path) -> None:
    """Two-phase build: skeleton first (no utilities), parameterize second.
    `tree validate` must complain about the missing utility until we set it."""
    data(["init", "delayed", "--title", "Delayed Utility"], tmp_path)
    project = tmp_path / "delayed"
    data(["tree", "add", "coin", "Flip"], project)
    data(["node", "add-decision", "coin", "root", "Flip or skip?"], project)
    # Terminal added with no --utility — should succeed.
    created = data(["node", "add-terminal", "coin", "skip", "Skip", "--parent", "root", "--branch-label", "skip"], project)
    assert created["utility"] is None
    data(["node", "add-chance", "coin", "outcome", "Outcome", "--parent", "root", "--branch-label", "flip"], project)
    data(["node", "add-terminal", "coin", "heads", "Heads", "--parent", "outcome", "--branch-label", "heads", "--utility", "1.0"], project)
    data(["node", "add-terminal", "coin", "tails", "Tails", "--parent", "outcome", "--branch-label", "tails"], project)
    data(["prob", "set", "coin", "outcome", "heads=0.5", "tails=0.5"], project)
    # Validate complains about the two terminals still missing utilities.
    err = invoke(["tree", "validate", "coin"], project, exit_code=3)["error"]
    missing = {e["node_id"] for e in err["details"]["errors"] if e["code"] == "missing_utility"}
    assert missing == {"skip", "tails"}
    # Set them via `utility set` and validation passes.
    data(["utility", "set", "coin", "skip", "--utility", "0.5"], project)
    data(["utility", "set", "coin", "tails", "--utility", "0.0"], project)
    assert data(["tree", "validate", "coin"], project)["valid"] is True


def test_threshold_between_is_order_insensitive(tmp_path: Path) -> None:
    """`--between A B` and `--between B A` must return the same threshold."""
    project = build_lawsuit(tmp_path)
    forward = data(
        ["sensitivity", "threshold", "lawsuit", "--param", "probability:trial_result.win_big",
         "--between", "settle", "litigate", "--from", "0.1", "--to", "0.6", "--steps", "6"],
        project,
    )
    reverse = data(
        ["sensitivity", "threshold", "lawsuit", "--param", "probability:trial_result.win_big",
         "--between", "litigate", "settle", "--from", "0.1", "--to", "0.6", "--steps", "6"],
        project,
    )
    assert forward["thresholds"] == reverse["thresholds"]
    assert len(forward["thresholds"]) == 1


def test_analysis_snapshot_written(tmp_path: Path) -> None:
    project = build_lawsuit(tmp_path)
    solved = data(["solve", "lawsuit"], project)
    assert "analysis_id" in solved
    analyses = data(["analysis", "list", "lawsuit"], project)
    assert len(analyses) == 1
    assert analyses[0]["id"] == solved["analysis_id"]
