"""Immutable content-addressed analyses and a serialized revision journal.

Each journal entry contains the entire model; its atomic rename is the commit
point. There is no separately updated current pointer to become inconsistent.
"""

from __future__ import annotations

import fcntl
import hashlib
import os
import re
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from raiffa import __version__
from raiffa.core.errors import ValidationError
from .model import canonical, digest, read_json, require, validate


def safe_id(value):
    require(
        bool(re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", value)),
        "Invalid artifact ID.",
        id=value,
    )
    return value


def atomic_bytes(path: Path, content: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class Store:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.data = self.root / ".raiffa"
        require(
            (self.data / "meta.json").is_file(),
            "Initialize a Raiffa project first.",
            path=str(self.root),
        )

    @contextmanager
    def locked(self):
        with (self.data / ".decision.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def history(self):
        entries, previous = [], None
        for path in sorted((self.data / "revisions").glob("*.json")):
            item = read_json(path)
            revision = item.get("revision")
            body = {k: v for k, v in item.items() if k != "revision"}
            expected = f"r{len(entries) + 1:06d}_{digest(body)}"
            require(
                revision == expected and path.stem == revision,
                "Revision hash or sequence mismatch.",
                path=str(path),
            )
            require(
                item["parent"] == previous, "Broken revision chain.", revision=revision
            )
            validate(item["model"])
            entries.append(item)
            previous = revision
        return entries

    def current(self, model_id):
        safe_id(model_id)
        entries = [r for r in self.history() if r["model"]["id"] == model_id]
        require(entries, "Unknown decision model.", model=model_id)
        return entries[-1]

    def has_model(self, model_id):
        return any(r["model"]["id"] == model_id for r in self.history())

    def verify_sources(self, model):
        for source in model["sources"]:
            path = self.data / "sources" / source["artifact_sha256"]
            try:
                sha = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError as exc:
                raise ValidationError(
                    "Frozen source is missing.", {"source": source["id"]}
                ) from exc
            require(
                sha == source["artifact_sha256"],
                "Frozen source was modified.",
                source=source["id"],
            )

    def load(self, model_id, strict=False):
        entry = self.current(model_id)
        self.verify_sources(entry["model"])
        return entry, validate(entry["model"], strict=strict)

    def commit(self, model, reason, artifacts, *, expected_revision=None, create=False):
        validate(model)
        require(reason.strip(), "A revision reason is required.")
        with self.locked():
            history = self.history()
            existing = [r for r in history if r["model"]["id"] == model["id"]]
            current = existing[-1] if existing else None
            if create and current:
                # Idempotent import of identical bytes is safe; changed imports must revise.
                require(
                    current["model"] == model, "Model already exists; use model revise."
                )
                self.verify_sources(model)
                return current
            if not create:
                require(
                    current and current["revision"] == expected_revision,
                    "Revision conflict; reload the current model before revising.",
                    expected=expected_revision,
                    actual=current["revision"] if current else None,
                )
            if current and current["model"] == model:
                return current
            for source in model["sources"]:
                sha = source["artifact_sha256"]
                content = artifacts.get(sha)
                existing_path = self.data / "sources" / sha
                if content is None and existing_path.exists():
                    content = existing_path.read_bytes()
                require(
                    content is not None and hashlib.sha256(content).hexdigest() == sha,
                    "Source artifact is unavailable or mismatched.",
                    source=source["id"],
                )
            # Orphan source blobs after a crash are harmless. Journal publication
            # is the sole accepted-state mutation and occurs last.
            for sha, content in artifacts.items():
                path = self.data / "sources" / sha
                if not path.exists():
                    atomic_bytes(path, content)
            body = {
                "schema_version": "raiffa.revision/1.0",
                "sequence": len(history) + 1,
                "parent": history[-1]["revision"] if history else None,
                "model_parent": current["revision"] if current else None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "actor": "cli_user",
                "reason": reason,
                "engine_version": __version__,
                "model": model,
            }
            revision = f"r{len(history) + 1:06d}_{digest(body)}"
            entry = {"revision": revision, **body}
            atomic_bytes(self.data / "revisions" / f"{revision}.json", canonical(entry))
            return entry

    def save_analysis(self, entry, kind, settings, result):
        body = {
            "schema_version": "raiffa.analysis/1.0",
            "engine_version": __version__,
            "model_revision": entry["revision"],
            "model": entry["model"],
            "kind": kind,
            "settings": settings,
            "result": result,
        }
        analysis_id = "a_" + digest(body)
        envelope = {"analysis_id": analysis_id, **body}
        with self.locked():
            path = self.data / "decision_analyses" / f"{analysis_id}.json"
            if path.exists():
                require(
                    read_json(path) == envelope, "Analysis artifact integrity failure."
                )
            else:
                atomic_bytes(path, canonical(envelope))
        return envelope

    def analysis(self, analysis_id):
        safe_id(analysis_id)
        item = read_json(self.data / "decision_analyses" / f"{analysis_id}.json")
        require(
            item.get("analysis_id") == analysis_id
            and "a_" + digest({k: v for k, v in item.items() if k != "analysis_id"})
            == analysis_id,
            "Analysis hash mismatch.",
            analysis=analysis_id,
        )
        entries = {r["revision"]: r for r in self.history()}
        require(
            item["model_revision"] in entries
            and entries[item["model_revision"]]["model"] == item["model"],
            "Analysis model differs from its revision.",
        )
        self.verify_sources(item["model"])
        return item

    def analyses(self, revision=None):
        result = [
            self.analysis(p.stem)
            for p in sorted((self.data / "decision_analyses").glob("*.json"))
        ]
        return [
            a for a in result if revision is None or a["model_revision"] == revision
        ]

    def doctor(self):
        revisions = self.history()
        for entry in revisions:
            self.verify_sources(entry["model"])
        analyses = self.analyses()
        reports = []
        for manifest_path in sorted(
            (self.data / "decision_reports").glob("*.manifest.json")
        ):
            manifest = read_json(manifest_path)
            require(
                manifest_path.name == f"{digest(manifest)}.manifest.json",
                "Report manifest hash mismatch.",
            )
            analysis = self.analysis(manifest["analysis_id"])
            for challenge in manifest["challenge_ids"]:
                require(
                    self.analysis(challenge)["model_revision"]
                    == analysis["model_revision"],
                    "Report mixes model revisions.",
                )
            artifact = self.data / "decision_reports" / manifest["artifact"]
            require(
                artifact.parent.resolve() == (self.data / "decision_reports").resolve(),
                "Unsafe report artifact path.",
            )
            require(
                artifact.is_file()
                and hashlib.sha256(artifact.read_bytes()).hexdigest()
                == manifest["sha256"],
                "Report artifact changed.",
            )
            reports.append(manifest)
        return {
            "valid": True,
            "revision_count": len(revisions),
            "analysis_count": len(analyses),
            "report_count": len(reports),
        }
