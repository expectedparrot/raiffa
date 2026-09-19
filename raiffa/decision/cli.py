from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from importlib.resources import files
from pathlib import Path

import typer

from raiffa import __version__
from raiffa.commands.common import ctx_project, output, resolve_project_root
from raiffa.core.errors import AnalysisError, ProjectNotFound, ValidationError
from . import engine, report
from .model import canonical, digest, read_json, require, validate, verify_sources
from .schema import SCHEMA
from .store import Store, atomic_bytes

model_app = typer.Typer(
    help="Import and evaluate provenance-aware finite influence diagrams."
)
research_app = typer.Typer(help="Compare the net value of declared studies.")
provenance_app = typer.Typer(help="Inspect parameter provenance coverage.")


def store_for(ctx):
    return Store(ctx_project(ctx).root)


def is_decision_model(ctx, model_id):
    return store_for(ctx).has_model(model_id)


def external_output(store, path):
    path = path.resolve()
    require(
        not path.is_relative_to(store.data.resolve()),
        "Output cannot overwrite managed .raiffa state; choose a path outside it.",
    )
    return path


@model_app.command("example")
def example(
    ctx: typer.Context,
    output_path: Path = typer.Option(..., "--output"),
    sequential: bool = typer.Option(False, "--sequential"),
):
    name = "leg01-sequential.json" if sequential else "leg01.json"
    raw = json.loads(files("raiffa").joinpath("examples", name).read_text())
    validate(raw)
    require(
        ".raiffa" not in output_path.resolve().parts,
        "Example output cannot overwrite managed state.",
    )
    atomic_bytes(output_path.resolve(), json.dumps(raw, indent=2).encode() + b"\n")
    output(
        ctx,
        {
            "output_path": str(output_path.resolve()),
            "model_id": raw["id"],
            "synthetic": True,
        },
    )


def result_output(ctx, entry, kind, settings, result, no_write=False):
    if not no_write:
        saved = store_for(ctx).save_analysis(entry, kind, settings, result)
        result = {**result, "analysis_id": saved["analysis_id"]}
    output(ctx, {**result, "model_revision": entry["revision"]})


@model_app.command("schema")
def schema(ctx: typer.Context):
    output(ctx, SCHEMA)


@model_app.command("import")
def import_model(ctx: typer.Context, file: Path = typer.Option(..., "--file")):
    raw = read_json(file)
    checked = validate(raw)
    artifacts = verify_sources(raw, file.parent)
    store = store_for(ctx)
    require(
        not (store.data / "trees" / f"{raw['id']}.json").exists(),
        "A legacy tree already uses this ID; choose a new model ID.",
    )
    entry = store.commit(raw, "Initial model import", artifacts, create=True)
    output(
        ctx,
        {
            "model_id": raw["id"],
            "model_revision": entry["revision"],
            "warnings": checked.warnings,
        },
    )


@model_app.command("revise")
def revise_model(
    ctx: typer.Context,
    model_id: str,
    file: Path = typer.Option(..., "--file"),
    reason: str = typer.Option(..., "--reason"),
    expected_revision: str | None = typer.Option(None, "--expected-revision"),
):
    store = store_for(ctx)
    previous = store.current(model_id)
    raw = read_json(file)
    validate(raw)
    require(raw["id"] == model_id, "Revision cannot change model identity.")
    artifacts = verify_sources(raw, file.parent)
    entry = store.commit(
        raw,
        reason,
        artifacts,
        expected_revision=expected_revision or previous["revision"],
    )
    output(ctx, {"model_id": model_id, "model_revision": entry["revision"]})


@model_app.command("show")
def show_model(ctx: typer.Context, model_id: str):
    entry, _ = store_for(ctx).load(model_id)
    output(ctx, entry)


@model_app.command("validate")
def validate_model(
    ctx: typer.Context, model_id: str, strict: bool = typer.Option(False, "--strict")
):
    entry, model = store_for(ctx).load(model_id, strict=strict)
    output(
        ctx,
        {
            "valid": True,
            "model_revision": entry["revision"],
            "warnings": model.warnings,
            "information_sets": model.information,
        },
    )


@model_app.command("compile")
def compile_model(
    ctx: typer.Context,
    model_id: str,
    output_path: Path | None = typer.Option(None, "--output"),
):
    entry, model = store_for(ctx).load(model_id)
    tree = engine.compile_tree(model)
    if output_path:
        output_path = external_output(store_for(ctx), output_path)
        atomic_bytes(output_path, canonical(tree))
        output(
            ctx,
            {
                "output_path": str(output_path.resolve()),
                "model_revision": entry["revision"],
                "node_count": len(tree["nodes"]),
            },
        )
    else:
        output(ctx, tree)


@provenance_app.command("check")
def provenance(ctx: typer.Context, model_id: str):
    entry, model = store_for(ctx).load(model_id)
    output(
        ctx,
        {
            "model_revision": entry["revision"],
            "parameters": len(model.parameters),
            "warnings": model.warnings,
            "sources": model.raw["sources"],
        },
    )


def solve_command(ctx, model_id, exploratory=False, no_write=False):
    entry, model = store_for(ctx).load(model_id, strict=not exploratory)
    result_output(
        ctx, entry, "solve", {"exploratory": exploratory}, engine.solve(model), no_write
    )


def sensitivity_command(ctx, model_id, param, start, stop, no_write=False):
    entry, model = store_for(ctx).load(model_id, strict=True)
    result_output(
        ctx,
        entry,
        "sensitivity",
        {"parameter": param, "start": start, "stop": stop},
        engine.sensitivity(model, param, start, stop),
        no_write,
    )


def perfect_command(
    ctx: typer.Context,
    model_id: str,
    targets: str | None = typer.Option(
        None, "--targets", help="Comma-separated chance node IDs; default all."
    ),
    before: str | None = typer.Option(None, "--before"),
    no_write: bool = typer.Option(False, "--no-write"),
):
    entry, model = store_for(ctx).load(model_id, strict=True)
    target_list = [x.strip() for x in targets.split(",")] if targets else None
    result_output(
        ctx,
        entry,
        "perfect",
        {"targets": target_list, "before": before},
        engine.perfect_information(model, target_list, before),
        no_write,
    )


def sample_command(
    ctx: typer.Context,
    model_id: str,
    study: str = typer.Option(..., "--study"),
    no_write: bool = typer.Option(False, "--no-write"),
):
    entry, model = store_for(ctx).load(model_id, strict=True)
    result_output(
        ctx,
        entry,
        "sample",
        {"study": study},
        engine.sample_information(model, study),
        no_write,
    )


@research_app.command("agenda")
def agenda(
    ctx: typer.Context,
    model_id: str,
    no_write: bool = typer.Option(False, "--no-write"),
):
    entry, model = store_for(ctx).load(model_id, strict=True)
    result_output(ctx, entry, "research", {}, engine.research_agenda(model), no_write)


def version(ctx: typer.Context):
    output(ctx, {"version": __version__, "model_schema": "raiffa.model/2.0"})


def guide(ctx: typer.Context):
    output(
        ctx,
        {
            "purpose": "Turn sourced beliefs into conditional, auditable decision policies.",
            "workflow": [
                "init",
                "model import",
                "model validate --strict",
                "solve",
                "sensitivity one-way",
                "research agenda",
                "report",
            ],
            "control_loop": "Run raiffa next after each material change.",
            "supported": [
                "finite influence diagrams",
                "perfect-recall policies",
                "typed provenance",
                "exact risk-neutral evaluation",
                "affine switching thresholds",
                "joint perfect information",
                "finite likelihood EVSI",
                "immutable local revisions",
                "HTML/SVG reports",
            ],
            "not_supported": [
                "continuous distributions",
                "nonlinear utility",
                "multiattribute preferences",
                "general nonlinear thresholds",
                "native upstream adapters",
                "EDSL instrument generation",
                "automatic external execution",
            ],
            "rules": [
                "Never invent probability sources. Named assumptions require owner and rationale.",
                "A source-complete model is not necessarily empirically supported.",
                "Policies can use only observed information; the solver enforces this.",
                "Import frozen source artifacts; no live remote resolution during solve.",
                "Research ranks are independent comparisons, not a portfolio optimizer.",
                "Legacy tree commands retain the old storage format; use model import for the new workflow.",
            ],
            "example": "raiffa model example --output model.json",
        },
    )


def next_state(ctx, model_id=None):
    try:
        store = store_for(ctx)
    except ProjectNotFound:
        root = resolve_project_root(ctx)
        return {
            "phase": "uninitialized",
            "complete": False,
            "action": action(
                root,
                ["init", "decision", "--here"],
                "Create a local decision workspace.",
            ),
        }
    history = store.history()
    models = sorted({r["model"]["id"] for r in history})
    if not models:
        return {
            "phase": "frame",
            "complete": False,
            "action": action(
                store.root,
                ["model", "import", "--file", "<model.json>"],
                "Provide a finite influence diagram with explicit choices, timing, payoffs, and sourced parameters.",
                {"model.json": {"type": "path", "schema": "raiffa.model/2.0"}},
            ),
        }
    if model_id is None and len(models) > 1:
        return {
            "phase": "select_model",
            "complete": False,
            "models": models,
            "action": action(
                store.root,
                ["next", "<model_id>"],
                "Select the decision to continue.",
                {"model_id": {"enum": models}},
                mutates=False,
            ),
        }
    model_id = model_id or models[0]
    entry, model = store.load(model_id)
    revision = entry["revision"]
    blockers = [
        w
        for w in model.warnings
        if w["code"] in ("missing_provenance", "unaccepted_provenance")
    ]
    if blockers:
        return {
            "phase": "source",
            "complete": False,
            "model_revision": revision,
            "issues": blockers,
            "action": action(
                store.root,
                [
                    "model",
                    "revise",
                    model_id,
                    "--file",
                    "<model.json>",
                    "--reason",
                    "<reason>",
                    "--expected-revision",
                    revision,
                ],
                "Resolve source provenance before normal evaluation.",
                {"model.json": {"type": "path"}, "reason": {"type": "string"}},
            ),
        }
    analyses = store.analyses(revision)

    def blocked(reason):
        return {
            "phase": "blocked",
            "complete": False,
            "model_revision": revision,
            "reason": reason,
            "action": action(
                store.root,
                [
                    "model",
                    "revise",
                    model_id,
                    "--file",
                    "<model.json>",
                    "--reason",
                    "<reason>",
                    "--expected-revision",
                    revision,
                ],
                "Revise the model or its declared analysis scope to resolve this unsupported requirement.",
                {"model.json": {"type": "path"}, "reason": {"type": "string"}},
            ),
        }

    try:
        engine.policy_space(model)
    except (AnalysisError, ValidationError) as exc:
        return blocked(exc.message)
    solved = [
        a for a in analyses if a["kind"] == "solve" and not a["settings"]["exploratory"]
    ]
    if not solved:
        return {
            "phase": "evaluate",
            "complete": False,
            "model_revision": revision,
            "action": action(
                store.root,
                ["solve", model_id],
                "Evaluate admissible policies on the current revision.",
            ),
        }
    for param in model.parameters.values():
        if (
            "bounds" in param
            and "value" in param
            and param["bounds"][0] < param["bounds"][1]
        ):
            matches = [
                a
                for a in analyses
                if a["kind"] == "sensitivity"
                and a["settings"]["parameter"] == param["id"]
                and [a["settings"]["start"], a["settings"]["stop"]] == param["bounds"]
            ]
            if not matches:
                if engine.parameter_degree(model, param["id"]) > 1:
                    return blocked(
                        f"Thresholds for {param['id']} are non-affine and unsupported."
                    )
                try:
                    for endpoint in param["bounds"]:
                        validate(model.raw, overrides={param["id"]: endpoint})
                except ValidationError as exc:
                    return blocked(
                        f"Declared bounds for {param['id']} produce an invalid model: {exc.message}"
                    )
                return {
                    "phase": "challenge",
                    "complete": False,
                    "model_revision": revision,
                    "action": action(
                        store.root,
                        [
                            "sensitivity",
                            "one-way",
                            model_id,
                            "--param",
                            param["id"],
                            "--from",
                            str(param["bounds"][0]),
                            "--to",
                            str(param["bounds"][1]),
                        ],
                        "Check switching conditions across the declared parameter bounds.",
                    ),
                }
    if model.raw["studies"] and not any(a["kind"] == "research" for a in analyses):
        return {
            "phase": "challenge",
            "complete": False,
            "model_revision": revision,
            "action": action(
                store.root,
                ["research", "agenda", model_id],
                "Price each declared study against acting now.",
            ),
        }
    for analysis in analyses:
        if analysis["kind"] == "research":
            unresolved = [
                s for s in analysis["result"]["studies"] if s["status"] != "evaluated"
            ]
            if unresolved:
                return blocked(
                    "Some declared studies are not evaluable: "
                    + "; ".join(s["study_id"] + ": " + s["reason"] for s in unresolved)
                )
    analysis = solved[0]
    manifests = [
        read_json(p) for p in (store.data / "decision_reports").glob("*.manifest.json")
    ]
    challenge_ids = sorted(a["analysis_id"] for a in analyses if a["kind"] != "solve")
    completed = any(
        m["analysis_id"] == analysis["analysis_id"]
        and m["challenge_ids"] == challenge_ids
        and m["format"] == "html"
        for m in manifests
    )
    if completed:
        store.doctor()
        return {
            "phase": "complete",
            "complete": True,
            "model_revision": revision,
            "action": None,
            "scope": "Finite analysis, sensitivity for declared bounds, declared-study agenda, and a current local HTML memo.",
        }
    return {
        "phase": "deliver",
        "complete": False,
        "model_revision": revision,
        "action": action(
            store.root,
            [
                "report",
                analysis["analysis_id"],
                "--output",
                str(store.root / f"{model_id}-decision.html"),
            ],
            "Render a memo from the frozen analysis and current challenge artifacts.",
        ),
    }


def action(root, args, reason, inputs=None, mutates=True):
    return {
        "argv": ["raiffa", "--project", str(root), *args],
        "cwd": str(root),
        "project": str(root),
        "reason": reason,
        "required_inputs": inputs or {},
        "mutates": mutates,
        "external_execution": False,
        "paid_execution": False,
        "expected_transition": "Re-run next to assess the first incomplete gate.",
    }


def next_command(ctx: typer.Context, model_id: str | None = typer.Argument(None)):
    state = next_state(ctx, model_id)
    output(ctx, state)


def doctor(ctx: typer.Context):
    output(ctx, store_for(ctx).doctor())


def risk_command(ctx: typer.Context, model_id: str):
    entry, model = store_for(ctx).load(model_id, strict=True)
    result = engine.solve(model)
    output(
        ctx,
        {
            "model_revision": entry["revision"],
            "unit": result["unit"],
            "policy": result["policy"],
            "risk_profile": result["risk_profile"],
            "alternatives": result["alternatives"],
            "dominance": engine.dominance(result),
        },
    )


def handoff(
    ctx: typer.Context,
    analysis_id: str,
    target: str = typer.Option(..., "--target"),
    output_path: Path = typer.Option(..., "--output"),
):
    require(
        target in ("treffen", "vorhersage"),
        "Handoff target must be treffen or vorhersage.",
    )
    store = store_for(ctx)
    output_path = external_output(store, output_path)
    analysis = store.analysis(analysis_id)
    require(analysis["kind"] == "solve", "Handoff requires a solve analysis.")
    require(
        analysis["result"]["recommendation_status"] != "exploratory",
        "Exploratory analyses cannot be exported as decision handoffs.",
    )
    thresholds = [
        a
        for a in store.analyses(analysis["model_revision"])
        if a["kind"] == "sensitivity"
    ]
    payload = {
        "schema_version": "raiffa.handoff/1.0",
        "recipient": target,
        "model_revision": analysis["model_revision"],
        "analysis_id": analysis_id,
        "recommendation_status": analysis["result"]["recommendation_status"],
        "decision_owner": analysis["model"]["decision_maker"],
        "owner_approved": False,
        "policy": analysis["result"]["policy"],
        "expected_value": analysis["result"]["expected_value"],
        "unit": analysis["result"]["unit"],
        "sources": analysis["model"]["sources"],
        "parameter_provenance": [
            {"id": p["id"], "provenance": p.get("provenance")}
            for p in analysis["model"]["parameters"]
        ],
        "monitored_conditions": [
            {
                "parameter": a["result"]["parameter"],
                "unit": a["result"]["unit"],
                "domain": a["result"]["domain"],
                "held_fixed": a["result"]["held_fixed"],
                "regions": a["result"]["regions"],
                "thresholds": a["result"]["thresholds"],
                "instruction": "Re-evaluate the model when an accepted source revision crosses a boundary.",
            }
            for a in thresholds
        ],
        "limitations": [
            "Proposed local interchange contract; receiver import support is not yet implemented.",
            "Individual one-way conditions are not a joint multi-parameter boundary.",
            "This file does not record a human decision or modify the receiving package.",
        ],
    }
    content = canonical(payload)
    sha = hashlib.sha256(content).hexdigest()
    with store.locked():
        atomic_bytes(store.data / "handoffs" / f"{sha}.json", content)
    atomic_bytes(output_path.resolve(), content)
    output(
        ctx,
        {
            "output_path": str(output_path.resolve()),
            "sha256": sha,
            "recipient": target,
            "model_revision": analysis["model_revision"],
        },
    )


def history(ctx: typer.Context):
    output(
        ctx,
        [
            {k: v for k, v in r.items() if k != "model"}
            | {"model_id": r["model"]["id"]}
            for r in store_for(ctx).history()
        ],
    )


def report_command(
    ctx: typer.Context,
    analysis_id: str,
    output_path: Path = typer.Option(..., "--output"),
    format: str = typer.Option("html", "--format"),
):
    require(
        format in ("html", "svg", "json"), "Report format must be html, svg, or json."
    )
    store = store_for(ctx)
    output_path = external_output(store, output_path)
    analysis = store.analysis(analysis_id)
    require(analysis["kind"] == "solve", "Report requires a solve analysis.")
    challenges = [
        a for a in store.analyses(analysis["model_revision"]) if a["kind"] != "solve"
    ]
    challenges.sort(key=lambda a: a["analysis_id"])
    if format == "html":
        content = report.render(analysis, challenges).encode()
    elif format == "svg":
        content = report.diagram(analysis["model"]).encode()
    else:
        content = canonical({"analysis": analysis, "challenges": challenges})
    sha = hashlib.sha256(content).hexdigest()
    name = f"report_{sha}.{format}"
    manifest = {
        "analysis_id": analysis_id,
        "challenge_ids": [a["analysis_id"] for a in challenges],
        "artifact": name,
        "format": format,
        "sha256": sha,
    }
    with store.locked():
        atomic_bytes(store.data / "decision_reports" / name, content)
        atomic_bytes(
            store.data / "decision_reports" / f"{digest(manifest)}.manifest.json",
            canonical(manifest),
        )
    atomic_bytes(output_path.resolve(), content)
    output(
        ctx,
        {
            "output_path": str(output_path.resolve()),
            "sha256": sha,
            "analysis_id": analysis_id,
            "model_revision": analysis["model_revision"],
        },
    )


def replay(ctx: typer.Context, analysis_id: str):
    store = store_for(ctx)
    analysis = store.analysis(analysis_id)
    require(
        analysis["engine_version"] == __version__,
        "Replay requires the recorded engine version.",
    )
    model = validate(analysis["model"])
    settings = analysis["settings"]
    kind = analysis["kind"]
    if kind == "solve":
        result = engine.solve(model)
    elif kind == "sensitivity":
        result = engine.sensitivity(model, **settings)
    elif kind == "perfect":
        result = engine.perfect_information(model, **settings)
    elif kind == "sample":
        result = engine.sample_information(model, settings["study"])
    elif kind == "research":
        result = engine.research_agenda(model)
    else:
        raise AnalysisError("Unknown replay analysis kind.")
    require(result == analysis["result"], "Replay differs from frozen result.")
    output(ctx, {"analysis_id": analysis_id, "identical": True})


def compare(ctx: typer.Context, before: str, after: str):
    store = store_for(ctx)
    a, b = store.analysis(before), store.analysis(after)
    require(a["kind"] == b["kind"] == "solve", "Compare requires two solve analyses.")
    require(
        a["model"]["id"] == b["model"]["id"],
        "Cannot attribute changes across unrelated models.",
    )
    ap = {p["id"]: p for p in a["model"]["parameters"]}
    bp = {p["id"]: p for p in b["model"]["parameters"]}

    def reachable_policy(result):
        return [
            {k: row[k] for k in ("decision", "when", "action")}
            for row in result["policy"]
            if row["reach_probability"] > 0
        ]

    changes = []
    for key in sorted(set(ap) | set(bp)):
        if ap.get(key) == bp.get(key):
            continue
        change = {"parameter": key, "before": ap.get(key), "after": bp.get(key)}
        if key in ap and key in bp:
            hybrid = deepcopy(a["model"])
            hybrid["parameters"] = [
                bp[key] if p["id"] == key else p for p in hybrid["parameters"]
            ]
            try:
                result = engine.solve(validate(hybrid))
                change.update(
                    counterfactual_value=result["expected_value"],
                    counterfactual_action=result["recommended_action"],
                    counterfactual_policy=result["policy"],
                    changes_reachable_policy=reachable_policy(result)
                    != reachable_policy(a["result"]),
                    changes_initial_action=result["recommended_action"]
                    != a["result"]["recommended_action"],
                )
            except (ValidationError, AnalysisError) as exc:
                change["counterfactual_status"] = "not_evaluable"
                change["reason"] = exc.message
        changes.append(change)
    other_a = {k: v for k, v in a["model"].items() if k != "parameters"}
    other_b = {k: v for k, v in b["model"].items() if k != "parameters"}
    output(
        ctx,
        {
            "before": before,
            "after": after,
            "parameter_changes": changes,
            "structure_or_source_changes": other_a != other_b,
            "before_value": a["result"]["expected_value"],
            "after_value": b["result"]["expected_value"],
            "before_policy": a["result"]["policy"],
            "after_policy": b["result"]["policy"],
            "interpretation": "One-at-a-time substitutions into the old model; interactions and structural changes are not uniquely attributed.",
        },
    )
