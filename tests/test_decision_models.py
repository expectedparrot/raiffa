from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from raiffa.cli import app
from raiffa.core.errors import AnalysisError, ValidationError
from raiffa.decision.engine import (
    compile_tree,
    dominance,
    perfect_information,
    research_agenda,
    sample_information,
    sensitivity,
    solve,
)
from raiffa.decision.model import read_json, validate
from raiffa.decision.schema import SCHEMA
from raiffa.decision.store import Store

FIXTURE = Path(__file__).resolve().parents[1] / "examples/leg01/model.json"


@pytest.fixture
def raw():
    return read_json(FIXTURE)


def parameter(raw, key):
    return next(p for p in raw["parameters"] if p["id"] == key)


def invoke(root, *args, code=0):
    result = CliRunner().invoke(app, ["--project", str(root), *args])
    assert result.exit_code == code, (result.output, result.exception)
    response = json.loads(result.stdout if code == 0 else result.stderr)
    assert response["schema_version"] == "raiffa.cli/1.0"
    assert response["ok"] == (code == 0)
    return response.get("data", response.get("error"))


def test_published_schema_matches_parser():
    Draft202012Validator.check_schema(SCHEMA)
    assert read_json(FIXTURE.parents[2] / "raiffa/schemas/model-2.0.json") == SCHEMA
    assert read_json(FIXTURE.parents[2] / "raiffa/examples/leg01.json") == read_json(
        FIXTURE
    )
    assert read_json(
        FIXTURE.parents[2] / "raiffa/examples/leg01-sequential.json"
    ) == read_json(FIXTURE.with_name("sequential.json"))


def test_exact_lawsuit_and_risk_profiles(raw):
    result = solve(validate(raw, strict=True))
    assert result["recommended_action"] == "settle"
    assert result["expected_value"] == -400_000
    trial = next(a for a in result["alternatives"] if a["initial_action"] == "litigate")
    assert trial["expected_value"] == -630_000
    assert trial["risk_profile"] == [
        {"payoff": -1_350_000, "probability": 0.4, "cdf": 0.4},
        {"payoff": -150_000, "probability": 0.6, "cdf": 1.0},
    ]
    assert dominance(result)["relations"] == []


def test_hidden_state_cannot_leak_into_policy(raw):
    # Force the latent win node to be generated before the decision by naming
    # the decision last in the topological tie-break order. Observation is absent.
    for n in raw["nodes"]:
        if n["id"] == "choice":
            n["id"] = "z_choice"
        n["parents"] = (
            ["z_choice" if p == "choice" else p for p in n.get("parents", [])]
            if "parents" in n
            else n.get("parents")
        )
        if n.get("parents") is None:
            n.pop("parents", None)
        for row in n.get("table", []):
            row["when"]["z_choice"] = row["when"].pop("choice")
    raw["decision_order"] = ["z_choice"]
    raw["arcs"][0]["from"] = "z_choice"
    raw["studies"][0]["before"] = "z_choice"
    model = validate(raw)
    assert model.order.index("win") < model.order.index("z_choice")
    assert solve(model)["expected_value"] == -400_000
    tree = compile_tree(model)
    decisions = [n for n in tree["nodes"] if n["kind"] == "decision"]
    assert len(decisions) == 2
    assert decisions[0]["information_set"] == decisions[1]["information_set"]
    assert perfect_information(model)["value_with_information"] == -250_000


def test_exact_thresholds_and_ties(raw):
    model = validate(raw)
    threshold = sensitivity(model, "p_win", 0, 1)["thresholds"][0]
    assert threshold["value"] == pytest.approx(19 / 24)
    assert threshold["residual"] < 1e-8
    assert sensitivity(model, "damages", 1, 2_000_000)["thresholds"][0][
        "value"
    ] == pytest.approx(625_000)
    assert set(
        solve(validate(raw, overrides={"p_win": 19 / 24}))["tied_initial_actions"]
    ) == {"settle", "litigate"}
    assert sensitivity(model, "p_win", 0.1, 0.2)["thresholds"] == []


def test_information_bounds_and_study_policy(raw):
    model = validate(raw, strict=True)
    perfect = perfect_information(model)
    sample = sample_information(model, "case_review")
    assert perfect["gross_value"] == 150_000
    assert sample["value_with_information"] == -356_000
    assert sample["gross_value"] == 44_000
    assert sample["net_value"] == 34_000
    assert 0 <= sample["gross_value"] <= perfect["gross_value"]
    assert {
        (r["when"]["study_signal"], r["action"])
        for r in sample["policy_with_information"]
    } == {("favorable", "litigate"), ("unfavorable", "settle")}
    assert research_agenda(model)["recommended_study"] == "case_review"


def test_uninformative_or_too_expensive_study(raw):
    parameter(raw, "signal_hit")["value"] = 0.5
    sample = sample_information(validate(raw), "case_review")
    assert sample["gross_value"] == pytest.approx(0)
    assert research_agenda(validate(raw))["recommended_study"] is None


def add_later_decision(raw, observes):
    raw["decision_order"].append("later")
    raw["nodes"].append(
        {
            "id": "later",
            "kind": "decision",
            "stage": 1,
            "actions": ["acknowledge"],
            "observes": observes,
        }
    )
    raw["arcs"].extend(
        {"from": o, "to": "later", "kind": "information"} for o in observes
    )


def test_late_information_cannot_change_earlier_choice(raw):
    add_later_decision(raw, [])
    model = validate(raw)
    assert perfect_information(model, ["win"], "later")["gross_value"] == pytest.approx(
        0
    )
    raw["studies"][0]["before"] = "later"
    assert sample_information(validate(raw), "case_review")[
        "gross_value"
    ] == pytest.approx(0)
    assert validate(raw).information["later"] == ["choice"]


def test_perfect_recall_and_illegal_future_observation(raw):
    raw["nodes"][1]["observes"] = ["win"]
    raw["arcs"].append({"from": "win", "to": "choice", "kind": "information"})
    add_later_decision(raw, [])
    assert validate(raw).information["later"] == ["win", "choice"]
    raw["nodes"][1]["observes"].append("later")
    raw["arcs"].append({"from": "later", "to": "choice", "kind": "information"})
    with pytest.raises(ValidationError, match="timing"):
        validate(raw)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), True, -0.1, 1.1])
def test_invalid_probabilities(raw, value):
    parameter(raw, "p_win")["value"] = value
    with pytest.raises(ValidationError):
        validate(raw)


def test_source_review_and_exploratory_status(raw):
    parameter(raw, "p_win").pop("provenance")
    with pytest.raises(ValidationError, match="Provenance"):
        validate(raw, strict=True)
    assert solve(validate(raw))["recommendation_status"] == "exploratory"
    parameter(raw, "risk_neutral")["provenance"]["source_type"] = "elicited"
    with pytest.raises(ValidationError, match="frozen source"):
        validate(raw)


@pytest.mark.parametrize(
    "mutation", ["table", "arc", "units", "expression", "unknown", "distribution"]
)
def test_semantic_validation(raw, mutation):
    if mutation == "table":
        raw["nodes"][2]["table"].pop()
    elif mutation == "arc":
        raw["arcs"].pop()
    elif mutation == "units":
        parameter(raw, "legal_cost")["unit"] = "EUR"
    elif mutation == "expression":
        parameter(raw, "p_lose")["expression"] = {"ref": "p_lose"}
    elif mutation == "unknown":
        raw["magic"] = "ignored?"
    else:
        parameter(raw, "p_win")["distribution"] = {"normal": [0, 1]}
    with pytest.raises(ValidationError):
        validate(raw)


def test_duplicate_json_key_is_rejected(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text('{"p": 0.2, "p": 0.8}')
    with pytest.raises(ValidationError, match="Cannot read JSON"):
        read_json(path)


def test_revision_replay_idempotency_and_conflict(tmp_path, raw):
    invoke(tmp_path, "init", str(tmp_path))
    store = Store(tmp_path)
    first = store.commit(raw, "initial", {}, create=True)
    assert store.commit(raw, "initial again", {}, create=True) == first
    result = solve(validate(raw))
    frozen = store.save_analysis(first, "solve", {"exploratory": False}, result)
    new = deepcopy(raw)
    parameter(new, "p_win")["value"] = 0.85
    second = store.commit(
        new, "revised assessment", {}, expected_revision=first["revision"]
    )
    assert second["model_parent"] == first["revision"]
    assert (
        store.analysis(frozen["analysis_id"])["result"]["recommended_action"]
        == "settle"
    )
    assert solve(store.load("leg01")[1])["recommended_action"] == "litigate"
    with pytest.raises(ValidationError, match="conflict"):
        store.commit(raw, "stale writer", {}, expected_revision=first["revision"])
    assert len(store.history()) == 2
    assert invoke(tmp_path, "analysis", "replay", frozen["analysis_id"])["identical"]


def test_frozen_source_survives_original_deletion(tmp_path, raw):
    invoke(tmp_path, "init", str(tmp_path))
    source = tmp_path / "source.txt"
    content = b"Synthetic source artifact for integrity test."
    source.write_bytes(content)
    sha = hashlib.sha256(content).hexdigest()
    raw["sources"] = [
        dict(
            id="evidence",
            package="test",
            object_type="record",
            object_id="one",
            revision="v1",
            artifact_sha256=sha,
            path="source.txt",
            locator="whole artifact",
            captured_at="2026-09-19",
        )
    ]
    parameter(raw, "p_win")["provenance"]["source_refs"] = ["evidence"]
    model_path = tmp_path / "model.json"
    model_path.write_text(json.dumps(raw))
    invoke(tmp_path, "model", "import", "--file", str(model_path))
    source.unlink()
    assert invoke(tmp_path, "solve", "leg01")["expected_value"] == -400_000
    frozen = tmp_path / ".raiffa/sources" / sha
    frozen.write_text("tampered")
    assert invoke(tmp_path, "doctor", code=3)["code"] == "validation_error"


def test_full_agent_workflow_and_deterministic_reports(tmp_path):
    assert invoke(tmp_path, "next")["phase"] == "uninitialized"
    invoke(tmp_path, "init", str(tmp_path))
    assert invoke(tmp_path, "next")["phase"] == "frame"
    invoke(tmp_path, "model", "import", "--file", str(FIXTURE))
    assert invoke(tmp_path, "next")["phase"] == "evaluate"
    solved = invoke(tmp_path, "solve", "leg01")
    assert invoke(tmp_path, "next")["phase"] == "challenge"
    invoke(
        tmp_path,
        "sensitivity",
        "one-way",
        "leg01",
        "--param",
        "p_win",
        "--from",
        "0",
        "--to",
        "1",
    )
    invoke(tmp_path, "research", "agenda", "leg01")
    assert invoke(tmp_path, "next")["phase"] == "deliver"
    out = tmp_path / "memo.html"
    invoke(tmp_path, "report", solved["analysis_id"], "--output", str(out))
    first = out.read_bytes()
    invoke(tmp_path, "report", solved["analysis_id"], "--output", str(out))
    assert first == out.read_bytes()
    assert "0.791667" in out.read_text()
    assert invoke(tmp_path, "next")["phase"] == "complete"
    for format in ("svg", "json"):
        invoke(
            tmp_path,
            "report",
            solved["analysis_id"],
            "--format",
            format,
            "--output",
            str(tmp_path / f"memo.{format}"),
        )
    assert invoke(tmp_path, "doctor")["valid"]
    assert invoke(tmp_path, "analysis", "replay", solved["analysis_id"])["identical"]


@pytest.mark.parametrize(
    "args",
    [
        ("--unknown",),
        ("solve",),
        ("model", "missing"),
        ("sensitivity", "one-way", "x", "--from", "oops"),
    ],
)
def test_parser_errors_have_versioned_json(tmp_path, args):
    assert invoke(tmp_path, *args, code=2)["code"] == "usage_error"


def test_compiler_budget(raw):
    with pytest.raises(AnalysisError, match="budget"):
        compile_tree(validate(raw), budget=2)


def test_sequential_study_option_and_cost():
    raw = read_json(FIXTURE.with_name("sequential.json"))
    result = solve(validate(raw, strict=True))
    assert result["recommended_action"] == "study"
    assert result["expected_value"] == -366_000
    reachable = [
        r
        for r in result["policy"]
        if r["decision"] == "choice" and r["reach_probability"] > 0
    ]
    assert {(r["when"]["signal"], r["action"]) for r in reachable} == {
        ("favorable", "litigate"),
        ("unfavorable", "settle"),
    }
    parameter(raw, "study_cost")["value"] = 50_000
    assert solve(validate(raw))["recommended_action"] == "act_now"


def test_joint_information_is_not_sum_of_components(raw):
    # Guess the parity of two independent fair bits. Each bit alone is useless;
    # both together allow a certain correct choice.
    provenance = deepcopy(raw["parameters"][0]["provenance"])
    raw["parameters"] = [
        dict(
            id="risk_neutral", kind="constant", unit="1", value=1, provenance=provenance
        ),
        dict(id="half", kind="probability", unit="1", value=0.5, provenance=provenance),
        dict(id="reward", kind="payoff", unit="USD", value=1, provenance=provenance),
        dict(id="zero", kind="payoff", unit="USD", value=0, provenance=provenance),
    ]
    raw["nodes"] = [
        dict(
            id=k,
            kind="chance",
            outcomes=["zero", "one"],
            parents=[],
            cpt=[
                dict(
                    when={},
                    probabilities={"zero": {"ref": "half"}, "one": {"ref": "half"}},
                )
            ],
        )
        for k in ("x", "y")
    ]
    raw["nodes"].append(
        dict(
            id="choice",
            kind="decision",
            actions=["equal", "different"],
            stage=0,
            observes=[],
        )
    )
    raw["nodes"].append(
        dict(
            id="payoff",
            kind="value",
            unit="USD",
            parents=["choice", "x", "y"],
            table=[
                dict(
                    when=dict(choice=a, x=x, y=y),
                    value={"ref": "reward" if (a == "equal") == (x == y) else "zero"},
                )
                for a in ("equal", "different")
                for x in ("zero", "one")
                for y in ("zero", "one")
            ],
        )
    )
    raw["arcs"] = [
        {"from": p, "to": "payoff", "kind": "value"} for p in ("choice", "x", "y")
    ]
    raw["studies"] = []
    model = validate(raw)
    assert solve(model)["expected_value"] == 0.5
    assert perfect_information(model, ["x"])["gross_value"] == 0
    assert perfect_information(model, ["y"])["gross_value"] == 0
    assert perfect_information(model, ["x", "y"])["gross_value"] == 0.5


def test_report_escapes_model_text(tmp_path, raw):
    raw["title"] = '<script>alert("unsafe")</script>'
    invoke(tmp_path, "init", str(tmp_path))
    file = tmp_path / "model.json"
    file.write_text(json.dumps(raw))
    invoke(tmp_path, "model", "import", "--file", str(file))
    result = invoke(tmp_path, "solve", "leg01")
    out = tmp_path / "report.html"
    invoke(tmp_path, "report", result["analysis_id"], "--output", str(out))
    assert "<script>" not in out.read_text()
    assert "&lt;script&gt;" in out.read_text()


def test_revision_changes_invalidate_completion_and_attribute_flip(tmp_path, raw):
    invoke(tmp_path, "init", str(tmp_path))
    invoke(tmp_path, "model", "import", "--file", str(FIXTURE))
    first = invoke(tmp_path, "solve", "leg01")
    parameter(raw, "p_win")["value"] = 0.85
    path = tmp_path / "revision.json"
    path.write_text(json.dumps(raw))
    invoke(
        tmp_path,
        "model",
        "revise",
        "leg01",
        "--file",
        str(path),
        "--reason",
        "Updated assessment",
    )
    assert invoke(tmp_path, "next")["phase"] == "evaluate"
    second = invoke(tmp_path, "solve", "leg01")
    compared = invoke(
        tmp_path, "analysis", "compare", first["analysis_id"], second["analysis_id"]
    )
    assert compared["parameter_changes"][0]["parameter"] == "p_win"
    assert compared["parameter_changes"][0]["changes_initial_action"]
    assert compared["after_value"] == pytest.approx(-330_000)


def test_outputs_cannot_overwrite_immutable_state(tmp_path):
    invoke(tmp_path, "init", str(tmp_path))
    entry = invoke(tmp_path, "model", "import", "--file", str(FIXTURE))
    result = invoke(tmp_path, "solve", "leg01")
    target = tmp_path / ".raiffa/revisions" / (entry["model_revision"] + ".json")
    original = target.read_bytes()
    for args in [
        ("report", result["analysis_id"]),
        ("model", "compile", "leg01"),
        ("handoff", result["analysis_id"], "--target", "treffen"),
    ]:
        assert (
            invoke(tmp_path, *args, "--output", str(target), code=3)["code"]
            == "validation_error"
        )
    assert target.read_bytes() == original


def test_installed_example_and_local_handoff(tmp_path):
    path = tmp_path / "example.json"
    invoke(tmp_path, "model", "example", "--output", str(path))
    assert read_json(path) == read_json(FIXTURE)
    invoke(tmp_path, "init", str(tmp_path))
    invoke(tmp_path, "model", "import", "--file", str(path))
    result = invoke(tmp_path, "solve", "leg01")
    invoke(
        tmp_path,
        "sensitivity",
        "one-way",
        "leg01",
        "--param",
        "p_win",
        "--from",
        "0",
        "--to",
        "1",
    )
    handoff = tmp_path / "handoff.json"
    invoke(
        tmp_path,
        "handoff",
        result["analysis_id"],
        "--target",
        "vorhersage",
        "--output",
        str(handoff),
    )
    payload = read_json(handoff)
    assert payload["owner_approved"] is False
    assert payload["monitored_conditions"][0]["thresholds"][0][
        "value"
    ] == pytest.approx(19 / 24)


def test_agent_blocks_unsupported_declared_sensitivity(tmp_path, raw):
    # The probability enters twice: through the chance model and a payoff.
    parameter(raw, "win_payoff")["expression"] = {
        "op": "multiply",
        "args": [{"ref": "p_win"}, {"ref": "legal_cost"}],
    }
    invoke(tmp_path, "init", str(tmp_path))
    path = tmp_path / "model.json"
    path.write_text(json.dumps(raw))
    invoke(tmp_path, "model", "import", "--file", str(path))
    invoke(tmp_path, "solve", "leg01")
    assert invoke(tmp_path, "next")["phase"] == "blocked"


def test_attribution_detects_changed_continuation_with_same_initial_action(tmp_path):
    raw = read_json(FIXTURE.with_name("sequential.json"))
    invoke(tmp_path, "init", str(tmp_path))
    invoke(
        tmp_path, "model", "import", "--file", str(FIXTURE.with_name("sequential.json"))
    )
    before = invoke(tmp_path, "solve", "leg01_sequential")
    parameter(raw, "signal_hit")["value"] = 0.2
    path = tmp_path / "reversed-signal.json"
    path.write_text(json.dumps(raw))
    invoke(
        tmp_path,
        "model",
        "revise",
        "leg01_sequential",
        "--file",
        str(path),
        "--reason",
        "Signal coding reversed",
    )
    after = invoke(tmp_path, "solve", "leg01_sequential")
    assert before["recommended_action"] == after["recommended_action"] == "study"
    result = invoke(
        tmp_path, "analysis", "compare", before["analysis_id"], after["analysis_id"]
    )
    change = result["parameter_changes"][0]
    assert change["changes_reachable_policy"]
    assert not change["changes_initial_action"]
