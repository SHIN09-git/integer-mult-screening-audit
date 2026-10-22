"""Recalculate timing summaries independently with the Python standard library.
Copyright 2026 JIN HANZHE. Licensed under Apache-2.0; see LICENSE.
"""
from __future__ import annotations
import ast
from collections import defaultdict
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import statistics as stats
import zipfile

FILES = ("TIMINGS.json", "PAIRED-TIMINGS.json", "COMPETITIVE-TIMINGS.json")
METHODS = ("root_screen", "point_screen", "full_single", "full_dual", "reject_gate")

def require(condition, message):
    if not condition:
        raise ValueError(message)

def read(path):
    return json.loads(Path(path).read_bytes())

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def compare(actual, expected, name):
    if isinstance(actual, dict):
        require(isinstance(expected, dict) and set(actual) == set(expected), "Keys differ: " + name)
        for key in actual:
            compare(actual[key], expected[key], name + "/" + key)
    elif isinstance(actual, list):
        require(isinstance(expected, list) and len(actual) == len(expected), "List differs: " + name)
        for i, (a, b) in enumerate(zip(actual, expected)):
            compare(a, b, name + "/" + str(i))
    elif isinstance(actual, (int, float)) and not isinstance(actual, bool):
        require(isinstance(expected, (int, float)) and math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12), "Number differs: " + name)
    else:
        require(actual == expected, "Value differs: " + name)

def distribution(values):
    quartiles = stats.quantiles(values, n=4, method="inclusive")
    return {"median": stats.median(values), "minimum": min(values), "maximum": max(values),
            "q1": quartiles[0], "q3": quartiles[2]}

def check_worker(row, result, manifest_hash):
    require(row["input_manifest_sha256"] == manifest_hash, "Timing input identity differs")
    case = next(x for x in result["cases"] if x["name"] == row["variant"])
    expected_cases = {x["name"]: x for x in case["thresholds"]}
    require(row["method"] in METHODS, "Unknown timing method")
    names = set(expected_cases) if row["mode"] == "batch" else {row["case"]}
    require(set(row["outcomes"]) == names, "Timing cases differ")
    for name, outcome in row["outcomes"].items():
        record = expected_cases[name]
        key = "root_screen" if row["method"] in ("root_screen", "point_screen") else None
        expected = record[key] if key else record["full"]["verdict"]
        require(outcome["verdict"] == expected, "Timing verdict differs")
        count = (0 if row["method"] in ("root_screen", "point_screen")
                 else record["reject_gate"]["full_engines"] if row["method"] == "reject_gate"
                 else 1 if row["method"] == "full_single" else 2)
        require(outcome["full_engines"] == count, "Timing fallback count differs")
    require(all(math.isfinite(t) and t >= 0 for t in row["seconds"].values()), "Invalid duration")
    if "end_to_end" in row["seconds"]:
        require(row["seconds"]["end_to_end"] >= row["seconds"]["worker_total"], "Invalid process duration")

def recalculate(study, timing_directory=None):
    study = Path(study)
    directory = Path(timing_directory) if timing_directory else study
    fixture = read(study / "RESULT.json")
    manifest_hash = sha(study / "INPUTS.json")
    initial, paired, competitive = [read(directory / x) for x in FILES]

    # Each first-run worker is fresh, but the measurements are not independent candidate invoices.
    groups = defaultdict(list)
    require(initial["workers"] == len(initial["trials"]), "First-run worker count")
    for row in initial["trials"]:
        check_worker(row, fixture, manifest_hash)
        groups[tuple(row[k] for k in ("method", "variant", "mode", "case"))].append(row)
    require(len(groups) == len(initial["summaries"]) == 50, "Expected 50 first-run scenarios")
    for summary in initial["summaries"]:
        key = tuple(summary[k] for k in ("method", "variant", "mode", "case"))
        group = groups[key]
        require(len(group) == initial["repetitions"], "Unequal repetition count")
        require(sorted(r["repeat"] for r in group) == list(range(initial["repetitions"])), "Repeat IDs")
        computed = {**dict(zip(("method", "variant", "mode", "case"), key)),
                    "samples": len(group),
                    "seconds": {k: distribution([r["seconds"][k] for r in group]) for k in group[0]["seconds"]},
                    "outcomes": group[0]["outcomes"]}
        compare(computed, summary, "First-run summary")

    paired_groups = defaultdict(list)
    require(paired["workers"] == 2 * len(paired["trials"]), "Paired worker count")
    for row in paired["trials"]:
        require(set(row["samples"]) == {"full_dual", "reject_gate"}, "Expected paired methods")
        for item in row["samples"].values():
            check_worker(item, fixture, manifest_hash)
        full = row["samples"]["full_dual"]["seconds"]["end_to_end"]
        gate = row["samples"]["reject_gate"]["seconds"]["end_to_end"]
        compare(gate - full, row["gate_minus_full_seconds"], "Pair difference")
        compare(100 * (1 - gate / full), row["gate_time_reduction_percent"], "Pair percentage")
        paired_groups[(row["mode"], row["case"])].append(row)
    require(len(paired_groups) == len(paired["summaries"]) == 4, "Expected four paired scenarios")
    paired_summary = []
    for summary in paired["summaries"]:
        group = paired_groups[(summary["mode"], summary["case"])]
        require(len(group) == paired["pairs_per_scenario"], "Pair count")
        require(sorted(r["pair"] for r in group) == list(range(paired["pairs_per_scenario"])), "Pair IDs")
        differences = [r["samples"]["reject_gate"]["seconds"]["end_to_end"] - r["samples"]["full_dual"]["seconds"]["end_to_end"] for r in group]
        reductions = [100 * (1 - r["samples"]["reject_gate"]["seconds"]["end_to_end"] / r["samples"]["full_dual"]["seconds"]["end_to_end"]) for r in group]
        computed = {"mode": summary["mode"], "case": summary["case"], "pairs": len(group),
                    "full_median_seconds": stats.median(r["samples"]["full_dual"]["seconds"]["end_to_end"] for r in group),
                    "gate_median_seconds": stats.median(r["samples"]["reject_gate"]["seconds"]["end_to_end"] for r in group),
                    "paired_median_gate_minus_full_seconds": stats.median(differences),
                    "paired_median_time_reduction_percent": stats.median(reductions),
                    "gate_faster_pairs": sum(x < 0 for x in differences),
                    "paired_difference_range_seconds": [min(differences), max(differences)]}
        compare(computed, summary, "Paired summary")
        paired_summary.append(computed)

    require(competitive["workers"] == 3 * len(competitive["trials"]), "Competitive worker count")
    require(competitive["source_sha256"] == sha(study / "COMPETITIVE-SOURCE.json"), "Competitive source identity")
    require(sorted(r["trial"] for r in competitive["trials"]) == list(range(len(competitive["trials"]))), "Triplet IDs")
    methods = ("full_dual", "root_screen", "reject_gate")
    for row in competitive["trials"]:
        require(set(row["samples"]) == set(methods) and set(row["order"]) == set(methods), "Triplet methods")
        for name, item in row["samples"].items():
            require(item["method"] == name and item["verdict"] == "reject" and Fraction(item["rate"]) == Fraction(84179, 50000000), "Competitive decision")
            require(item["full_engines"] == (2 if name == "full_dual" else 0), "Competitive fallback")
            require(0 <= item["arithmetic_seconds"] <= item["worker_seconds"] <= item["end_to_end_seconds"], "Competitive durations")
    competitive_summary = {}
    for name in methods:
        actual = [r["samples"][name]["end_to_end_seconds"] for r in competitive["trials"]]
        baseline = [r["samples"]["full_dual"]["end_to_end_seconds"] for r in competitive["trials"]]
        computed = {"trials": len(actual), "end_to_end_median_seconds": stats.median(actual),
                    "arithmetic_median_seconds": stats.median(r["samples"][name]["arithmetic_seconds"] for r in competitive["trials"]),
                    "paired_median_seconds_saved": stats.median(b - a for a, b in zip(actual, baseline)),
                    "paired_median_percent_saved": stats.median(100 * (1 - a / b) for a, b in zip(actual, baseline)),
                    "faster_trials": sum(a < b for a, b in zip(actual, baseline))}
        compare(computed, competitive["summaries"][name], "Competitive summary")
        competitive_summary[name] = computed
    return {"status": "passed", "workers": initial["workers"] + paired["workers"] + competitive["workers"],
            "worker_counts": dict(zip(FILES, [initial["workers"], paired["workers"], competitive["workers"]])),
            "initial_summary_groups": len(groups), "paired_summaries": paired_summary,
            "competitive_summaries": competitive_summary,
            "scope": "Recalculated from saved process samples; no timing value is a correctness threshold."}

def check_provenance(study):
    study = Path(study)
    p = read(study / "BENCHMARK-PROVENANCE.json")
    for name, record in p["benchmarks"].items():
        require(sha(study / name) == record["sha256"], "Benchmark file hash: " + name)
    require(p["total_fresh_process_workers"] == sum(x["workers"] for x in p["benchmarks"].values()) == 581, "Historical count")
    require(sha(study / "INPUTS.json") == p["input_manifest_sha256"], "Historical input hash")
    require(sha(study / "RESULT.json") == p["fixture_result_sha256"], "Historical result hash")
    archive = study / p["measured_harness_archive"]["path"]
    require(sha(archive) == p["measured_harness_archive"]["sha256"], "Measured harness archive")
    with zipfile.ZipFile(archive) as z:
        for name, expected in p["packaged_harness_sha256"].items():
            require(sha(study / name) == expected, "Packaged harness hash: " + name)
            matches = [entry for entry in z.namelist() if Path(entry).name == name]
            require(len(matches) == 1, "Measured harness entry: " + name)
            measured = z.read(matches[0])
            require(hashlib.sha256(measured).hexdigest() == p["harness_sha256"][name], "Measured harness hash: " + name)
            require(ast.dump(ast.parse(measured.decode("utf-8"))) == ast.dump(ast.parse((study / name).read_text(encoding="utf-8"))), "Measured and packaged Python AST differ")
    return {"status": "passed", "benchmark_files": len(p["benchmarks"]), "measured_harness_files": len(p["packaged_harness_sha256"]),
            "measured_packaged_python_ast_equal": True}

