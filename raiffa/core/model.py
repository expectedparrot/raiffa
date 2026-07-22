from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from .errors import AnalysisError, UserError, ValidationError
from .project import Project
from .store import list_entities, read_entity


@dataclass
class TreeModel:
    tree: dict
    nodes: dict[str, dict]
    children: dict[str, list[str]]

    @property
    def tree_id(self) -> str:
        return self.tree["id"]

    @property
    def root_id(self) -> str | None:
        return self.tree.get("root_node")


def load_tree_model(project: Project, tree_id: str, scenario_id: str | None = None) -> TreeModel:
    tree = read_entity(project, "trees", tree_id)
    nodes = {node["id"]: deepcopy(node) for node in list_entities(project, "nodes") if node.get("tree_id") == tree_id}
    if scenario_id and scenario_id != "base":
        scenario = read_entity(project, "scenarios", scenario_id)
        if scenario.get("tree_id") != tree_id:
            raise UserError("Scenario does not belong to tree.", {"tree_id": tree_id, "scenario_id": scenario_id})
        apply_scenario(nodes, scenario)
    children = index_children(nodes)
    return TreeModel(tree=tree, nodes=nodes, children=children)


def index_children(nodes: dict[str, dict]) -> dict[str, list[str]]:
    children: dict[str, list[str]] = defaultdict(list)
    for node in nodes.values():
        parent = node.get("parent")
        if parent is not None:
            children[parent].append(node["id"])
    return {parent: sorted(ids, key=lambda node_id: nodes[node_id].get("created_at", node_id)) for parent, ids in children.items()}


def apply_scenario(nodes: dict[str, dict], scenario: dict) -> None:
    overrides = scenario.get("overrides", {})
    for node_id, probabilities in overrides.get("probabilities", {}).items():
        if node_id not in nodes:
            raise UserError("Scenario references missing chance node.", {"node_id": node_id})
        nodes[node_id]["probabilities"] = probabilities
    for node_id, utility in overrides.get("utilities", {}).items():
        if node_id not in nodes:
            raise UserError("Scenario references missing terminal node.", {"node_id": node_id})
        nodes[node_id]["utility"] = utility


def validate_model(model: TreeModel, warnings_as_errors: bool = False) -> dict:
    errors: list[dict] = []
    warnings: list[dict] = []
    tree_id = model.tree_id
    nodes = model.nodes
    children = model.children
    root_id = model.root_id

    if not root_id:
        errors.append({"code": "missing_root", "message": "Tree has no root node.", "tree_id": tree_id})
    elif root_id not in nodes:
        errors.append({"code": "missing_root", "message": "Root node does not exist.", "tree_id": tree_id, "root_node": root_id})
    elif nodes[root_id].get("parent") is not None:
        errors.append({"code": "root_has_parent", "message": "Root node must not have a parent.", "node_id": root_id})

    for node_id, node in nodes.items():
        node_type = node.get("type")
        parent = node.get("parent")
        if node_type not in {"decision", "chance", "terminal"}:
            errors.append({"code": "invalid_node_type", "message": "Invalid node type.", "node_id": node_id, "type": node_type})
        if parent is not None and parent not in nodes:
            errors.append({"code": "missing_parent", "message": "Parent node does not exist.", "node_id": node_id, "parent": parent})
        if parent is not None and not node.get("branch_label"):
            errors.append({"code": "missing_branch_label", "message": "Non-root node needs a branch label.", "node_id": node_id})
        if node_type in {"decision", "chance"} and not children.get(node_id):
            errors.append({"code": "missing_children", "message": "Decision and chance nodes need children.", "node_id": node_id})
        if node_type == "terminal" and children.get(node_id):
            errors.append({"code": "terminal_has_children", "message": "Terminal node cannot have children.", "node_id": node_id})
        if node_type == "terminal":
            utility = node.get("utility")
            if not isinstance(utility, int | float):
                errors.append({"code": "missing_utility", "message": "Terminal node needs a numeric utility.", "node_id": node_id})

    for parent, child_ids in children.items():
        seen: dict[str, str] = {}
        for child_id in child_ids:
            label = nodes[child_id].get("branch_label")
            if label in seen:
                errors.append(
                    {
                        "code": "duplicate_branch_label",
                        "message": "Sibling branch labels must be unique.",
                        "parent": parent,
                        "branch_label": label,
                        "nodes": [seen[label], child_id],
                    }
                )
            seen[label] = child_id

    for node_id, node in nodes.items():
        if node.get("type") == "chance":
            probs = node.get("probabilities", {})
            if not isinstance(probs, dict):
                errors.append({"code": "invalid_probabilities", "message": "Probabilities must be an object.", "node_id": node_id})
                continue
            child_ids = set(children.get(node_id, []))
            prob_ids = set(probs)
            for extra in sorted(prob_ids - child_ids):
                errors.append({"code": "extra_probability", "message": "Probability references a non-child.", "node_id": node_id, "child_id": extra})
            for missing in sorted(child_ids - prob_ids):
                errors.append({"code": "missing_probability", "message": "Chance child is missing a probability.", "node_id": node_id, "child_id": missing})
            total = 0.0
            for child_id, probability in probs.items():
                if not isinstance(probability, int | float):
                    errors.append({"code": "invalid_probability", "message": "Probability must be numeric.", "node_id": node_id, "child_id": child_id})
                    continue
                if probability < 0:
                    errors.append({"code": "negative_probability", "message": "Probability must be nonnegative.", "node_id": node_id, "child_id": child_id})
                total += float(probability)
            tolerance = float(model.tree.get("settings", {}).get("probability_tolerance", 1e-9))
            if child_ids and abs(total - 1.0) > tolerance:
                errors.append({"code": "probability_sum", "message": "Chance node probabilities must sum to 1.0.", "node_id": node_id, "sum": total})

    if root_id in nodes:
        reachable = reachable_nodes(model)
        for node_id in sorted(set(nodes) - reachable):
            errors.append({"code": "unreachable_node", "message": "Node is not reachable from root.", "node_id": node_id})
        if has_cycle(model):
            errors.append({"code": "cycle", "message": "Tree contains a cycle.", "tree_id": tree_id})

    if warnings_as_errors and warnings:
        errors.extend(warnings)
        warnings = []
    if errors:
        raise ValidationError("Tree validation failed.", {"tree_id": tree_id, "errors": errors})
    return {"valid": True, "tree_id": tree_id, "node_count": len(nodes), "warnings": warnings}


def reachable_nodes(model: TreeModel) -> set[str]:
    if not model.root_id:
        return set()
    seen: set[str] = set()
    stack = [model.root_id]
    while stack:
        node_id = stack.pop()
        if node_id in seen:
            continue
        seen.add(node_id)
        stack.extend(model.children.get(node_id, []))
    return seen


def has_cycle(model: TreeModel) -> bool:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node_id: str) -> bool:
        if node_id in visiting:
            return True
        if node_id in visited:
            return False
        visiting.add(node_id)
        for child_id in model.children.get(node_id, []):
            if visit(child_id):
                return True
        visiting.remove(node_id)
        visited.add(node_id)
        return False

    return bool(model.root_id and visit(model.root_id))


def solve_model(model: TreeModel) -> dict:
    validate_model(model)
    values: dict[str, float] = {}
    policy: dict[str, list[str]] = {}
    policy_branch_labels: dict[str, list[str]] = {}
    dominated: list[dict] = []

    def value(node_id: str) -> float:
        if node_id in values:
            return values[node_id]
        node = model.nodes[node_id]
        node_type = node["type"]
        if node_type == "terminal":
            result = float(node["utility"])
        elif node_type == "chance":
            result = sum(float(node["probabilities"][child_id]) * value(child_id) for child_id in model.children[node_id])
        elif node_type == "decision":
            child_values = {child_id: value(child_id) for child_id in model.children[node_id]}
            best = max(child_values.values())
            tolerance = float(model.tree.get("settings", {}).get("tie_tolerance", 1e-9))
            best_children = [child_id for child_id, child_value in child_values.items() if abs(child_value - best) <= tolerance]
            policy[node_id] = best_children
            policy_branch_labels[node_id] = [branch_label(model, child_id) for child_id in best_children]
            for child_id, child_value in child_values.items():
                if child_id not in best_children:
                    dominated.append(
                        {
                            "decision_node": node_id,
                            "branch": child_id,
                            "branch_label": branch_label(model, child_id),
                            "value": child_value,
                            "best_value": best,
                        }
                    )
            result = best
        else:
            raise AnalysisError("Unknown node type during solve.", {"node_id": node_id, "type": node_type})
        values[node_id] = result
        return result

    root_value = value(model.root_id or "")
    root_policy = policy.get(model.root_id or "", [])
    root_policy_labels = policy_branch_labels.get(model.root_id or "", [])
    return {
        "tree_id": model.tree_id,
        "scenario_id": "base",
        "criterion": "expected_utility",
        "root_node": model.root_id,
        "root_value": root_value,
        "recommended_action": root_policy[0] if len(root_policy) == 1 else root_policy,
        "recommended_branch_label": root_policy_labels[0] if len(root_policy_labels) == 1 else root_policy_labels,
        "policy": policy,
        "policy_branch_labels": policy_branch_labels,
        "node_values": values,
        "dominated_branches": dominated,
    }


def branch_label(model: TreeModel, child_id: str) -> str:
    node = model.nodes.get(child_id, {})
    return str(node.get("branch_label") or child_id)


def adjusted_probability_model(model: TreeModel, chance_node_id: str, child_id: str, new_probability: float) -> TreeModel:
    if not 0 <= new_probability <= 1:
        raise UserError("Probability must be between 0 and 1.", {"probability": new_probability})
    clone = TreeModel(tree=deepcopy(model.tree), nodes=deepcopy(model.nodes), children=deepcopy(model.children))
    node = clone.nodes.get(chance_node_id)
    if not node or node.get("type") != "chance":
        raise UserError("Chance node not found.", {"node_id": chance_node_id})
    probs = node.get("probabilities", {})
    if child_id not in probs:
        raise UserError("Child probability not found.", {"node_id": chance_node_id, "child_id": child_id})
    siblings = [item for item in clone.children[chance_node_id] if item != child_id]
    old_sibling_mass = sum(float(probs[item]) for item in siblings)
    if siblings and old_sibling_mass <= 0:
        raise UserError("Cannot proportionally rescale zero-mass siblings.", {"node_id": chance_node_id})
    probs[child_id] = new_probability
    scale = (1.0 - new_probability) / old_sibling_mass if siblings else 0.0
    for sibling in siblings:
        probs[sibling] = float(probs[sibling]) * scale
    return clone


def set_utility_model(model: TreeModel, terminal_node_id: str, utility: float) -> TreeModel:
    clone = TreeModel(tree=deepcopy(model.tree), nodes=deepcopy(model.nodes), children=deepcopy(model.children))
    node = clone.nodes.get(terminal_node_id)
    if not node or node.get("type") != "terminal":
        raise UserError("Terminal node not found.", {"node_id": terminal_node_id})
    node["utility"] = utility
    return clone


def parse_param(param: str) -> tuple[str, str, str | None]:
    if "/" in param and not param.startswith(("probability:", "utility:")):
        node_id, child_id = param.split("/", 1)
        return "probability", node_id, child_id
    if param.startswith("probability:"):
        address = param.removeprefix("probability:")
        if "." not in address:
            raise UserError("Probability parameter must be probability:<chance_node>.<child_node>.", {"param": param})
        node_id, child_id = address.split(".", 1)
        return "probability", node_id, child_id
    if param.startswith("utility:"):
        return "utility", param.removeprefix("utility:"), None
    raise UserError(
        "Unsupported parameter address. Use probability:<chance_node>.<child_node> or utility:<terminal_node>.",
        {"param": param},
    )


def one_way_sensitivity(model: TreeModel, param: str, start: float, stop: float, steps: int) -> dict:
    if steps < 2:
        raise UserError("Steps must be at least 2.", {"steps": steps})
    kind, node_id, child_id = parse_param(param)
    samples = []
    recommendations: list[Any] = []
    for index in range(steps):
        x = start + (stop - start) * index / (steps - 1)
        if kind == "probability":
            sample_model = adjusted_probability_model(model, node_id, child_id or "", x)
        else:
            sample_model = set_utility_model(model, node_id, x)
        solved = solve_model(sample_model)
        recommendation = solved["recommended_action"]
        recommendation_label = solved["recommended_branch_label"]
        recommendations.append(recommendation)
        samples.append(
            {
                "value": x,
                "root_value": solved["root_value"],
                "recommended_action": recommendation,
                "recommended_branch_label": recommendation_label,
            }
        )
    thresholds = []
    for previous, current in zip(samples, samples[1:], strict=False):
        if previous["recommended_action"] != current["recommended_action"]:
            thresholds.append(
                {
                    "between": [previous["value"], current["value"]],
                    "from": previous["recommended_action"],
                    "from_branch_label": previous["recommended_branch_label"],
                    "to": current["recommended_action"],
                    "to_branch_label": current["recommended_branch_label"],
                }
            )
    return {"tree_id": model.tree_id, "param": param, "samples": samples, "thresholds": thresholds}


def evppi(model: TreeModel, chance_node_id: str) -> dict:
    base = solve_model(model)
    chance = model.nodes.get(chance_node_id)
    if not chance or chance.get("type") != "chance":
        raise UserError("Chance node not found.", {"node_id": chance_node_id})
    parent_id = chance.get("parent")
    if not parent_id or model.nodes[parent_id].get("type") != "decision":
        raise AnalysisError("V1 EVPPI requires the chance node to be a direct child of a decision node.", {"node_id": chance_node_id})
    sibling_actions = model.children[parent_id]
    value_with_info = 0.0
    states = []
    for state_id in model.children[chance_node_id]:
        probability = float(chance["probabilities"][state_id])
        state_values = {}
        for action_id in sibling_actions:
            if action_id == chance_node_id:
                state_values[action_id] = solve_model(subtree_model(model, state_id))["root_value"]
            else:
                state_values[action_id] = solve_model(subtree_model(model, action_id))["root_value"]
        best_action = max(state_values, key=state_values.get)
        best_value = state_values[best_action]
        value_with_info += probability * best_value
        states.append(
            {
                "state": state_id,
                "state_label": branch_label(model, state_id),
                "probability": probability,
                "best_action": best_action,
                "best_action_branch_label": branch_label(model, best_action),
                "best_value": best_value,
                "action_values": state_values,
                "action_branch_labels": {action_id: branch_label(model, action_id) for action_id in state_values},
            }
        )
    return {
        "tree_id": model.tree_id,
        "chance_node": chance_node_id,
        "current_value": base["root_value"],
        "value_with_information": value_with_info,
        "expected_value_of_information": value_with_info - base["root_value"],
        "states": states,
    }


def subtree_model(model: TreeModel, root_id: str) -> TreeModel:
    keep: set[str] = set()

    def collect(node_id: str) -> None:
        keep.add(node_id)
        for child_id in model.children.get(node_id, []):
            collect(child_id)

    collect(root_id)
    nodes = {node_id: deepcopy(node) for node_id, node in model.nodes.items() if node_id in keep}
    clone = TreeModel(tree=deepcopy(model.tree), nodes=nodes, children=index_children(nodes))
    clone.tree["root_node"] = root_id
    clone.nodes[root_id]["parent"] = None
    return clone


def mermaid(model: TreeModel) -> str:
    validate_model(model)
    lines = ["flowchart TD"]
    for node_id in reachable_order(model):
        node = model.nodes[node_id]
        label = str(node.get("label", node_id)).replace('"', "'")
        if node["type"] == "decision":
            rendered = f"{node_id}{{{label}}}"
        elif node["type"] == "chance":
            rendered = f"{node_id}(({label}))"
        else:
            rendered = f"{node_id}[{label}: U={node['utility']}]"
        lines.append(f"  {rendered}")
        for child_id in model.children.get(node_id, []):
            child = model.nodes[child_id]
            branch = child.get("branch_label", child_id)
            if node["type"] == "chance":
                branch = str(node["probabilities"].get(child_id, branch))
            lines.append(f"  {node_id} -->|{branch}| {child_id}")
    return "\n".join(lines) + "\n"


def reachable_order(model: TreeModel) -> list[str]:
    order: list[str] = []

    def visit(node_id: str) -> None:
        order.append(node_id)
        for child_id in model.children.get(node_id, []):
            visit(child_id)

    if model.root_id:
        visit(model.root_id)
    return order
