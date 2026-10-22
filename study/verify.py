"""Recompute exact screening evidence and semantic controls; no timing thresholds."""
from pathlib import Path
import argparse
import copy
from fractions import Fraction as Q
import hashlib
import json
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from experiment import (Engines, PR, bracket_verdict, evaluate, full_moment,
                        point_screen, read_json, recount, require, source_data,
                        thresholds, verify_sources)


def reject(call, diagnostic):
    try:
        call()
    except (ValueError, KeyError) as error:
        require(diagnostic in str(error), "unexpected control failure: " + str(error))
    else:
        raise ValueError("negative control accepted: " + diagnostic)


def data_controls(data):
    cases = [
        ("omitted_owner", lambda d: d["rows"].pop(), "owner row inventory"),
        ("wrong_width", lambda d: d["rows"][0].__setitem__("width", d["rows"][0]["width"]+1), "owner width"),
        ("wrong_copy", lambda d: d["rows"][0].__setitem__("copy", -1), "copy identity"),
        ("wrong_time", lambda d: d["rows"][0].__setitem__("time", -1), "owner time range"),
        ("out_of_capacity", lambda d: d["rows"][0].__setitem__("offset", 1000), "owner capacity"),
        ("missing_local_child", lambda d: d["trace"]["local_profile"].__setitem__("1", d["trace"]["local_profile"]["1"]-1), "mass/deficit"),
        ("wrong_live_stock", lambda d: d["plan"].__setitem__("live", d["plan"]["live"]+1), "mass/deficit"),
        ("omitted_idle_rank", lambda d: d["owner_receipt"]["idle"].pop("48"), "idle receipt disagreement"),
        ("receipt_profile_drift", lambda d: d["arithmetic_receipt"]["profile"].__setitem__("1", 1), "profile receipt disagreement"),
        ("physical_stock_omitted", lambda d: d["finite_invoice"].__setitem__("physical_families", 7168), "physical stock sum"),
    ]
    passed = []
    for name, mutate, diagnostic in cases:
        changed = copy.deepcopy(data)
        mutate(changed)
        reject(lambda: recount(changed), diagnostic)
        passed.append(name)
    return passed


def arithmetic_controls(eng, model):
    plain = eng.screen.coefficients(model["profile"], 73, model["W"], False)
    charged = eng.screen.coefficients(model["profile"], 73, model["W"], True)
    rho = Q(32*73*sum(model["profile"].values()), 10**16*model["W"])
    lo, hi = eng.screen.logarithm(Q(73))
    require(plain[0]-charged[0] == rho == charged[6], "surcharge D")
    require(charged[1]-plain[1] == rho*lo and charged[2]-plain[2] == rho*hi
            and charged[3]-plain[3] == rho*lo*lo and charged[4]-plain[4] == rho*hi*hi
            and charged[5] >= hi, "surcharge E/F/L")
    # Pure logarithm caching must never reuse profile-dependent coefficients.
    changed = copy.deepcopy(model)
    changed["profile"][1] += 1
    cached = eng.screen.coefficients(changed["profile"], 73, changed["W"], True)
    require(cached[0] != charged[0] and cached[1:] != charged[1:], "profile counts not invalidated")
    eng.screen.logarithm.cache_clear()
    require(cached == eng.screen.coefficients(changed["profile"], 73, changed["W"], True),
            "warm/cold changed profile disagreement")
    changed["m"] = 74
    warm_width = eng.screen.coefficients(changed["profile"], 74, changed["W"], True)
    eng.screen.logarithm.cache_clear()
    require(warm_width == eng.screen.coefficients(changed["profile"], 74, changed["W"], True),
            "width cache invalidation")
    # An artificial exact interval checks both boundary equality rules.
    sample = {"root_lower": "1/1000", "root_upper": "2/1000"}
    require(bracket_verdict(Q(1,1000), sample) == "inconclusive"
            and bracket_verdict(Q(2,1000), sample) == "inconclusive", "strict bracket boundary")
    reject(lambda: point_screen(eng.screen, model, Q(-1), False), "negative threshold")
    reject(lambda: point_screen(eng.screen, model, Q(1), True), "threshold outside majorant domain")
    invalid = {**model, "W": 1}
    reject(lambda: point_screen(eng.screen, invalid, Q(1,1000), False), "no positive saving domain")
    return ["surcharge_D_E_F_L", "same_support_count_invalidation", "width_invalidation",
            "strict_bracket_boundary", "negative_threshold", "majorant_domain", "no_positive_saving"]


def full_reference_replay():
    with tempfile.TemporaryDirectory(prefix="pending2260-full-arithmetic-") as directory:
        target = Path(directory) / "receipt.json"
        child = subprocess.run([sys.executable, "-I", "-B",
                                str(PR / "arithmetic/verify.py"), "--out", str(target)],
                               capture_output=True, text=True, timeout=90)
        require(child.returncode == 0, "frozen full arithmetic failed: " + child.stderr[-2000:])
        result = read_json(target)
        require(result == read_json(PR / "arithmetic/EXPECTED.json"),
                "frozen complete arithmetic receipt changed")
    return {"status": result["status"], "exact_receipt_match": True,
            "outer_constraints": len(result["outer_constraints"]),
            "controls": result["controls_rejected"],
            "scope": "Complete inherited arithmetic stage only; native, owner-chart and precision proof replays remain inherited."}


def run():
    input_hash = verify_sources()
    data = source_data()
    model = recount(data)
    # Cross-bind inputs to the independent owner receipt and the arithmetic receipt.
    bindings = {"owners/OWNERS.json.gz": "owners_sha256",
                "local/data/forward.json": "source_trace_sha256",
                "owners/inputs/PLAN.json": "source_plan_sha256"}
    for name, field in bindings.items():
        require(hashlib.sha256((PR/name).read_bytes()).hexdigest() == data["owner_receipt"][field],
                "owner source binding")
    for name, digest in data["arithmetic_receipt"]["source_sha256"].items():
        require(hashlib.sha256((PR/name).read_bytes()).hexdigest() == digest, "arithmetic source binding")
    eng = Engines()
    models = []
    for bad in (False, True):
        bracket = eng.screen.screen(model["profile"], 73, model["W"], bad)
        checks = []
        for label, a in thresholds(bracket).items():
            screen = bracket_verdict(a, bracket)
            point = point_screen(eng.screen, model, a, bad)
            full = full_moment(eng, model, a, bad)
            require(screen == point["verdict"], "root/point screen disagreement on fixture")
            require(screen == "inconclusive" or screen == full["verdict"], "screen/full disagreement")
            for interval in full["moment_minus_one"].values():
                require(Q(point["moment_minus_one"][0]) <= Q(interval[0])
                        <= Q(interval[1]) <= Q(point["moment_minus_one"][1]),
                        "full interval outside quadratic envelope")
            # Observe actual evaluator calls, rather than trusting the gate's
            # reported engine count. The conservative atanh call has a separate
            # surcharge evaluation, as in the frozen original caller.
            calls = {"atanh": 0, "mercator": 0}
            original_atanh, original_mercator = eng.atanh.moment, eng.mercator.moment
            def counted_atanh(*args, **kwargs):
                calls["atanh"] += 1
                return original_atanh(*args, **kwargs)
            def counted_mercator(*args, **kwargs):
                calls["mercator"] += 1
                return original_mercator(*args, **kwargs)
            eng.atanh.moment, eng.mercator.moment = counted_atanh, counted_mercator
            try:
                gated = evaluate("reject_gate", eng, model, a, bad)
            finally:
                eng.atanh.moment, eng.mercator.moment = original_atanh, original_mercator
            expected_calls = {"atanh": 0, "mercator": 0} if point["verdict"] == "reject" else {
                "atanh": 1 + int(bad), "mercator": 1}
            require(calls == expected_calls, "gate evaluator invocation coverage")
            require(gated["verdict"] == full["verdict"], "gate changed decision")
            require(gated["full_engines"] == (0 if point["verdict"] == "reject" else 2),
                    "gate skipped required exact engines")
            checks.append({"name": label, "rate": str(a), "root_screen": screen,
                           "point_screen": point, "full": full, "reject_gate": gated})
        boundary_signs = {}
        for key in ("root_lower", "root_upper"):
            full = full_moment(eng, model, Q(bracket[key]), bad)
            require(full["verdict"] == ("accept" if key == "root_lower" else "reject"),
                    "screen bracket independent boundary sign")
            boundary_signs[key] = full
        models.append({"name": "conservative" if bad else "native", "surcharge": bad,
                       "bracket": bracket, "thresholds": checks,
                       "independent_boundary_signs": boundary_signs})
    controls = data_controls(data) + arithmetic_controls(eng, model)
    inherited_controls = eng.screen.controls()
    reference = full_reference_replay()
    require(verify_sources() == input_hash, "inputs changed during replay")
    return {"status": "PASS_PENDING2260_QUADRATIC_SCREEN",
            "input_manifest_sha256": input_hash, "model": model, "cases": models,
            "semantic_controls": controls, "inherited_pr1669_controls": inherited_controls,
            "full_reference_replay": reference,
            "scope": "Pricing threshold evidence for one frozen complete reported invoice; no supplier admission, native/physical proof, selected frontier or endpoint-grid replacement."}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--result", type=Path, default=HERE/"RESULT.json")
    args = ap.parse_args()
    # JSON object keys have a single canonical representation across write/read.
    result = json.loads(json.dumps(run()))
    if args.write:
        args.result.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n", encoding="utf-8", newline="\n")
    else:
        require(result == read_json(args.result), "result receipt mismatch")
    print(f'PASS_PENDING2260_QUADRATIC_SCREEN models=2 thresholds=8 '
          f'controls={len(result["semantic_controls"])} inherited_controls=12 full_arithmetic_match=True')


if __name__ == "__main__":
    main()
