from __future__ import annotations

import html

from .engine import compile_tree, dominance
from .model import validate


def esc(value):
    return html.escape(str(value), quote=True)


def number(value):
    return f"{value:,.6f}".rstrip("0").rstrip(".")


def table(headers, rows):
    return (
        "<table><thead><tr>"
        + "".join(f"<th>{esc(h)}</th>" for h in headers)
        + "</tr></thead><tbody>"
        + "".join(
            "<tr>" + "".join(f"<td>{esc(cell)}</td>" for cell in row) + "</tr>"
            for row in rows
        )
        + "</tbody></table>"
    )


def diagram(raw):
    model = validate(raw)
    levels, counts, positions = {}, {}, {}
    for key in model.order:
        parents = [a["from"] for a in raw["arcs"] if a["to"] == key]
        level = max((levels[p] + 1 for p in parents), default=0)
        levels[key] = level
        positions[key] = (40 + level * 290, 60 + counts.get(level, 0) * 145)
        counts[level] = counts.get(level, 0) + 1
    height = 40 + max(y + 60 for _, y in positions.values())
    width = 40 + max(x + 220 for x, _ in positions.values())
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="Influence diagram">',
        '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#334155"/></marker></defs>',
        f'<rect width="{width}" height="{height}" fill="white"/>',
    ]
    for arc in raw["arcs"]:
        x, y = positions[arc["from"]]
        xx, yy = positions[arc["to"]]
        dashed = ' stroke-dasharray="6 4"' if arc["kind"] == "information" else ""
        parts.append(
            f'<path d="M{x + 220},{y + 30} L{xx},{yy + 30}" stroke="#334155" fill="none" marker-end="url(#arrow)"{dashed}/>'
        )
    for key, (x, y) in positions.items():
        kind = model.nodes[key]["kind"]
        color = {"decision": "#dbeafe", "chance": "#fef3c7", "value": "#dcfce7"}[kind]
        radius = 28 if kind == "chance" else 4
        parts.append(
            f'<rect x="{x}" y="{y}" width="220" height="60" rx="{radius}" fill="{color}" stroke="#334155"/>'
        )
        parts.append(
            f'<text x="{x + 110}" y="{y + 25}" text-anchor="middle" fill="#0f172a" font-family="sans-serif" font-size="14">{esc(key)}</text>'
        )
        parts.append(
            f'<text x="{x + 110}" y="{y + 45}" text-anchor="middle" fill="#334155" font-family="sans-serif" font-size="12">{kind}</text>'
        )
    parts.append(
        '<text x="40" y="25" font-family="sans-serif" font-size="14" fill="#0f172a">Dashed arcs: information available before deciding</text></svg>'
    )
    return "".join(parts)


def tree_diagram(raw):
    """Small deterministic compiled tree; information-set constraints stay visible."""
    from raiffa.core.errors import AnalysisError

    try:
        tree = compile_tree(validate(raw), budget=150)
    except AnalysisError:
        return "<p>The compiled tree exceeds the report diagram budget. Export it with model compile; the influence diagram above remains available.</p>"
    nodes = tree["nodes"]
    positions = {}
    leaves = 0

    def place(key, depth):
        nonlocal leaves
        children = [b["child"] for b in nodes[key].get("branches", [])]
        if children:
            ys = [place(c, depth + 1) for c in children]
            y = sum(ys) / len(ys)
        else:
            y = 35 + leaves * 58
            leaves += 1
        positions[key] = (25 + depth * 230, y)
        return y

    place(0, 0)
    width = max(x for x, _ in positions.values()) + 220
    height = max(80, leaves * 58 + 20)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="Compiled decision tree">',
        f'<rect width="{width}" height="{height}" fill="white"/>',
    ]
    for n in nodes:
        x, y = positions[n["id"]]
        for b in n.get("branches", []):
            xx, yy = positions[b["child"]]
            label = b["state"] + (
                f" ({number(b['probability'])})" if "probability" in b else ""
            )
            parts.extend(
                [
                    f'<path d="M{x + 155},{y} L{xx},{yy}" stroke="#94a3b8" fill="none"/>',
                    f'<text x="{x + 159}" y="{(y + yy) / 2 - 5}" font-family="sans-serif" font-size="10" fill="#334155">{esc(label)}</text>',
                ]
            )
        title = n.get("source_node", number(n["payoff"]) if "payoff" in n else "")
        parts.append(
            f'<rect x="{x}" y="{y - 17}" width="155" height="34" rx="5" fill="#eef2f6" stroke="#475569"/>'
        )
        parts.append(
            f'<text x="{x + 7}" y="{y + 4}" font-family="sans-serif" font-size="12" fill="#0f172a">{esc(title)}</text>'
        )
    parts.append(
        "</svg><p>Branches enumerate possible histories. Decisions with identical observed information must share one action; hidden outcomes do not grant foresight.</p>"
    )
    return "".join(parts)


def policy_text(rows):
    return "; ".join(
        f"{r['decision']}: {r['action']}"
        + (
            " when " + ", ".join(f"{k}={v}" for k, v in r["when"].items())
            if r["when"]
            else ""
        )
        for r in rows
        if r.get("reach_probability", 1) > 0
    )


def risk_chart(result):
    alternatives = result["alternatives"] or [result]
    points = [r["payoff"] for a in alternatives for r in a["risk_profile"]]
    lo, hi = min(points), max(points)
    pad = max((hi - lo) * 0.08, 1)
    lo, hi = lo - pad, hi + pad

    def x(value):
        return 100 + (value - lo) / (hi - lo) * 720

    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 280" role="img" aria-label="Policy payoff CDFs">',
        '<rect width="900" height="280" fill="white"/>',
        '<path d="M100,45 V225 H820" fill="none" stroke="#64748b"/>',
    ]
    for i, a in enumerate(alternatives):
        color = ["#2563eb", "#d97706", "#059669", "#9333ea"][i % 4]
        path = "M100,225"
        for row in a["risk_profile"]:
            path += f" H{x(row['payoff']):.3f} V{225 - row['cdf'] * 180:.3f}"
        path += " H820"
        parts.append(
            f'<path d="{path}" fill="none" stroke="{color}" stroke-width="3"/>'
        )
        parts.append(
            f'<text x="{100 + i * 180}" y="25" fill="{color}" font-family="sans-serif" font-size="13">{esc(a.get("initial_action", "Policy"))}</text>'
        )
    for value in (lo + pad, (lo + hi) / 2, hi - pad):
        parts.append(
            f'<text x="{x(value):.3f}" y="247" text-anchor="middle" font-family="sans-serif" font-size="12">{number(value)}</text>'
        )
    parts.extend(
        [
            '<text x="90" y="50" text-anchor="end" font-family="sans-serif" font-size="12">1.0</text>',
            '<text x="90" y="225" text-anchor="end" font-family="sans-serif" font-size="12">0.0</text>',
            f'<text x="460" y="270" text-anchor="middle" font-family="sans-serif" font-size="12">Payoff ({esc(result["unit"])}); vertical axis P(payoff ≤ x)</text></svg>',
        ]
    )
    return "".join(parts)


def render(analysis, challenges):
    result, raw = analysis["result"], analysis["model"]
    parts = [
        '<!DOCTYPE html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{esc(raw['title'])} — Raiffa decision memo</title>",
        "<style>body{font:16px/1.55 system-ui,sans-serif;color:#172033;background:#fff;max-width:1080px;margin:40px auto;padding:0 24px}table{border-collapse:collapse;width:100%;margin:20px 0}th,td{text-align:left;border-bottom:1px solid #ccd5df;padding:9px}th{background:#eef2f6}svg{max-width:100%}code,pre{white-space:pre-wrap;overflow-wrap:anywhere}small{color:#475569}.lead{font-size:22px}</style>",
        f'<h1>{esc(raw["title"])}</h1><p class="lead">Recommended: {esc(result["recommended_action"] or "follow the contingent policy below")}. Expected payoff: {number(result["expected_value"])} {esc(result["unit"])}.</p>',
        f"<p>Decision maker: {esc(raw['decision_maker'])}. Risk-neutral evaluation on {esc(raw['valuation_context']['valuation_date'])}. Status: {esc(result['recommendation_status'].replace('_', ' '))}.</p>",
        "<p>This recommendation is conditional on the recorded assumptions and evidence. It does not record the decision owner’s approval.</p>",
        "<h2>Decision and information structure</h2>",
        diagram(raw),
        "<h2>Compiled tree</h2>",
        tree_diagram(raw),
        "<h2>Policy</h2>",
        table(
            ["Decision", "Observed information", "Action", "Reach probability"],
            [
                [
                    r["decision"],
                    ", ".join(f"{k}={v}" for k, v in r["when"].items())
                    or "No prior observation",
                    r["action"],
                    number(r["reach_probability"]),
                ]
                for r in result["policy"]
                if r["reach_probability"] > 0
            ],
        ),
        "<h2>Alternatives and risk profiles</h2>",
        risk_chart(result),
    ]
    for alternative in result["alternatives"] or [result]:
        parts.append(
            f"<h3>{esc(alternative.get('initial_action', 'Optimal policy'))}</h3>"
        )
        parts.append(
            table(
                ["Payoff", "Probability", "CDF"],
                [
                    [number(r["payoff"]), number(r["probability"]), number(r["cdf"])]
                    for r in alternative["risk_profile"]
                ],
            )
        )
    parts.extend(
        [
            "<h2>First-order stochastic dominance</h2>",
            (
                table(
                    ["Dominating action", "Dominated action"],
                    [
                        [r["dominates"], r["dominated"]]
                        for r in dominance(result)["relations"]
                    ],
                )
                if dominance(result)["relations"]
                else "<p>No first-order dominance was found between the compared initial-action policies.</p>"
            ),
            "<h2>Switching conditions</h2>",
        ]
    )
    thresholds = [a for a in challenges if a["kind"] == "sensitivity"]
    if not thresholds:
        parts.append(
            "<p>No threshold analysis recorded for this revision. The recommendation has not been tested for switching conditions.</p>"
        )
    for a in thresholds:
        s = a["result"]
        parts.append(
            f"<h3>{esc(s['parameter'])}</h3><p>{esc(s['held_fixed'])} Domain: {esc(s['domain'])}. Coverage: {esc(s['coverage'])}.</p>"
        )
        parts.append(
            table(
                ["Switch value", "Unit", "Residual"],
                [
                    [number(t["value"]), s["unit"], number(t["residual"])]
                    for t in s["thresholds"]
                ],
            )
        )
        for region in s["regions"]:
            parts.append(
                f"<p>Between {number(region['from'])} and {number(region['to'])}: {esc(policy_text(region['policy']))}. Boundaries may tie.</p>"
            )
    parts.append("<h2>Value of information and research</h2>")
    research = [a for a in challenges if a["kind"] in ("research", "perfect", "sample")]
    if not research:
        parts.append("<p>No information-value analysis recorded for this revision.</p>")
    for a in research:
        data = a["result"]
        if a["kind"] == "research":
            parts.append(
                table(
                    ["Study", "Gross value", "Cost", "Net value"],
                    [
                        [
                            s["study_id"],
                            number(s["gross_value"]),
                            number(s["cost"]),
                            number(s["net_value"]),
                        ]
                        if s["status"] == "evaluated"
                        else [s["study_id"], "Not evaluable: " + s["reason"], "—", "—"]
                        for s in data["studies"]
                    ],
                )
            )
            parts.append(
                f"<p>Highest positive net value: {esc(data['recommended_study'] or 'none')}. {esc(data['interpretation'])}</p>"
            )
        else:
            label = (
                "Perfect information about " + ", ".join(data["targets"])
                if a["kind"] == "perfect"
                else "Study: " + data["study_id"]
            )
            parts.append(
                f"<h3>{esc(label)}</h3><p>Gross value: {number(data['gross_value'])} {esc(data['unit'])}. Information arrives before {esc(data['before'])}.</p>"
            )
            if "net_value" in data:
                parts.append(
                    f"<p>Cost: {number(data['cost'])}. Net value: {number(data['net_value'])}.</p>"
                )
            parts.append(f"<p>{esc(policy_text(data['policy_with_information']))}.</p>")
    model = validate(raw)
    parts.extend(
        [
            "<h2>Parameter provenance and limitations</h2>",
            table(
                [
                    "Parameter",
                    "Value/expression",
                    "Unit",
                    "Source",
                    "Owner",
                    "Rationale",
                ],
                [
                    [
                        p["id"],
                        number(model.values[p["id"]]),
                        p["unit"],
                        p.get("provenance", {}).get("source_type", "MISSING"),
                        p.get("provenance", {}).get("owner", "MISSING"),
                        p.get("provenance", {}).get("rationale", "MISSING"),
                    ]
                    for p in raw["parameters"]
                ],
            ),
            "<p>Finite discrete states, a single valuation date, additive monetary payoffs, and risk neutrality. Named assumptions are not empirical verification. Research ranks are independent comparisons, not a portfolio optimum.</p>",
            f"<p><small>Model revision: {esc(analysis['model_revision'])}<br>Analysis: {esc(analysis['analysis_id'])}<br>Engine: {esc(analysis['engine_version'])}</small></p></html>",
        ]
    )
    return "".join(parts)
