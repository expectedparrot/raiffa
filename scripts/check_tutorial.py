"""Execute the HTML tutorial in a fresh workspace and check its numerical claims.

Run: python3 scripts/check_tutorial.py
Use --write-assets to refresh the public memo, fixture copies, and diagrams.
No inference, network access, or installed raiffa executable is required.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shlex
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

REPO = Path(__file__).resolve().parents[1]
PAGE = REPO / "docs/index.html"


class Tutorial(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks = []
        self.active = None
        self.ids = set()
        self.references = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            if attrs["id"] in self.ids:
                raise ValueError(f"Duplicate page anchor: {attrs['id']}")
            self.ids.add(attrs["id"])
        if tag == "code" and "data-run" in attrs:
            self.active = []
            self.blocks.append((attrs["data-run"], self.active))
        for attribute in ("href", "src"):
            if attribute in attrs:
                self.references.append(attrs[attribute])

    def handle_endtag(self, tag):
        if tag == "code":
            self.active = None

    def handle_data(self, text):
        if self.active is not None:
            self.active.append(text)

    def check_links(self):
        for reference in self.references:
            parsed = urlsplit(reference)
            if parsed.scheme or parsed.netloc:
                continue
            if parsed.path:
                if not (PAGE.parent / unquote(parsed.path)).is_file():
                    raise ValueError(f"Missing local link: {reference}")
            elif parsed.fragment and unquote(parsed.fragment) not in self.ids:
                raise ValueError(f"Missing page anchor: {reference}")


def close(actual, expected):
    if not math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-7):
        raise ValueError(f"Numerical mismatch: {actual} != {expected}")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-assets", action="store_true")
    args = parser.parse_args()
    tutorial = Tutorial()
    tutorial.feed(PAGE.read_text())
    require(
        [name for name, _ in tutorial.blocks]
        == [
            "model",
            "solve",
            "threshold",
            "research",
            "sequence",
            "memo",
            "revise",
            "finish",
        ],
        "Missing or reordered executable tutorial chapters.",
    )
    with tempfile.TemporaryDirectory(prefix="raiffa-tutorial-") as directory:
        root = Path(directory)
        bin_dir = root / "bin"
        bin_dir.mkdir()
        command = bin_dir / "raiffa"
        command.write_text(
            f'#!/bin/sh\nexec {shlex.quote(sys.executable)} -m raiffa.cli "$@"\n'
        )
        command.chmod(0o755)
        (bin_dir / "python3").symlink_to(sys.executable)
        env = os.environ.copy()
        env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")
        env["PYTHONPATH"] = str(REPO) + os.pathsep + env.get("PYTHONPATH", "")
        env.pop("RAIFFA_PROJECT_DIR", None)
        source = "set -eu\n" + "\n\n".join("".join(code) for _, code in tutorial.blocks)
        result = subprocess.run(
            ["/bin/sh", "-c", source],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode:
            raise RuntimeError(
                f"Tutorial commands failed ({result.returncode}):\n{result.stderr[-5000:]}\n{result.stdout[-3000:]}"
            )
        workspace = root / "lawsuit"

        def response(name):
            data = json.loads((workspace / name).read_text())
            require(data["ok"] is True, f"Failed command response: {name}")
            return data["data"]

        base = response("solve-base.json")
        require(base["recommended_action"] == "settle", "Base recommendation changed.")
        close(base["expected_value"], -400000)
        trial = next(
            a for a in base["alternatives"] if a["initial_action"] == "litigate"
        )
        close(trial["expected_value"], -630000)
        close(response("win-threshold.json")["thresholds"][0]["value"], 19 / 24)
        close(response("damages-threshold.json")["thresholds"][0]["value"], 625000)
        close(response("perfect-information.json")["gross_value"], 150000)
        study = response("study-value.json")
        close(study["gross_value"], 44000)
        close(study["net_value"], 34000)
        require(
            response("research-agenda.json")["recommended_study"] == "case_review",
            "Study ranking changed.",
        )
        sequential = response("solve-sequential.json")
        require(
            sequential["recommended_action"] == "study",
            "Study-purchase policy changed.",
        )
        close(sequential["expected_value"], -366000)
        revised = response("solve-revised.json")
        require(
            revised["recommended_action"] == "litigate",
            "Revised recommendation changed.",
        )
        close(revised["expected_value"], -330000)
        attribution = response("recommendation-change.json")["parameter_changes"]
        require(
            len(attribution) == 1
            and attribution[0]["parameter"] == "p_win"
            and attribution[0]["changes_initial_action"],
            "The changed belief no longer explains the recommendation flip.",
        )
        require(
            response("final-state.json")["complete"],
            "Tutorial does not reach completion.",
        )
        require(
            (workspace / "revised-decision-memo.html").is_file(),
            "Revised memo missing.",
        )
        handoff = json.loads((workspace / "monitoring.json").read_text())
        require(
            handoff["owner_approved"] is False, "Handoff must not imply human approval."
        )

        sys.path.insert(0, str(REPO))
        from raiffa.decision.report import diagram

        assets = REPO / "docs/assets"
        generated = {
            "leg01-model.json": (REPO / "examples/leg01/model.json").read_bytes(),
            "leg01-sequential.json": (
                REPO / "examples/leg01/sequential.json"
            ).read_bytes(),
            "model-2.0.schema.json": (
                REPO / "raiffa/schemas/model-2.0.json"
            ).read_bytes(),
        }
        for name in ("leg01-model", "leg01-sequential"):
            generated[name + ".svg"] = diagram(
                json.loads(generated[name + ".json"])
            ).encode()
        if args.write_assets:
            assets.mkdir(exist_ok=True)
            for name, content in generated.items():
                (assets / name).write_bytes(content)
            (assets / "leg01-decision.html").write_bytes(
                (workspace / "decision-memo.html").read_bytes()
            )
        else:
            for name, content in generated.items():
                require(
                    (assets / name).read_bytes() == content,
                    f"Stale tutorial asset: {name}; run --write-assets.",
                )
        tutorial.check_links()
        print(
            f"Tutorial passed: {len(tutorial.blocks)} command blocks, expected numerical results, revision attribution, replay, completion, and local links."
        )
        if args.write_assets:
            print(f"Updated example memo and assets in {assets}")


if __name__ == "__main__":
    main()
