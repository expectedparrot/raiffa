"""Bounded exact enumeration of finite policies, respecting information sets.

This deliberately favors a transparent reference solver over scalability.
No maximization is performed separately on indistinguishable histories.
"""

from __future__ import annotations

import itertools
import math
from collections import defaultdict
from copy import deepcopy

from raiffa.core.errors import AnalysisError, ValidationError
from .model import Model, assignments, digest, require, validate

MAX_POLICIES = 100_000
MAX_WORK = 2_000_000
VALUE_TOL = 1e-7


def info_key(model, decision, world):
    return tuple(world[n] for n in model.information[decision])


def policy_space(model: Model):
    slots, choices = [], []
    count = 1
    for decision in model.raw["decision_order"]:
        for assignment in assignments(model.information[decision], model.domains):
            count *= len(model.domains[decision])
            if count > MAX_POLICIES:
                raise AnalysisError(
                    "Exact policy budget exceeded.",
                    {"limit": MAX_POLICIES, "decision": decision},
                )
            slots.append((decision, info_key(model, decision, assignment)))
            choices.append(model.domains[decision])
    worlds = math.prod(
        len(n["outcomes"]) for n in model.nodes.values() if n["kind"] == "chance"
    )
    if count * worlds * len(model.nodes) > MAX_WORK:
        raise AnalysisError(
            "Exact evaluation budget exceeded.",
            {"policies": count, "worlds": worlds, "limit": MAX_WORK},
        )
    return slots, choices


def policy_rows(model, policy):
    return [
        {"decision": d, "when": dict(zip(model.information[d], key)), "action": action}
        for (d, key), action in policy.items()
    ]


def evaluate_policy(model: Model, policy):
    support, reached = defaultdict(float), defaultdict(float)
    order = [k for k in model.order if model.nodes[k]["kind"] != "value"]

    def walk(index, world, probability):
        if probability == 0:
            return
        if index == len(order):
            payoff = sum(
                model.ref(model.row(model.nodes[k], world, "table")["value"])
                for k in model.raw["objective"]["value_nodes"]
            )
            support[payoff] += probability
            return
        key = order[index]
        node = model.nodes[key]
        if node["kind"] == "decision":
            slot = (key, info_key(model, key, world))
            reached[slot] += probability
            walk(index + 1, {**world, key: policy[slot]}, probability)
        else:
            probs = model.row(node, world, "cpt")["probabilities"]
            for state in node["outcomes"]:
                walk(
                    index + 1,
                    {**world, key: state},
                    probability * model.ref(probs[state]),
                )

    walk(0, {}, 1.0)
    cdf, risk = 0.0, []
    for value, probability in sorted(support.items()):
        cdf += probability
        risk.append({"payoff": value, "probability": probability, "cdf": cdf})
    value = math.fsum(v * p for v, p in support.items())
    if not math.isfinite(value):
        raise AnalysisError("Nonfinite expected value.")
    rows = policy_rows(model, policy)
    for row, slot in zip(rows, policy):
        row["reach_probability"] = reached[slot]
    return {
        "expected_value": value,
        "policy": rows,
        "risk_profile": risk,
        "probability_of_loss": sum(p for v, p in support.items() if v < 0),
    }


def candidates(model):
    slots, choices = policy_space(model)
    for actions in itertools.product(*choices):
        policy = dict(zip(slots, actions))
        yield policy, evaluate_policy(model, policy)


def solve(model: Model):
    best, tie_count, total = None, 0, 0
    first = model.raw["decision_order"][0]
    groups = {}
    for policy, result in candidates(model):
        total += 1
        if (
            best is None
            or result["expected_value"] > best["expected_value"] + VALUE_TOL
        ):
            best, tie_count = result, 1
        elif abs(result["expected_value"] - best["expected_value"]) <= VALUE_TOL:
            tie_count += 1
        # Compare all initial actions when they precede observations. Continuations
        # are optimized separately within each group, never fixed implicitly.
        if not model.information[first]:
            action = policy[(first, ())]
            old = groups.get(action)
            if (
                old is None
                or result["expected_value"] > old["expected_value"] + VALUE_TOL
            ):
                groups[action] = {"initial_action": action, **result}
    assert best is not None
    tied_actions = [
        a
        for a, r in groups.items()
        if abs(r["expected_value"] - best["expected_value"]) <= VALUE_TOL
    ]
    blockers = any(
        w["code"] in ("missing_provenance", "unaccepted_provenance")
        for w in model.warnings
    )
    return {
        "model_id": model.raw["id"],
        "model_hash": digest(model.raw),
        "criterion": "risk_neutral_expected_value",
        "unit": model.raw["valuation_context"]["unit"],
        "method": "exact_finite_policy_enumeration",
        "policies_evaluated": total,
        "optimal_policy_count_including_unreachable_rows": tie_count,
        "recommendation_status": "exploratory"
        if blockers
        else "conditional_on_recorded_inputs",
        "recommended_action": tied_actions[0] if len(tied_actions) == 1 else None,
        "tied_initial_actions": tied_actions,
        "alternatives": list(groups.values()),
        "warnings": model.warnings,
        **best,
    }


def compile_tree(model: Model, budget=10_000):
    order = [k for k in model.order if model.nodes[k]["kind"] != "value"]
    compiled = []

    def walk(index, world):
        if len(compiled) >= budget:
            raise AnalysisError(
                "Compiled tree size budget exceeded.", {"limit": budget}
            )
        tree_id = len(compiled)
        item = {"id": tree_id}
        compiled.append(item)
        if index == len(order):
            item.update(
                kind="terminal",
                payoff=sum(
                    model.ref(model.row(model.nodes[k], world, "table")["value"])
                    for k in model.raw["objective"]["value_nodes"]
                ),
            )
        else:
            node_id = order[index]
            node = model.nodes[node_id]
            item.update(kind=node["kind"], source_node=node_id, branches=[])
            if node["kind"] == "decision":
                item["information_set"] = {
                    "decision": node_id,
                    "observed": {n: world[n] for n in model.information[node_id]},
                }
            for state in model.domains[node_id]:
                branch = {
                    "state": state,
                    "child": walk(index + 1, {**world, node_id: state}),
                }
                if node["kind"] == "chance":
                    branch["probability"] = model.ref(
                        model.row(node, world, "cpt")["probabilities"][state]
                    )
                item["branches"].append(branch)
        return tree_id

    walk(0, {})
    return {
        "model_hash": digest(model.raw),
        "root": 0,
        "nodes": compiled,
        "semantics": "Decisions sharing an information_set must choose the same action; ordinary unconstrained tree rollback is invalid.",
    }


def dominance(result):
    alternatives = result["alternatives"]
    relations = []
    for a, b in itertools.permutations(alternatives, 2):
        points = sorted({row["payoff"] for r in (a, b) for row in r["risk_profile"]})

        def cdf(r, x):
            return sum(
                row["probability"] for row in r["risk_profile"] if row["payoff"] <= x
            )

        diffs = [cdf(a, x) - cdf(b, x) for x in points]
        if all(d <= 1e-12 for d in diffs) and any(d < -1e-12 for d in diffs):
            relations.append(
                {"dominates": a["initial_action"], "dominated": b["initial_action"]}
            )
    return {
        "kind": "first_order",
        "method": "exact_finite_cdf",
        "relations": relations,
        "scope": "Initial actions with their EV-optimal continuation policies",
        "alternatives_compared": len(alternatives),
    }


def perfect_information(model, targets=None, before=None):
    targets = targets or [k for k, n in model.nodes.items() if n["kind"] == "chance"]
    require(
        targets and len(targets) == len(set(targets)),
        "Specify distinct chance targets.",
    )
    require(
        all(k in model.nodes and model.nodes[k]["kind"] == "chance" for k in targets),
        "Perfect information targets must be chance nodes.",
    )
    before = before or model.raw["decision_order"][0]
    require(before in model.information, "Unknown observation decision.")
    raw = deepcopy(model.raw)
    node = next(n for n in raw["nodes"] if n["id"] == before)
    for target in targets:
        if target not in node["observes"]:
            node["observes"].append(target)
            raw["arcs"].append({"from": target, "to": before, "kind": "information"})
    try:
        informed = validate(raw)
    except ValidationError as exc:
        raise AnalysisError(
            "Requested perfect information cannot precede this decision in the declared dependency model.",
            {"reason": exc.message},
        ) from exc
    baseline, learned = solve(model), solve(informed)
    return {
        "kind": "perfect_information",
        "targets": targets,
        "before": before,
        "baseline_value": baseline["expected_value"],
        "value_with_information": learned["expected_value"],
        "gross_value": learned["expected_value"] - baseline["expected_value"],
        "unit": baseline["unit"],
        "policy_with_information": learned["policy"],
        "interpretation": "Ideal information intervention, not a feasible study promise.",
    }


def sample_information(model, study_id):
    study = next((s for s in model.raw["studies"] if s["id"] == study_id), None)
    require(study is not None, "Unknown study.", study=study_id)
    raw = deepcopy(model.raw)
    signal = "study_signal"
    while any(n["id"] == signal for n in raw["nodes"]):
        signal += "_"
    raw["nodes"].append(
        {
            "id": signal,
            "kind": "chance",
            "outcomes": study["outcomes"],
            "parents": study["targets"],
            "cpt": study["likelihood"],
        }
    )
    for target in study["targets"]:
        raw["arcs"].append({"from": target, "to": signal, "kind": "dependency"})
    decision = next(n for n in raw["nodes"] if n["id"] == study["before"])
    decision["observes"].append(signal)
    raw["arcs"].append({"from": signal, "to": study["before"], "kind": "information"})
    try:
        informed = validate(raw)
    except ValidationError as exc:
        raise AnalysisError(
            "Study timing conflicts with its target dependencies.",
            {"reason": exc.message},
        ) from exc
    baseline, learned = solve(model), solve(informed)
    cost = model.ref(study["cost"])
    gross = learned["expected_value"] - baseline["expected_value"]
    return {
        "kind": "sample_information",
        "study_id": study_id,
        "before": study["before"],
        "baseline_value": baseline["expected_value"],
        "value_with_information": learned["expected_value"],
        "gross_value": gross,
        "cost": cost,
        "net_value": gross - cost,
        "unit": baseline["unit"],
        "policy_with_information": learned["policy"],
        "design": study["design"],
    }


def research_agenda(model):
    studies = []
    for study in model.raw["studies"]:
        try:
            studies.append(
                {"status": "evaluated", **sample_information(model, study["id"])}
            )
        except AnalysisError as exc:
            studies.append(
                {
                    "study_id": study["id"],
                    "status": "not_evaluable",
                    "reason": exc.message,
                }
            )
    studies.sort(
        key=lambda s: (
            s["status"] != "evaluated",
            -s.get("net_value", 0),
            s["study_id"],
        )
    )
    positive = [s for s in studies if s.get("net_value", 0) > VALUE_TOL]
    return {
        "studies": studies,
        "recommended_study": positive[0]["study_id"] if positive else None,
        "interpretation": "Independent study comparisons against acting now; not a joint portfolio optimum.",
    }


def parameter_degree(model, target):
    """A conservative symbolic degree bound; division by the swept input is unsupported."""
    cache = {}

    def expr(x):
        if isinstance(x, (int, float)):
            return 0
        if "ref" in x:
            return degree(x["ref"])
        ds = [expr(a) for a in x["args"]]
        if x["op"] == "multiply":
            return sum(ds)
        if x["op"] == "divide":
            return ds[0] if ds[1] == 0 else math.inf
        return max(ds)

    def degree(key):
        if key not in cache:
            p = model.parameters[key]
            cache[key] = (
                1
                if key == target
                else (expr(p["expression"]) if "expression" in p else 0)
            )
        return cache[key]

    chance = sum(
        max(
            degree(ref["ref"])
            for row in n["cpt"]
            for ref in row["probabilities"].values()
        )
        for n in model.nodes.values()
        if n["kind"] == "chance"
    )
    payoff = max(
        degree(row["value"]["ref"])
        for n in model.nodes.values()
        if n["kind"] == "value"
        for row in n["table"]
    )
    return chance + payoff


def sensitivity(model, parameter, start, stop):
    require(
        math.isfinite(start) and math.isfinite(stop) and start < stop,
        "Sensitivity domain must be finite and increasing.",
    )
    require(
        parameter in model.parameters and "value" in model.parameters[parameter],
        "Sensitivity requires a literal parameter.",
    )
    if parameter_degree(model, parameter) > 1:
        raise AnalysisError(
            "Certified finite sensitivity currently supports affine policy values only.",
            {"parameter": parameter, "hint": "Nonlinear sweeps are not yet supported."},
        )
    lo = validate(model.raw, overrides={parameter: start})
    hi = validate(model.raw, overrides={parameter: stop})
    # Validate an interior point as well; affine CPTs are bounded by their endpoints.
    validate(model.raw, overrides={parameter: (start + stop) / 2})
    slots, choices = policy_space(model)
    policy_count = math.prod(len(c) for c in choices)
    if policy_count * policy_count > MAX_WORK:
        raise AnalysisError(
            "Threshold policy-pair budget exceeded.", {"policies": policy_count}
        )
    lines = []
    for actions in itertools.product(*choices):
        policy = dict(zip(slots, actions))
        left, right = evaluate_policy(lo, policy), evaluate_policy(hi, policy)
        slope = (right["expected_value"] - left["expected_value"]) / (stop - start)
        lines.append(
            {
                "slope": slope,
                "intercept": left["expected_value"] - slope * start,
                "policy": policy_rows(model, policy),
            }
        )
    points = {start, stop}
    for a, b in itertools.combinations(lines, 2):
        ds = a["slope"] - b["slope"]
        if ds != 0:
            x = (b["intercept"] - a["intercept"]) / ds
            if start < x < stop:
                points.add(x)
    points = sorted(points)

    def winner(x):
        return max(
            range(len(lines)),
            key=lambda i: lines[i]["intercept"] + lines[i]["slope"] * x,
        )

    regions = []
    for left, right in zip(points, points[1:]):
        index = winner((left + right) / 2)
        if regions and regions[-1]["policy_index"] == index:
            regions[-1]["to"] = right
        else:
            regions.append(
                {
                    "from": left,
                    "to": right,
                    "policy_index": index,
                    "policy": lines[index]["policy"],
                }
            )
    switches = []
    for a, b in zip(regions, regions[1:]):
        x = a["to"]
        la, lb = lines[a["policy_index"]], lines[b["policy_index"]]
        switches.append(
            {
                "value": x,
                "from_policy": a["policy"],
                "to_policy": b["policy"],
                "residual": abs(
                    (la["intercept"] - lb["intercept"])
                    + (la["slope"] - lb["slope"]) * x
                ),
                "tie": True,
            }
        )
    return {
        "parameter": parameter,
        "unit": model.parameters[parameter]["unit"],
        "domain": [start, stop],
        "held_fixed": "All other literal parameters; dependent expressions recomputed.",
        "method": "upper_envelope_of_affine_policy_values",
        "coverage": "certified_affine_with_float_arithmetic",
        "regions": regions,
        "thresholds": switches,
        "endpoint_policies": {"from": solve(lo)["policy"], "to": solve(hi)["policy"]},
    }
