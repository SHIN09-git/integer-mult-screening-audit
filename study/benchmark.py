"""Reproducible sequential timing experiment; timings are descriptive, not tests.

Every worker is a fresh Python process, checks frozen hashes, recounts all
31,392 owner rows and imports the same three engines. No disk-cache flushing
or native/supplier replay is claimed. The batch mode reuses a single profile.
"""
from pathlib import Path
import argparse
from fractions import Fraction as Q
import json
import os
import platform
import random
import statistics
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from experiment import (Engines, bracket_verdict, evaluate, full_moment,
                        read_json, recount, require, source_data, verify_sources)

METHODS = ["root_screen", "point_screen", "full_single", "full_dual", "reject_gate"]


def prepared_point(screen, a, coefficients):
    d, elo, ehi, flo, fhi, ell, rho = coefficients
    require(a >= 0 and ell*d/elo < 3 and ell*a < 3, "surrogate domain")
    low, high = screen.gain(a, elo, flo), screen.gain(a, ehi, fhi, ell)
    return "reject" if low > d else "accept" if high < d else "inconclusive"


def batch_evaluate(method, eng, model, cases, bad):
    bracket = coeff = None
    if method == "root_screen":
        bracket = eng.screen.screen(model["profile"], 73, model["W"], bad)
    if method in ("point_screen", "reject_gate"):
        coeff = eng.screen.coefficients(model["profile"], 73, model["W"], bad)
    outcomes = {}
    for name, rate in cases.items():
        if method == "root_screen":
            outcomes[name] = {"verdict": bracket_verdict(rate, bracket), "full_engines": 0}
        elif method in ("point_screen", "reject_gate"):
            point = prepared_point(eng.screen, rate, coeff)
            if method == "point_screen" or point == "reject":
                outcomes[name] = {"verdict": point, "full_engines": 0}
            else:
                full = full_moment(eng, model, rate, bad, True)
                outcomes[name] = {"verdict": full["verdict"], "full_engines": 2}
        else:
            outcomes[name] = evaluate(method, eng, model, rate, bad)
    return outcomes


def worker(args):
    start = time.perf_counter()
    manifest = verify_sources()
    hash_end = time.perf_counter()
    data = source_data()
    model = recount(data)
    recount_end = time.perf_counter()
    eng = Engines()
    load_end = time.perf_counter()
    receipt = read_json(HERE/"RESULT.json")
    row = next(r for r in receipt["cases"] if r["name"] == args.variant)
    cases = {r["name"]: Q(r["rate"]) for r in row["thresholds"]}
    chosen = cases if args.mode == "batch" else {args.case: cases[args.case]}
    fixture_end = time.perf_counter()
    outcomes = batch_evaluate(args.method, eng, model, chosen, row["surcharge"])
    end = time.perf_counter()
    for name, actual in outcomes.items():
        expected = next(r for r in row["thresholds"] if r["name"] == name)
        target = expected["root_screen"] if args.method in ("root_screen", "point_screen") else expected["full"]["verdict"]
        require(actual["verdict"] == target, "timed result mismatch")
        if args.method == "reject_gate":
            require(actual["full_engines"] == expected["reject_gate"]["full_engines"], "timed gate coverage")
    return {"method": args.method, "variant": args.variant, "mode": args.mode,
            "case": args.case if args.mode == "cold" else "all_four",
            "seconds": {"input_hashes": hash_end-start, "read_and_recount": recount_end-hash_end,
                        "engine_imports": load_end-recount_end, "threshold_inputs": fixture_end-load_end,
                        "arithmetic": end-fixture_end, "worker_total": end-start},
            "input_manifest_sha256": manifest, "outcomes": outcomes}


def distribution(values):
    ordered = sorted(values)
    return {"median": statistics.median(values), "minimum": min(values), "maximum": max(values),
            "q1": statistics.quantiles(values, n=4, method="inclusive")[0],
            "q3": statistics.quantiles(values, n=4, method="inclusive")[2]}


def orchestrate(args):
    require(args.repetitions >= 3, "at least three repetitions")
    cases = ["selected_balanced_rate", "advertised_complex_rate", "too_large_rate", "bracket_midpoint"]
    base = [(m, v, "cold", c) for v in ("native", "conservative") for c in cases for m in METHODS]
    base += [(m, v, "batch", "all_four") for v in ("native", "conservative") for m in METHODS]
    rng = random.Random(22601669)
    trials = []
    started = time.time()
    for repeat in range(args.repetitions):
        jobs = list(base)
        rng.shuffle(jobs)
        for method, variant, mode, case in jobs:
            argv = [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--worker",
                    "--method", method, "--variant", variant, "--mode", mode, "--case", case]
            start = time.perf_counter()
            child = subprocess.run(argv, capture_output=True, text=True, timeout=30)
            elapsed = time.perf_counter()-start
            require(child.returncode == 0, "benchmark worker failed: " + child.stderr[-1500:])
            result = json.loads(child.stdout)
            result["seconds"]["end_to_end"] = elapsed
            result["repeat"] = repeat
            trials.append(result)
        print(f"Completed repetition {repeat+1}/{args.repetitions}", flush=True)
    summaries = []
    for method, variant, mode, case in base:
        group = [r for r in trials if (r["method"],r["variant"],r["mode"],r["case"]) == (method,variant,mode,case)]
        summaries.append({"method": method, "variant": variant, "mode": mode, "case": case,
                          "samples": len(group), "seconds": {k: distribution([r["seconds"][k] for r in group])
                                                           for k in group[0]["seconds"]},
                          "outcomes": group[0]["outcomes"]})
    result = {"scope": "Pricing stage only. Fresh processes and cold Python caches; operating-system file cache not flushed. Source hashes and owner recount charged to every method. Frozen source supplier/native/physical proofs remain inherited.",
              "repetitions": args.repetitions, "workers": len(trials), "order_seed": 22601669,
              "elapsed_seconds": time.time()-started,
              "environment": {"python": platform.python_version(), "implementation": platform.python_implementation(),
                              "platform": platform.platform(), "machine": platform.machine(),
                              "processor": platform.processor(), "logical_cpus": os.cpu_count(),
                              "executable": sys.executable},
              "summaries": summaries, "trials": trials}
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n",encoding="utf-8",newline="\n")
    print("BENCHMARK_WRITTEN", args.output)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--worker", action="store_true")
    ap.add_argument("--method", choices=METHODS, default="root_screen")
    ap.add_argument("--variant", choices=["native","conservative"], default="conservative")
    ap.add_argument("--mode", choices=["cold","batch"], default="cold")
    ap.add_argument("--case", default="advertised_complex_rate")
    ap.add_argument("--repetitions", type=int, default=7)
    ap.add_argument("--output", type=Path, default=HERE/"TIMINGS.json")
    args = ap.parse_args()
    if args.worker:
        print(json.dumps(worker(args)))
    else:
        orchestrate(args)


if __name__ == "__main__":
    main()
