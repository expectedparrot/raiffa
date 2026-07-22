"""Generate a self-contained interactive HTML explorer for a raiffa decision tree."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .model import TreeModel


def build_explorer_html(model: TreeModel) -> str:
    """Return a complete, self-contained HTML page for interactively exploring the tree."""
    js_tree = _js_node(model, model.root_id)
    defaults = _defaults(model)
    chance_nodes = _chance_nodes(model)
    root_children = _root_children(model)
    sidebar = _sidebar(model, chance_nodes)
    title = _esc(model.tree.get("name", model.tree_id))

    html = _TEMPLATE
    html = html.replace("__TITLE__", title)
    html = html.replace("__TREE_JS__", json.dumps(js_tree, indent=2))
    html = html.replace("__DEFAULTS_JS__", json.dumps(defaults, indent=2))
    html = html.replace("__CHANCE_NODES_JS__", json.dumps(chance_nodes, indent=2))
    html = html.replace("__ROOT_CHILDREN_JS__", json.dumps(root_children, indent=2))
    html = html.replace("__SIDEBAR_HTML__", sidebar)
    return html


# ── Helpers ──────────────────────────────────────────────────────────────────

def _js_node(model: TreeModel, node_id: str) -> dict:
    node = model.nodes[node_id]
    children = model.children.get(node_id, [])
    result: dict = {
        "id": node_id,
        "type": node["type"],
        "label": node.get("label", node_id),
    }
    if node.get("branch_label"):
        result["edgeLabel"] = node["branch_label"]
    if node["type"] == "terminal":
        result["utilKey"] = f"u_{node_id}"
    elif children:
        js_children = []
        for child_id in children:
            child_js = _js_node(model, child_id)
            if node["type"] == "chance":
                child_js["probKey"] = f"p_{node_id}_{child_id}"
            js_children.append(child_js)
        result["children"] = js_children
    return result


def _defaults(model: TreeModel) -> dict:
    d: dict = {}
    for node_id, node in model.nodes.items():
        if node["type"] == "terminal" and node.get("utility") is not None:
            d[f"u_{node_id}"] = float(node["utility"])
        elif node["type"] == "chance":
            for child_id, prob in node.get("probabilities", {}).items():
                d[f"p_{node_id}_{child_id}"] = float(prob)
    return d


def _chance_nodes(model: TreeModel) -> list[dict]:
    result = []
    for node_id, node in model.nodes.items():
        if node["type"] != "chance":
            continue
        children = model.children.get(node_id, [])
        if len(children) < 2:
            continue
        result.append({
            "id": node_id,
            "label": node.get("label", node_id).replace("\n", " "),
            "controlled": children[:-1],
            "derived": children[-1],
        })
    return result


def _root_children(model: TreeModel) -> list[dict]:
    if not model.root_id:
        return []
    root = model.nodes.get(model.root_id, {})
    if root.get("type") != "decision":
        return []
    return [
        {"id": cid, "label": model.nodes[cid].get("branch_label", cid)}
        for cid in model.children.get(model.root_id, [])
    ]


def _sidebar(model: TreeModel, chance_nodes: list[dict]) -> str:
    parts: list[str] = []
    node_map = model.nodes

    for cn in chance_nodes:
        node = node_map[cn["id"]]
        probs = node.get("probabilities", {})
        sliders = ""
        for child_id in cn["controlled"]:
            child = node_map[child_id]
            bl = _esc(child.get("branch_label", child_id))
            key = f"p_{cn['id']}_{child_id}"
            val = float(probs.get(child_id, 0.5))
            sliders += (
                f'\n      <div class="sg">'
                f'\n        <div class="sl"><span>{bl}</span>'
                f'<span class="v" id="v-{key}">{val:.2f}</span></div>'
                f'\n        <input type="range" class="p" id="s-{key}" data-key="{key}"'
                f' min="0" max="1" step="0.05" value="{val:.2f}">'
                f"\n      </div>"
            )
        derived_child = node_map[cn["derived"]]
        derived_bl = _esc(derived_child.get("branch_label", cn["derived"]))
        derived_key = f"p_{cn['id']}_{cn['derived']}"
        derived_val = float(probs.get(cn["derived"], 0.0))
        parts.append(
            f'\n    <div class="sec">'
            f'\n      <div class="sec-title">{_esc(cn["label"])}</div>'
            f"{sliders}"
            f'\n      <div class="derived">{derived_bl} (derived) = '
            f'<span id="d-{derived_key}">{derived_val:.2f}</span></div>'
            f"\n    </div>"
        )

    terminals: list[str] = []

    def _collect(nid: str) -> None:
        n = node_map[nid]
        if n["type"] == "terminal":
            terminals.append(nid)
        for cid in model.children.get(nid, []):
            _collect(cid)

    if model.root_id:
        _collect(model.root_id)

    if terminals:
        sliders = ""
        for node_id in terminals:
            node = node_map[node_id]
            label = _esc(node.get("label", node_id).replace("\n", " "))
            key = f"u_{node_id}"
            val = float(node.get("utility", 0.5))
            sliders += (
                f'\n      <div class="sg">'
                f'\n        <div class="sl"><span>{label}</span>'
                f'<span class="v" id="v-{key}">{val:.2f}</span></div>'
                f'\n        <input type="range" class="u" id="s-{key}" data-key="{key}"'
                f' min="0" max="1" step="0.01" value="{val:.2f}">'
                f"\n      </div>"
            )
        parts.append(
            f'\n    <div class="sec">'
            f'\n      <div class="sec-title">Utilities</div>'
            f"{sliders}"
            f"\n    </div>"
        )

    parts.append('\n    <button class="reset" onclick="resetDefaults()">&#8635; Reset to defaults</button>')
    return "\n".join(parts)


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


# ── HTML template ─────────────────────────────────────────────────────────────
# Placeholders: __TITLE__ __TREE_JS__ __DEFAULTS_JS__ __CHANCE_NODES_JS__
#               __ROOT_CHILDREN_JS__ __SIDEBAR_HTML__

_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="color-scheme" content="light">
<title>__TITLE__ — Decision Explorer</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
:root{color-scheme:light}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f0f2f5;color:#212529;height:100vh;display:flex;flex-direction:column;overflow:hidden}
header{background:#1d3557;color:white;padding:10px 20px;display:flex;align-items:baseline;gap:14px;flex-shrink:0}
header h1{font-size:15px;font-weight:600}
header p{font-size:12px;opacity:.65}
#layout{display:flex;flex:1;overflow:hidden}
#sidebar{width:272px;flex-shrink:0;background:white;border-right:1px solid #dee2e6;overflow-y:auto;padding:14px 16px;font-size:12px}
#main{flex:1;display:flex;flex-direction:column;overflow:hidden}
#viz-wrap{flex:1;overflow:auto;padding:12px 16px}
#legend{display:flex;gap:14px;margin-bottom:10px;flex-wrap:wrap}
.li{display:flex;align-items:center;gap:5px;font-size:11px;color:#212529}
.sw{width:13px;height:13px}
.sw.dec{background:#f4a261;transform:rotate(45deg)}
.sw.ch{background:#457b9d;border-radius:50%}
.sw.t-hi{background:#2a9d8f;border-radius:2px}
.sw.t-mid{background:#e9ecef;border:1px solid #adb5bd;border-radius:2px}
.sw.t-lo{background:#ffd6cc;border:1px solid #e07b6a;border-radius:2px}
#results{background:white;border-top:1px solid #dee2e6;padding:10px 16px;flex-shrink:0}
#results h2{font-size:12px;font-weight:600;color:#495057;margin-bottom:8px}
#rankings{display:flex;gap:8px;flex-wrap:wrap}
.rc{background:#f8f9fa;border:1px solid #dee2e6;border-radius:6px;padding:7px 11px;min-width:150px}
.rc.best{background:#e6f4f1;border-color:#2a9d8f}
.rc .rn{font-size:10px;color:#6c757d}
.rc .rl{font-size:11px;font-weight:600;color:#212529;line-height:1.3;margin:2px 0}
.rc .re{font-size:15px;font-weight:700;font-family:monospace;color:#1d3557}
.rc.best .re{color:#2a9d8f}
.sec{margin-bottom:16px}
.sec-title{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:#6c757d;border-bottom:1px solid #f0f2f5;padding-bottom:5px;margin-bottom:8px}
.sg{margin-bottom:8px}
.sl{display:flex;justify-content:space-between;margin-bottom:2px}
.sl span:first-child{color:#495057}
.sl .v{font-weight:700;font-family:monospace;color:#1d3557;font-size:11px}
input[type=range]{-webkit-appearance:none;width:100%;height:4px;background:#dee2e6;border-radius:2px;outline:none}
input[type=range].p::-webkit-slider-thumb{-webkit-appearance:none;width:13px;height:13px;border-radius:50%;background:#457b9d;cursor:pointer}
input[type=range].u::-webkit-slider-thumb{-webkit-appearance:none;width:13px;height:13px;border-radius:50%;background:#2a9d8f;cursor:pointer}
.derived{font-size:10px;color:#6c757d;font-style:italic;margin-top:2px}
button.reset{width:100%;margin-top:4px;padding:6px;background:#f8f9fa;border:1px solid #dee2e6;border-radius:4px;font-size:11px;color:#495057;cursor:pointer}
button.reset:hover{background:#e9ecef}
</style>
</head>
<body>
<header>
  <h1>__TITLE__</h1>
  <p>Adjust probabilities and utilities — tree and rankings update live</p>
</header>
<div id="layout">
<div id="sidebar">
__SIDEBAR_HTML__
</div>
<div id="main">
  <div id="viz-wrap">
    <div id="legend">
      <div class="li"><div class="sw dec"></div>Decision</div>
      <div class="li"><div class="sw ch"></div>Chance</div>
      <div class="li"><div class="sw t-hi"></div>Terminal (high U)</div>
      <div class="li"><div class="sw t-mid"></div>Terminal (mid U)</div>
      <div class="li"><div class="sw t-lo"></div>Terminal (low U)</div>
      <div class="li"><svg width="28" height="12"><line x1="0" y1="6" x2="28" y2="6" stroke="#e76f51" stroke-width="2.5"/></svg>Optimal path</div>
      <div class="li"><svg width="28" height="12"><line x1="0" y1="6" x2="28" y2="6" stroke="#ced4da" stroke-width="1.5" stroke-dasharray="4 3"/></svg>Suboptimal</div>
    </div>
    <svg id="tree"></svg>
  </div>
  <div id="results">
    <h2>Rankings <span style="font-weight:400;color:#6c757d;font-size:11px">— updates live</span></h2>
    <div id="rankings"></div>
  </div>
</div>
</div>
<script>
const TREE = __TREE_JS__;
const DEFAULTS = __DEFAULTS_JS__;
const CHANCE_NODES = __CHANCE_NODES_JS__;
const ROOT_CHILDREN = __ROOT_CHILDREN_JS__;
let P = { ...DEFAULTS };

// ── EU computation ────────────────────────────────────────────────────────
function computeEU(node) {
  if (node.type === 'terminal') return node.eu = P[node.utilKey] ?? 0;
  if (node.type === 'chance')
    return node.eu = node.children.reduce((s,c) => s + (P[c.probKey]||0) * computeEU(c), 0);
  let best = -Infinity, bestId = null;
  for (const c of node.children) { const v = computeEU(c); if (v > best) { best = v; bestId = c.id; } }
  node.eu = best; node.optId = bestId; return best;
}

function markPath(node, on) {
  node.onPath = on;
  if (!node.children) return;
  for (const c of node.children) markPath(c, on && (node.type !== 'decision' || node.optId === c.id));
}

// ── Color scale (relative to current utility range) ───────────────────────
function tfill(u) {
  const vals = Object.entries(P).filter(([k]) => k.startsWith('u_')).map(([,v]) => v);
  if (!vals.length) return {bg:'#e9ecef', border:'#adb5bd', fg:'#212529'};
  const mx = Math.max(...vals), mn = Math.min(...vals), rng = mx - mn || 1;
  if (u >= mn + 0.67 * rng) return {bg:'#2a9d8f', border:'#264653', fg:'#fff'};
  if (u <= mn + 0.33 * rng) return {bg:'#ffd6cc', border:'#e07b6a', fg:'#333'};
  return {bg:'#e9ecef', border:'#adb5bd', fg:'#212529'};
}

// ── D3 render ─────────────────────────────────────────────────────────────
const W = 1360, H = 840;
const svg = d3.select('#tree').attr('width', W).attr('height', H);
const rg = svg.append('g').attr('transform', 'translate(8,10)');

function render() {
  computeEU(TREE); markPath(TREE, true);
  const hier = d3.hierarchy(TREE);
  d3.tree().size([H - 20, W - 190])(hier);
  rg.selectAll('*').remove();

  for (const lk of hier.links()) {
    const s = lk.source, t = lk.target, onPath = t.data.onPath;
    rg.append('path')
      .attr('d', d3.linkHorizontal().x(d => d.y).y(d => d.x)({source:s, target:t}))
      .attr('fill', 'none')
      .attr('stroke', onPath ? '#e76f51' : '#ced4da')
      .attr('stroke-width', onPath ? 2.5 : 1.5)
      .attr('stroke-dasharray', (!onPath && s.data.type === 'decision') ? '4 3' : null);

    const mx = (s.y+t.y)/2, my = (s.x+t.x)/2;
    const rawLabel = (s.data.type === 'chance' && t.data.probKey)
      ? 'p=' + (P[t.data.probKey]||0).toFixed(2)
      : (t.data.edgeLabel || '');
    if (rawLabel) {
      const lines = rawLabel.split('\\n');
      const tg = rg.append('text').attr('text-anchor','middle').attr('font-size',9)
        .attr('fill', onPath ? '#c0392b' : '#495057');
      lines.forEach((ln,i) => tg.append('tspan').attr('x',mx).attr('y', my - 4 + i*11).text(ln));
    }
  }

  for (const d of hier.descendants()) {
    const nd = d.data;
    const g = rg.append('g').attr('transform', `translate(${d.y},${d.x})`);
    const eu = nd.eu != null ? nd.eu.toFixed(3) : '';

    if (nd.type === 'decision') {
      const s = 20;
      g.append('polygon').attr('points', `0,${-s} ${s},0 0,${s} ${-s},0`)
        .attr('fill','#f4a261').attr('stroke','#e76f51').attr('stroke-width',1.5);
      nd.label.split('\\n').forEach((ln,i,a) => g.append('text')
        .attr('text-anchor','middle').attr('font-size',8).attr('fill','#333')
        .attr('y',(i-(a.length-1)/2)*10).text(ln));
      if (eu) g.append('text').attr('y',s+12).attr('text-anchor','middle')
        .attr('font-size',9).attr('font-weight','700').attr('fill','#1d3557').text('EU='+eu);

    } else if (nd.type === 'chance') {
      g.append('circle').attr('r',18).attr('fill','#457b9d').attr('stroke','#1d3557').attr('stroke-width',1.5);
      nd.label.split('\\n').forEach((ln,i,a) => g.append('text')
        .attr('text-anchor','middle').attr('font-size',8).attr('fill','#fff')
        .attr('y',(i-(a.length-1)/2)*10).text(ln));
      if (eu) g.append('text').attr('y',28).attr('text-anchor','middle')
        .attr('font-size',9).attr('font-weight','700').attr('fill','#1d3557').text('EU='+eu);

    } else {
      const u = P[nd.utilKey] ?? 0;
      const {bg, border, fg} = tfill(u);
      g.append('rect').attr('x',-44).attr('y',-22).attr('width',88).attr('height',44)
        .attr('rx',4).attr('fill',bg).attr('stroke',border).attr('stroke-width',1.5);
      const lines = nd.label.split('\\n');
      lines.forEach((ln,i) => g.append('text').attr('text-anchor','middle').attr('font-size',8)
        .attr('fill',fg).attr('y',(i-(lines.length-1)/2)*10-5).text(ln));
      g.append('text').attr('y',13).attr('text-anchor','middle')
        .attr('font-size',10).attr('font-weight','700').attr('fill',fg).text('U='+u.toFixed(2));
    }
  }
  updateRankings();
}

// ── Rankings ──────────────────────────────────────────────────────────────
function updateRankings() {
  if (!ROOT_CHILDREN.length) return;
  const opts = ROOT_CHILDREN.map(rc => {
    const child = (TREE.children || []).find(c => c.id === rc.id);
    return {label: rc.label, eu: child ? (child.eu ?? 0) : 0};
  }).sort((a,b) => b.eu - a.eu);
  document.getElementById('rankings').innerHTML = opts.map((o,i) =>
    `<div class="rc${i===0?' best':''}">` +
    `<div class="rn">#${i+1}${i===0?' \\u2190 Best':''}</div>` +
    `<div class="rl">${o.label}</div>` +
    `<div class="re">${o.eu.toFixed(3)}</div></div>`
  ).join('');
}

// ── Probability sync ──────────────────────────────────────────────────────
function sync() {
  for (const cn of CHANCE_NODES) {
    const sum = cn.controlled.reduce((s,cid) => s + (P['p_'+cn.id+'_'+cid]||0), 0);
    const dk = 'p_'+cn.id+'_'+cn.derived;
    P[dk] = Math.max(0, parseFloat((1-sum).toFixed(10)));
    const el = document.getElementById('d-'+dk);
    if (el) el.textContent = P[dk].toFixed(2);
  }
}

// ── Sliders ───────────────────────────────────────────────────────────────
document.querySelectorAll('input[type=range]').forEach(el => {
  el.addEventListener('input', function() {
    P[this.dataset.key] = +this.value;
    const vEl = document.getElementById('v-' + this.dataset.key);
    if (vEl) vEl.textContent = (+this.value).toFixed(2);
    sync(); render();
  });
});

function resetDefaults() {
  P = { ...DEFAULTS };
  document.querySelectorAll('input[type=range]').forEach(el => {
    const k = el.dataset.key;
    if (DEFAULTS[k] != null) {
      el.value = DEFAULTS[k];
      const vEl = document.getElementById('v-'+k);
      if (vEl) vEl.textContent = DEFAULTS[k].toFixed(2);
    }
  });
  sync(); render();
}

render();
</script>
</body>
</html>
"""
