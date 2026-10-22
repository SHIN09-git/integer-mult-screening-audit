"""Source-bound pending-invoice screening experiment.

SHIN09-git, with substantial OpenAI Codex assistance. Apache-2.0.
The surrogate and both exact moment engines are credited, frozen predecessors.
"""
from collections import Counter, defaultdict
from fractions import Fraction as Q
from functools import lru_cache
from pathlib import Path
import hashlib
import importlib.util
import json

HERE = Path(__file__).resolve().parent
PR = HERE / "inputs/pr2260"


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read_json(path):
    return json.loads(path.read_bytes())


def verify_sources(root=HERE):
    manifest = read_json(root / "INPUTS.json")
    for name, digest in manifest["files"].items():
        path = root / name
        require(path.resolve().is_relative_to(root.resolve()), "external source path")
        require(hashlib.sha256(path.read_bytes()).hexdigest() == digest,
                "frozen input changed: " + name)
    return hashlib.sha256((root / "INPUTS.json").read_bytes()).hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Engines:
    def __init__(self):
        self.screen = module("credited_pr1669_screen", HERE / "inputs/pr1669/verify.py")
        self.mercator = module("credited_pr2260_mercator", PR / "arithmetic/vendor/moment.py")
        self.atanh = module("credited_pr2260_atanh", PR / "arithmetic/vendor/base_two_moment.py")
        # Same pure-argument cache wrapper used by the frozen PR2260 caller.
        self.atanh.log_bounds = lru_cache(None)(self.atanh.log_bounds)

    def clear(self):
        self.screen.logarithm.cache_clear()
        self.mercator.logarithm.cache_clear()
        self.atanh.log_bounds.cache_clear()


def source_data():
    import gzip
    return {
        "trace": read_json(PR / "local/data/forward.json"),
        "plan": read_json(PR / "owners/inputs/PLAN.json"),
        "rows": json.loads(gzip.decompress((PR / "owners/OWNERS.json.gz").read_bytes())),
        "owner_receipt": read_json(PR / "owners/EXPECTED.json"),
        "arithmetic_receipt": read_json(PR / "arithmetic/EXPECTED.json"),
        "finite_invoice": read_json(PR / "local/data/finite-invoice.json"),
    }


def recount(data):
    """Recount the complete supplied local+residual profile; not native replay."""
    trace, plan, rows = data["trace"], data["plan"], data["rows"]
    owner, arithmetic = data["owner_receipt"], data["arithmetic_receipt"]
    widths = {int(k): v for k, v in trace["helper_widths"].items()}
    require(len(widths) == 436 and len(rows) == 72 * len(widths), "owner row inventory")
    calls = defaultdict(list)
    occupied = defaultdict(set)
    for row in rows:
        require(row["copy"] == 112 * row["owner_replica"] + row["port"], "copy identity")
        require(row["helper"] in widths and row["width"] == widths[row["helper"]], "owner width")
        require(0 <= row["time"] < len(plan["order"]), "owner time range")
        require(plan["order"][row["time"]] == [row["stage"], row["replica"]], "call order")
        key = f'{row["owner_replica"]},{row["child"]}'
        require(key in plan["windows"], "owner window identity")
        capacity, times = plan["windows"][key]
        require(row["time"] in times, "owner time window")
        require(0 <= row["port"] < 112, "port range")
        axes = set(range(row["offset"], row["offset"] + row["width"]))
        require(axes and min(axes) >= 0 and max(axes) < capacity, "owner capacity")
        bucket = (row["owner_replica"], row["child"], row["port"])
        require(not (axes & occupied[bucket]), "owner axis overlap")
        occupied[bucket].update(axes)
        calls[row["time"]].append(row)
    require(set(calls) == set(range(72)), "complete call inventory")
    for call in calls.values():
        require(len(call) == len(widths) and {r["helper"] for r in call} == set(widths),
                "per-call helper inventory")
        require(len({r["family"] for r in call}) == len(call), "per-call family uniqueness")
    idle = Counter()
    for key, (capacity, times) in plan["windows"].items():
        rep, child = map(int, key.split(","))
        for port in range(112):
            remain = capacity - len(occupied[(rep, child, port)])
            require(remain >= 0, "negative residual")
            if remain:
                idle[remain] += 1
    local = Counter({int(r): n for r, n in trace["local_profile"].items()})
    require(local and all(0 < r < 73 and type(n) is int and n > 0
                          for r, n in local.items()), "local invoice domain")
    profile = Counter({r: 72*n for r, n in local.items()})
    profile.update(idle)
    mass = sum(r*n for r, n in profile.items())
    live = plan["live"]
    require(live == 7168 and mass == 520704 and 73*live-mass == 2560, "mass/deficit")
    require(73*73 > 2*max(profile)**2, "halving guard")
    require(dict(profile) == {int(r): n for r, n in owner["profile"].items()}
            == {int(r): n for r, n in arithmetic["profile"].items()}, "profile receipt disagreement")
    require(dict(idle) == {int(r): n for r, n in owner["idle"].items()}, "idle receipt disagreement")
    invoice = data["finite_invoice"]
    require(invoice["actual_calls"] == 72 and invoice["actual_roles"] == len(rows)
            and invoice["helper_count"] == len(widths), "finite invoice inventory")
    require(invoice["physical_families"] == sum(invoice["physical_stock_identity"].values())
            == 7745, "physical stock sum")
    return {"profile": dict(sorted(profile.items())), "local": dict(sorted(local.items())),
            "idle": dict(sorted(idle.items())), "m": 73, "W": live,
            "rank_mass": mass, "deficit": 2560, "calls": 72, "owner_rows": len(rows)}


def bracket_verdict(a, bracket):
    lower, upper = Q(bracket["root_lower"]), Q(bracket["root_upper"])
    if a < lower:
        return "accept"
    if a > upper:
        return "reject"
    return "inconclusive"


def point_screen(engine, model, a, bad):
    """The same proved quadratic inequalities, evaluated at one target.

    No root bisection is needed for a threshold decision. Unsupported domains
    fail closed; equality or overlap yields inconclusive.
    """
    require(a >= 0, "negative threshold")
    d, elo, ehi, flo, fhi, ell, rho = engine.coefficients(
        model["profile"], model["m"], model["W"], bad)
    require(ell * d / elo < 3, "linear root ceiling crosses majorant pole")
    require(ell*a < 3, "threshold outside majorant domain")
    lower_gain = engine.gain(a, elo, flo)
    upper_gain = engine.gain(a, ehi, fhi, ell)
    verdict = "reject" if lower_gain > d else "accept" if upper_gain < d else "inconclusive"
    return {"verdict": verdict, "D": str(d), "surcharge_coefficient": str(rho),
            "moment_minus_one": [str(lower_gain-d), str(upper_gain-d)]}


def full_moment(engines, model, a, bad, dual=True):
    h, m, w = model["profile"], model["m"], model["W"]
    y = engines.atanh.moment(m, w, list(h.items()), a)
    if bad:
        extra = engines.atanh.moment(m, w, [(1, 32*m*m*sum(h.values()))], a)
        y = y[0] + extra[0]/10**16, y[1] + extra[1]/10**16
    intervals = {"atanh": y}
    if dual:
        x = engines.mercator.moment(h, m, w, a, bad)
        require(max(x[0], y[0]) <= min(x[1], y[1]), "independent interval disagreement")
        intervals["mercator"] = x
    decisions = {"accept" if hi < 1 else "reject" if lo > 1 else "inconclusive"
                 for lo, hi in intervals.values()}
    require(len(decisions) == 1, "independent verdict disagreement")
    return {"verdict": decisions.pop(), "engines": len(intervals),
            "moment_minus_one": {k: [str(lo-1), str(hi-1)] for k, (lo, hi) in intervals.items()}}


def evaluate(method, engines, model, a, bad):
    if method == "root_screen":
        b = engines.screen.screen(model["profile"], model["m"], model["W"], bad)
        return {"verdict": bracket_verdict(a, b), "full_engines": 0}
    if method == "point_screen":
        result = point_screen(engines.screen, model, a, bad)
        return {"verdict": result["verdict"], "full_engines": 0}
    if method in ("full_single", "full_dual"):
        result = full_moment(engines, model, a, bad, method == "full_dual")
        return {"verdict": result["verdict"], "full_engines": result["engines"]}
    if method == "reject_gate":
        screen = point_screen(engines.screen, model, a, bad)
        if screen["verdict"] == "reject":
            return {"verdict": "reject", "full_engines": 0, "screen_verdict": "reject"}
        full = full_moment(engines, model, a, bad, True)
        return {"verdict": full["verdict"], "full_engines": 2,
                "screen_verdict": screen["verdict"]}
    raise ValueError("unknown method")


def thresholds(bracket):
    selected = Q(836330098538459, 500000000000000000)
    b = Q(8417, 5000000)
    return {
        "selected_balanced_rate": selected/(1-selected),
        "advertised_complex_rate": b,
        "too_large_rate": b+Q(1, 10**5),
        "bracket_midpoint": (Q(bracket["root_lower"])+Q(bracket["root_upper"]))/2,
    }
