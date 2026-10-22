"""Paired follow-up of the noisy end-to-end gate comparison.

Adjacent fresh-process A/B pairs alternate order; thresholds and worker coverage
are identical to benchmark.py. Added because seven-run cold timings overlap.
"""
from pathlib import Path
import argparse
import json
import statistics
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pairs", type=int, default=21)
    ap.add_argument("--output", type=Path, default=HERE/"PAIRED-TIMINGS.json")
    args = ap.parse_args()
    if args.pairs < 3:
        raise ValueError("at least three pairs")
    scenarios = [("cold","advertised_complex_rate"),("cold","too_large_rate"),
                 ("cold","bracket_midpoint"),("batch","all_four")]
    rows = []
    for i in range(args.pairs):
        for mode, case in scenarios[i % 4:] + scenarios[:i % 4]:
            methods = ["full_dual","reject_gate"] if i % 2 == 0 else ["reject_gate","full_dual"]
            pair = {"pair":i,"mode":mode,"case":case,"order":methods,"samples":{}}
            for method in methods:
                argv = [sys.executable,"-I","-B",str(HERE/"benchmark.py"),"--worker",
                        "--variant","conservative","--method",method,"--mode",mode,"--case",case]
                start=time.perf_counter()
                child=subprocess.run(argv,capture_output=True,text=True,timeout=30)
                elapsed=time.perf_counter()-start
                if child.returncode:
                    raise ValueError(child.stderr)
                item=json.loads(child.stdout)
                item["seconds"]["end_to_end"]=elapsed
                pair["samples"][method]=item
            full=pair["samples"]["full_dual"]["seconds"]["end_to_end"]
            gate=pair["samples"]["reject_gate"]["seconds"]["end_to_end"]
            pair["gate_minus_full_seconds"]=gate-full
            pair["gate_time_reduction_percent"]=100*(1-gate/full)
            rows.append(pair)
        print(f"Completed pair {i+1}/{args.pairs}",flush=True)
    summaries=[]
    for mode,case in scenarios:
        group=[r for r in rows if r["mode"]==mode and r["case"]==case]
        summaries.append({"mode":mode,"case":case,"pairs":len(group),
            "full_median_seconds":statistics.median(r["samples"]["full_dual"]["seconds"]["end_to_end"] for r in group),
            "gate_median_seconds":statistics.median(r["samples"]["reject_gate"]["seconds"]["end_to_end"] for r in group),
            "paired_median_gate_minus_full_seconds":statistics.median(r["gate_minus_full_seconds"] for r in group),
            "paired_median_time_reduction_percent":statistics.median(r["gate_time_reduction_percent"] for r in group),
            "gate_faster_pairs":sum(r["gate_minus_full_seconds"]<0 for r in group),
            "paired_difference_range_seconds":[min(r["gate_minus_full_seconds"] for r in group),
                                               max(r["gate_minus_full_seconds"] for r in group)]})
    result={"reason":"Follow up overlapping cold end-to-end timings; fixed conservative fixture and adjacent alternating-order pairs.",
            "pairs_per_scenario":args.pairs,"workers":len(rows)*2,"summaries":summaries,"trials":rows,
            "scope":"Fresh processes, input hashes and full arithmetic recount charged. OS cache not flushed; one machine, no general performance guarantee."}
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")


if __name__=="__main__":
    main()
