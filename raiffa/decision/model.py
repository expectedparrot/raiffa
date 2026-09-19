from __future__ import annotations

import hashlib
import itertools
import json
import math
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

from jsonschema import Draft202012Validator

from raiffa.core.errors import ValidationError
from .schema import SCHEMA

TOL = 1e-9


def canonical(value) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def digest(value) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def read_json(path: Path):
    try:

        def pairs(items):
            result = {}
            for key, value in items:
                if key in result:
                    raise ValueError(f"Duplicate JSON key: {key}")
                result[key] = value
            return result

        return json.loads(
            path.read_text(),
            object_pairs_hook=pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"Invalid number {value}")
            ),
        )
    except (OSError, ValueError) as exc:
        raise ValidationError(
            f"Cannot read JSON: {path}", {"reason": str(exc)}
        ) from exc


def require(condition, message, **details):
    if not condition:
        raise ValidationError(message, details)


def unique(items, name):
    require(len(items) == len(set(items)), f"Duplicate {name}.")


def assignments(names, domains):
    require(
        math.prod(len(domains[n]) for n in names) <= 10_000,
        "Conditional table/information set budget exceeded.",
        limit=10_000,
    )
    return [
        dict(zip(names, values))
        for values in itertools.product(*(domains[n] for n in names))
    ]


@dataclass
class Model:
    raw: dict
    nodes: dict
    parameters: dict
    values: dict
    units: dict
    domains: dict
    order: list
    information: dict
    warnings: list

    def ref(self, ref):
        return self.values[ref["ref"]]

    def row(self, node, world, key):
        return next(
            row
            for row in node[key]
            if all(world[k] == v for k, v in row["when"].items())
        )


def validate(raw: dict, *, strict=False, overrides=None) -> Model:
    errors = sorted(
        Draft202012Validator(SCHEMA).iter_errors(raw), key=lambda e: str(list(e.path))
    )
    if errors:
        raise ValidationError(
            "Model does not match raiffa.model/2.0.",
            {
                "errors": [
                    {"path": list(e.path), "message": e.message} for e in errors[:20]
                ]
            },
        )
    try:
        canonical(raw)
    except ValueError as exc:
        raise ValidationError("Nonfinite numeric input.") from exc
    raw = deepcopy(raw)
    for collection in ("nodes", "parameters", "sources", "studies"):
        unique([x["id"] for x in raw[collection]], collection)
    params = {x["id"]: x for x in raw["parameters"]}
    for key, value in (overrides or {}).items():
        require(
            key in params and "value" in params[key],
            "Only literal parameters can be swept.",
            parameter=key,
        )
        require(
            type(value) in (int, float) and math.isfinite(value), "Invalid override."
        )
        params[key]["value"] = value
    nodes = {x["id"]: x for x in raw["nodes"]}
    sources = {x["id"]: x for x in raw["sources"]}
    values, units, visiting, warnings = {}, {}, set(), []

    def provenance(item):
        source = item.get("provenance")
        if not source:
            warnings.append({"code": "missing_provenance", "id": item["id"]})
            return
        require(
            all(ref in sources for ref in source["source_refs"]),
            "Unknown source reference.",
            id=item["id"],
        )
        require(
            source["source_type"] == "assumption" or source["source_refs"],
            "Non-assumption provenance requires a frozen source.",
            id=item["id"],
        )
        if source["review_status"] != "accepted":
            warnings.append(
                {
                    "code": "unaccepted_provenance",
                    "id": item["id"],
                    "status": source["review_status"],
                }
            )
        if source["source_type"] == "assumption":
            warnings.append(
                {
                    "code": "named_assumption",
                    "id": item["id"],
                    "owner": source["owner"],
                    "rationale": source["rationale"],
                }
            )
        if source["evidence_population"] == "simulated":
            warnings.append({"code": "simulated_evidence", "id": item["id"]})

    def expression(expr):
        if isinstance(expr, (int, float)):
            return float(expr), "1"
        if "ref" in expr:
            return parameter(expr["ref"])
        op, args = expr["op"], [expression(a) for a in expr["args"]]
        require(len(args) == (1 if op == "negate" else 2), "Wrong expression arity.")
        a, au = args[0]
        if op == "negate":
            return -a, au
        b, bu = args[1]
        if op in ("add", "subtract"):
            require(
                au == bu, "Cannot add/subtract incompatible units.", left=au, right=bu
            )
            return (a + b if op == "add" else a - b), au
        if op == "multiply":
            require(
                "1" in (au, bu),
                "Only multiplication by a dimensionless scalar is supported.",
            )
            return a * b, bu if au == "1" else au
        require(b != 0, "Division by zero.")
        require(bu == "1" or au == bu, "Unsupported division units.")
        return a / b, au if bu == "1" else "1"

    def parameter(key):
        require(key in params, "Unknown parameter.", parameter=key)
        require(key not in visiting, "Cyclic parameter expression.", parameter=key)
        if key in values:
            return values[key], units[key]
        visiting.add(key)
        p = params[key]
        if "value" in p:
            value, unit = float(p["value"]), p["unit"]
        else:
            value, unit = expression(p["expression"])
        require(math.isfinite(value), "Nonfinite parameter value.", parameter=key)
        require(
            unit == p["unit"],
            "Parameter unit differs from expression unit.",
            parameter=key,
        )
        if p["kind"] == "probability":
            require(
                unit == "1" and 0 <= value <= 1,
                "Invalid probability parameter.",
                parameter=key,
            )
        if p["kind"] == "cost":
            require(value >= 0, "Cost must be nonnegative.", parameter=key)
        if "bounds" in p:
            bounds = p["bounds"]
            require(
                len(bounds) == 2 and bounds[0] <= value <= bounds[1],
                "Value outside parameter bounds.",
                parameter=key,
            )
        visiting.remove(key)
        values[key], units[key] = value, unit
        return value, unit

    for p in params.values():
        provenance(p)
        parameter(p["id"])
    pref = raw["objective"]["preference_ref"]
    require(
        pref in params and values[pref] == 1 and units[pref] == "1",
        "Finite release requires an explicitly sourced risk-neutral preference parameter equal to 1.",
    )
    decisions = raw["decision_order"]
    unique(decisions, "decision order entries")
    require(
        set(decisions) == {n for n in nodes if nodes[n]["kind"] == "decision"},
        "Decision order must include every decision exactly once.",
    )
    require(
        [nodes[n]["stage"] for n in decisions]
        == sorted(set(nodes[n]["stage"] for n in decisions)),
        "Decision stages must strictly increase.",
    )
    domains = {}
    for key, n in nodes.items():
        if n["kind"] != "value":
            domain = n.get("actions", n.get("outcomes"))
            unique(domain, f"states of {key}")
            domains[key] = domain
    expected_arcs = set()
    predecessors = {key: set() for key in nodes}
    information, remembered = {}, []
    for key in decisions:
        explicit = nodes[key]["observes"]
        unique(explicit, "observations")
        for observed in explicit:
            require(
                observed in domains and observed != key,
                "Invalid observation.",
                decision=key,
                observed=observed,
            )
            expected_arcs.add((observed, key, "information"))
        information[key] = list(dict.fromkeys(remembered + explicit))
        predecessors[key].update(information[key])
        remembered = information[key] + [key]
    for key, n in nodes.items():
        if n["kind"] == "decision":
            continue
        parents = n["parents"]
        unique(parents, "parents")
        require(
            all(p in domains and p != key for p in parents), "Invalid parent.", node=key
        )
        predecessors[key].update(parents)
        kind = "dependency" if n["kind"] == "chance" else "value"
        expected_arcs.update((p, key, kind) for p in parents)
        rows = n["cpt"] if n["kind"] == "chance" else n["table"]
        required_rows = {
            tuple(sorted(x.items())) for x in assignments(parents, domains)
        }
        actual_rows = [tuple(sorted(x["when"].items())) for x in rows]
        require(
            len(actual_rows) == len(set(actual_rows))
            and set(actual_rows) == required_rows,
            "Conditional table must cover every parent assignment exactly once.",
            node=key,
        )
        for row in rows:
            if n["kind"] == "chance":
                probs = row["probabilities"]
                require(
                    set(probs) == set(n["outcomes"]),
                    "CPT outcomes do not match node domain.",
                    node=key,
                )
                for ref in probs.values():
                    val, unit = parameter(ref["ref"])
                    require(
                        unit == "1" and 0 <= val <= 1,
                        "Invalid CPT probability.",
                        node=key,
                    )
                require(
                    abs(sum(values[r["ref"]] for r in probs.values()) - 1) <= TOL,
                    "CPT row does not sum to one.",
                    node=key,
                )
            else:
                _, unit = parameter(row["value"]["ref"])
                require(
                    unit == n["unit"] == raw["valuation_context"]["unit"],
                    "Payoff units differ from valuation basis.",
                    node=key,
                )
    actual_arcs = [(a["from"], a["to"], a["kind"]) for a in raw["arcs"]]
    require(
        len(actual_arcs) == len(set(actual_arcs)) and set(actual_arcs) == expected_arcs,
        "Arcs must exactly match declared parents and observations.",
    )
    objective_nodes = raw["objective"]["value_nodes"]
    unique(objective_nodes, "objective values")
    require(
        set(objective_nodes) == {k for k, n in nodes.items() if n["kind"] == "value"},
        "Objective must include every value node exactly once.",
    )
    order = []
    while len(order) < len(nodes):
        ready = sorted(
            k for k in nodes if k not in order and predecessors[k] <= set(order)
        )
        require(ready, "Cyclic dependencies or impossible information timing.")
        order.extend(ready)
    for study in raw["studies"]:
        provenance(study)
        require(study["before"] in decisions, "Study refers to unknown decision.")
        require(
            all(t in nodes and nodes[t]["kind"] == "chance" for t in study["targets"]),
            "Study targets must be chance nodes.",
        )
        unique(study["targets"], "study targets")
        unique(study["outcomes"], "study outcomes")
        require(
            len(study["likelihood"]) == len(assignments(study["targets"], domains)),
            "Incomplete study likelihood.",
        )
        seen = set()
        for row in study["likelihood"]:
            key = tuple(sorted(row["when"].items()))
            require(
                key not in seen
                and row["when"] in assignments(study["targets"], domains),
                "Invalid study likelihood assignment.",
            )
            seen.add(key)
            require(
                set(row["probabilities"]) == set(study["outcomes"]),
                "Study observation domain mismatch.",
            )
            probs = [parameter(ref["ref"]) for ref in row["probabilities"].values()]
            require(
                all(u == "1" and 0 <= p <= 1 for p, u in probs)
                and abs(sum(p for p, _ in probs) - 1) <= TOL,
                "Invalid study likelihood probabilities.",
            )
        cost, unit = parameter(study["cost"]["ref"])
        require(
            cost >= 0 and unit == raw["valuation_context"]["unit"],
            "Study cost units/value invalid.",
        )
    blockers = [
        w
        for w in warnings
        if w["code"] in ("missing_provenance", "unaccepted_provenance")
    ]
    if strict and blockers:
        raise ValidationError(
            "Provenance requires review before solving. Use --exploratory for a draft analysis.",
            {"issues": blockers},
        )
    return Model(
        raw, nodes, params, values, units, domains, order, information, warnings
    )


def verify_sources(raw, base: Path):
    artifacts = {}
    for source in raw["sources"]:
        path = (base / source["path"]).resolve()
        try:
            content = path.read_bytes()
        except OSError as exc:
            raise ValidationError(
                "Cannot read frozen source artifact.",
                {"source": source["id"], "path": str(path)},
            ) from exc
        sha = hashlib.sha256(content).hexdigest()
        require(
            sha == source["artifact_sha256"],
            "Source artifact hash mismatch.",
            source=source["id"],
        )
        artifacts[sha] = content
    return artifacts
