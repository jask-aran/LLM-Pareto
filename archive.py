#!/usr/bin/env python3
"""Persist verbose collections as recoverable JSON records and SQLite snapshots."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import artificial_analysis_v2 as scraper


ARCHIVE_VERSION = 1
DEFAULT_DATA_DIR = Path("data")
DATABASE_NAME = "archive.sqlite3"
JSON_DIRECTORY = "json"

SCHEMA = """
CREATE TABLE IF NOT EXISTS collection_runs (
    run_id TEXT PRIMARY KEY,
    collected_at TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    schema_version INTEGER NOT NULL,
    job_json TEXT NOT NULL,
    response_sha256 TEXT NOT NULL,
    json_path TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS snapshots (
    run_id TEXT NOT NULL REFERENCES collection_runs(run_id) ON DELETE CASCADE,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    release_date TEXT,
    collected_at TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    PRIMARY KEY (run_id, entity_type, entity_id)
);
CREATE INDEX IF NOT EXISTS snapshots_entity_history
    ON snapshots(entity_type, entity_id, collected_at);
CREATE INDEX IF NOT EXISTS snapshots_payload_hash
    ON snapshots(entity_type, entity_id, payload_sha256);
"""


class ArchiveError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def paths(data_dir: Path) -> tuple[Path, Path]:
    return data_dir / DATABASE_NAME, data_dir / JSON_DIRECTORY


def connect_database(database: Path) -> sqlite3.Connection:
    database.parent.mkdir(parents=True, exist_ok=True)
    try:
        connection = sqlite3.connect(database)
        result = connection.execute("PRAGMA quick_check").fetchone()
        if result != ("ok",):
            raise ArchiveError(f"SQLite integrity check failed: {result!r}")
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = FULL")
        connection.executescript(SCHEMA)
        return connection
    except (sqlite3.DatabaseError, OSError) as exc:
        raise ArchiveError(
            f"Cannot use database {database}: {exc}. "
            "Preserve the JSON records and run `archive.py rebuild --replace`."
        ) from exc


def atomic_json_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)


def make_archive_record(job: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    collected_at = response.get("collected_at") or utc_now()
    return {
        "archive_version": ARCHIVE_VERSION,
        "run_id": uuid.uuid4().hex,
        "collected_at": collected_at,
        "job": job,
        "response_sha256": digest(response),
        "response": response,
    }


def json_relative_path(record: dict[str, Any]) -> Path:
    date = str(record["collected_at"])[0:10]
    year, month, day = date.split("-")
    job_type = record["job"]["type"]
    return Path(year, month, day, f"{record['collected_at'].replace(':', '')}_{job_type}_{record['run_id']}.json")


def entities(record: dict[str, Any]) -> Iterable[tuple[str, str, str | None, dict[str, Any]]]:
    response = record["response"]
    job_type = record["job"]["type"]
    data = response.get("data") or {}
    if job_type == "model_catalogue":
        for model in data.get("models") or []:
            yield "model_catalogue_entry", model["slug"], model.get("release_date"), model
    elif job_type == "models":
        models = [data["model"]] if "model" in data else data.get("models") or []
        for model in models:
            yield "model", model["slug"], (model.get("model_metadata") or {}).get("release_date"), model
    elif job_type == "coding_agents":
        for agent in data.get("coding_agents") or []:
            yield "coding_agent_configuration", agent["id"], None, agent
    else:
        raise ArchiveError(f"Unknown archive job type {job_type!r}")


def validate_archive_record(record: dict[str, Any], source: Path | None = None) -> None:
    label = str(source) if source else "archive record"
    required = {"archive_version", "run_id", "collected_at", "job", "response_sha256", "response"}
    missing = required - record.keys()
    if missing:
        raise ArchiveError(f"{label} is missing fields: {', '.join(sorted(missing))}")
    if record["archive_version"] != ARCHIVE_VERSION:
        raise ArchiveError(f"{label} uses unsupported archive version {record['archive_version']!r}")
    if digest(record["response"]) != record["response_sha256"]:
        raise ArchiveError(f"{label} failed its SHA-256 check")
    list(entities(record))


def insert_record(connection: sqlite3.Connection, record: dict[str, Any], relative_path: Path) -> None:
    validate_archive_record(record)
    response = record["response"]
    job_type = record["job"]["type"]
    connection.execute(
        "INSERT INTO collection_runs VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            record["run_id"], record["collected_at"], job_type,
            int(response.get("schema_version", 0)), canonical_json(record["job"]),
            record["response_sha256"], relative_path.as_posix(),
        ),
    )
    for entity_type, entity_id, release_date, payload in entities(record):
        connection.execute(
            "INSERT INTO snapshots VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                record["run_id"], entity_type, entity_id, release_date,
                record["collected_at"], canonical_json(payload), digest(payload),
            ),
        )


def persist(data_dir: Path, job: dict[str, Any], response: dict[str, Any]) -> Path:
    database, json_dir = paths(data_dir)
    record = make_archive_record(job, response)
    relative = json_relative_path(record)
    destination = json_dir / relative
    atomic_json_write(destination, record)
    try:
        with closing(connect_database(database)) as connection:
            with connection:
                insert_record(connection, record, relative)
    except Exception:
        # Deliberately retain the durable JSON record for a later rebuild.
        raise
    return destination


def collect(args: argparse.Namespace) -> list[Path]:
    written: list[Path] = []
    if not args.no_catalogue:
        job = {
            "type": "model_catalogue", "eligibility": args.eligibility,
            "include_deprecated": args.include_deprecated, "since": args.since,
        }
        response = scraper.build_model_catalog(
            timeout=args.timeout, eligibility=args.eligibility,
            include_deprecated=args.include_deprecated, since=args.since, verbose=True,
        )
        written.append(persist(args.data_dir, job, response))
    if args.models:
        slugs = scraper.parse_slugs(args.models)
        job = {"type": "models", "slugs": slugs, "evaluation_reference_model": args.evaluation_reference_model}
        response = scraper.extract_models(
            slugs, timeout=args.timeout,
            evaluation_reference_model=args.evaluation_reference_model, verbose=True,
        )
        written.append(persist(args.data_dir, job, response))
    if not args.no_coding_agents:
        job = {"type": "coding_agents", "selectors": args.coding_agent or []}
        response = scraper.extract_coding_agents(
            args.coding_agent or None, timeout=args.timeout, verbose=True,
        )
        written.append(persist(args.data_dir, job, response))
    if not written:
        raise ArchiveError("No collection jobs selected")
    return written


def load_json_records(json_dir: Path) -> list[tuple[Path, dict[str, Any]]]:
    records: list[tuple[Path, dict[str, Any]]] = []
    if not json_dir.exists():
        return records
    for path in sorted(json_dir.rglob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ArchiveError(f"Cannot read {path}: {exc}") from exc
        validate_archive_record(record, path)
        records.append((path.relative_to(json_dir), record))
    return records


def rebuild(data_dir: Path, replace: bool) -> tuple[int, int]:
    database, json_dir = paths(data_dir)
    records = load_json_records(json_dir)
    if database.exists() and not replace:
        raise ArchiveError(f"{database} already exists; pass --replace after preserving a backup")
    data_dir.mkdir(parents=True, exist_ok=True)
    temporary = data_dir / f".{DATABASE_NAME}.rebuild-{uuid.uuid4().hex}"
    try:
        with closing(connect_database(temporary)) as connection:
            with connection:
                for relative, record in records:
                    insert_record(connection, record, relative)
        for suffix in ("-wal", "-shm"):
            Path(str(database) + suffix).unlink(missing_ok=True)
        os.replace(temporary, database)
    finally:
        temporary.unlink(missing_ok=True)
    return len(records), sum(len(list(entities(record))) for _, record in records)


def verify(data_dir: Path) -> tuple[int, int]:
    database, json_dir = paths(data_dir)
    records = load_json_records(json_dir)
    if not database.exists():
        raise ArchiveError(f"Database {database} does not exist; run rebuild to create it")
    with closing(connect_database(database)) as connection:
        db_runs = connection.execute("SELECT COUNT(*) FROM collection_runs").fetchone()[0]
        db_snapshots = connection.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
        expected = {record["run_id"]: record["response_sha256"] for _, record in records}
        actual = dict(connection.execute("SELECT run_id, response_sha256 FROM collection_runs"))
        if actual != expected:
            raise ArchiveError("SQLite run IDs or response hashes do not match the JSON record set")
        expected_snapshots = {
            (record["run_id"], entity_type, entity_id): digest(payload)
            for _, record in records
            for entity_type, entity_id, _, payload in entities(record)
        }
        actual_snapshots: dict[tuple[str, str, str], str] = {}
        for run_id, entity_type, entity_id, payload_json, payload_sha256 in connection.execute(
            "SELECT run_id, entity_type, entity_id, payload_json, payload_sha256 FROM snapshots"
        ):
            try:
                payload = json.loads(payload_json)
            except json.JSONDecodeError as exc:
                raise ArchiveError(
                    f"SQLite payload for {entity_type}/{entity_id} is invalid JSON"
                ) from exc
            calculated = digest(payload)
            if calculated != payload_sha256:
                raise ArchiveError(
                    f"SQLite payload for {entity_type}/{entity_id} failed its SHA-256 check"
                )
            actual_snapshots[(run_id, entity_type, entity_id)] = payload_sha256
        if actual_snapshots != expected_snapshots:
            raise ArchiveError(
                "SQLite snapshot IDs or payload hashes do not match the JSON record set"
            )
    return db_runs, db_snapshots


def reset(data_dir: Path, confirmed: bool) -> Path | None:
    if not confirmed:
        raise ArchiveError("Reset requires --yes")
    resolved = data_dir.resolve()
    if resolved in {Path("/").resolve(), Path.cwd().resolve(), Path.home().resolve()}:
        raise ArchiveError(f"Refusing to reset broad directory {resolved}")
    if not data_dir.exists():
        data_dir.mkdir(parents=True)
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = data_dir.with_name(f"{data_dir.name}.reset-{stamp}")
    counter = 1
    while backup.exists():
        backup = data_dir.with_name(f"{data_dir.name}.reset-{stamp}-{counter}")
        counter += 1
    shutil.move(data_dir, backup)
    data_dir.mkdir(parents=True)
    return backup


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect_parser = subparsers.add_parser("collect", help="Collect verbose JSON and SQLite snapshots")
    collect_parser.add_argument("--models", action="append", default=[], help="Model slugs; comma-separated or repeatable")
    collect_parser.add_argument("--coding-agent", action="append", default=[], help="Limit coding agents by ID or exact label")
    collect_parser.add_argument("--no-catalogue", action="store_true")
    collect_parser.add_argument("--no-coding-agents", action="store_true")
    collect_parser.add_argument("--eligibility", choices=("all", "active", "general", "coding", "full"), default="active")
    collect_parser.add_argument("--include-deprecated", action="store_true")
    collect_parser.add_argument("--since")
    collect_parser.add_argument("--evaluation-reference-model", default=scraper.EVALUATION_REFERENCE_MODEL)
    collect_parser.add_argument("--timeout", type=float, default=30.0)

    rebuild_parser = subparsers.add_parser("rebuild", help="Reconstruct SQLite from JSON records")
    rebuild_parser.add_argument("--replace", action="store_true", help="Atomically replace an existing database")
    subparsers.add_parser("verify", help="Verify JSON hashes, SQLite integrity, and parity")
    reset_parser = subparsers.add_parser("reset", help="Move the data directory aside and start empty")
    reset_parser.add_argument("--yes", action="store_true", help="Confirm the reset")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command == "collect":
            written = collect(args)
            result = {"status": "success", "json_records": [str(path) for path in written]}
        elif args.command == "rebuild":
            runs, snapshots = rebuild(args.data_dir, args.replace)
            result = {"status": "success", "runs": runs, "snapshots": snapshots}
        elif args.command == "verify":
            runs, snapshots = verify(args.data_dir)
            result = {"status": "success", "runs": runs, "snapshots": snapshots}
        else:
            backup = reset(args.data_dir, args.yes)
            result = {"status": "success", "backup": str(backup) if backup else None}
    except (ArchiveError, scraper.ExtractionError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
