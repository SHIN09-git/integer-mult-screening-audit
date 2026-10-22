#!/usr/bin/env python3
"""Offline reproduction of the fixed integer-multiplication pricing experiment.
Copyright 2026 JIN HANZHE. Apache-2.0; see LICENSE.
"""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
import uuid

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
STUDY = ROOT / "study"
spec = importlib.util.spec_from_file_location("public_timing_audit", ROOT / "tools/audit_timings.py")
timing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(timing)

def read(path):
    return json.loads(Path(path).read_bytes())

def save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def verify_manifest(path):
    checked = 0
    with path.open(encoding="utf-8", newline="") as f:
        for record in csv.DictReader(f):
            target = (ROOT / record["path"]).resolve()
            if not target.is_relative_to(ROOT):
                raise ValueError("Manifest path escapes the package")
            if target.stat().st_size != int(record["bytes"]) or digest(target) != record["sha256"]:
                raise ValueError("Package file mismatch: " + record["path"])
            checked += 1
    return checked

def verify_public_changes():
    changes = read(ROOT / "provenance/PUBLIC_CHANGES.json")
    for item in changes["changes"]:
        if digest(ROOT / item["path"]) != item["public_sha256"]:
            raise ValueError("Public adaptation differs: " + item["path"])
    return len(changes["changes"])

def run(script, args, output):
    suffix = "-timing" if "--benchmark" in args else ""
    log = output / "logs" / (script.removesuffix(".py") + suffix + ".log")
    print("Running " + script, flush=True)
    started = time.monotonic()
    with log.open("w", encoding="utf-8") as f:
        result = subprocess.run([sys.executable, "-I", "-B", str(STUDY / script), *args],
                                cwd=ROOT, stdout=f, stderr=subprocess.STDOUT, timeout=1200)
    if result.returncode:
        raise RuntimeError(script + " failed; see " + str(log))
    return {"script": script, "exit_code": result.returncode, "seconds": round(time.monotonic() - started, 4), "log": log.name}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("audit", "verify", "benchmark"), default="verify")
    parser.add_argument("--output", type=Path, help="A new output directory; existing directories are refused")
    args = parser.parse_args()
    files = verify_manifest(ROOT / "MANIFEST_SHA256.csv")
    frozen = verify_manifest(ROOT / "provenance/FROZEN_SHA256.csv")
    modified = verify_public_changes()
    output = (args.output or ROOT / "reproductions" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6])).resolve()
    if output == ROOT or ROOT.is_relative_to(output):
        parser.error("Output must not be the package root or its ancestor")
    output.mkdir(parents=True, exist_ok=False)
    (output / "logs").mkdir()
    report = {"status": "running", "mode": args.mode, "started_at_utc": datetime.now(timezone.utc).isoformat(),
              "environment": {"python": platform.python_version(), "implementation": platform.python_implementation(),
                              "platform": platform.platform(), "dependencies": "Python standard library only"},
              "manifest_files": files, "unchanged_research_files": frozen, "documented_public_adaptations": modified}
    started = time.monotonic()
    try:
        report["historical_provenance"] = timing.check_provenance(STUDY)
        report["historical_timings"] = timing.recalculate(STUDY)
        save(output / "historical-timing-summary.json", report["historical_timings"])
        published_run = ROOT / "validation/20261022"
        if published_run.is_dir():
            report["published_release_timings"] = timing.recalculate(STUDY, published_run)
            save(output / "published-release-timing-summary.json", report["published_release_timings"])
        report["steps"] = []
        if args.mode != "audit":
            for script in ("verify.py", "competitive_target.py", "test_receipts.py"):
                report["steps"].append(run(script, [], output))
            result = read(STUDY / "RESULT.json")
            report["exact_scope"] = {
                "owner_rows": result["model"]["owner_rows"], "calls": result["model"]["calls"],
                "main_model_threshold_cases": sum(len(c["thresholds"]) for c in result["cases"]),
                "competitive_cases": len(read(STUDY / "COMPETITIVE-RESULT.json")["models"]),
                "semantic_controls": len(result["semantic_controls"]),
                "inherited_controls": result["inherited_pr1669_controls"],
                "source_receipt_corruptions": 4,
                "outer_constraints": result["full_reference_replay"]["outer_constraints"],
                "full_inherited_arithmetic_receipt_exact_match": result["full_reference_replay"]["exact_receipt_match"],
                "note": "Counts reported only after rerunning and matching the exact receipts. Does not verify the complete multiplication algorithm."}
        if args.mode == "benchmark":
            jobs = [
                ("benchmark.py", ["--repetitions", "7", "--output", str(output / "TIMINGS.json")]),
                ("paired_benchmark.py", ["--pairs", "21", "--output", str(output / "PAIRED-TIMINGS.json")]),
                ("competitive_target.py", ["--benchmark", "--trials", "21", "--output", str(output / "COMPETITIVE-TIMINGS.json")]),
            ]
            for script, argv in jobs:
                report["steps"].append(run(script, argv, output))
            # Remove the machine-specific interpreter path from newly generated metadata.
            p = output / "TIMINGS.json"
            data = read(p)
            data["environment"]["executable"] = "[local executable path omitted]"
            save(p, data)
            report["new_timings"] = timing.recalculate(STUDY, output)
            save(output / "new-timing-summary.json", report["new_timings"])
        report["frozen_files_unchanged_after_run"] = verify_manifest(ROOT / "provenance/FROZEN_SHA256.csv")
        report["manifest_files_unchanged_after_run"] = verify_manifest(ROOT / "MANIFEST_SHA256.csv")
        report["status"] = "passed"
    except Exception as error:
        report["status"] = "failed"
        report["error"] = str(error)
        raise
    finally:
        report["elapsed_seconds"] = round(time.monotonic() - started, 4)
        report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        save(output / "validation.json", report)
    print("PASS: " + args.mode + "; report: " + str(output / "validation.json"))

if __name__ == "__main__":
    main()

