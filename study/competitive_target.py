"""Apply the old PR2260 invoice to PR2284's published higher rate.

Follow-up chosen during the final overlap checkpoint, after the original four
thresholds were measured. It does not audit or reject PR2284's changed supplier.
"""
from pathlib import Path
from fractions import Fraction as Q
import argparse
import hashlib
import json
import statistics
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from experiment import (Engines, bracket_verdict, evaluate, full_moment,
                        point_screen, read_json, recount, require, source_data,
                        verify_sources)


def published_target():
    source=read_json(HERE/"COMPETITIVE-SOURCE.json")
    for row in source["files"]:
        require(hashlib.sha256((HERE/row["path"]).read_bytes()).hexdigest()==row["sha256"],
                "competitive source drift")
    receipt=read_json(HERE/"competitive-input/PRICE-EXPECTED.json")
    rate=Q(receipt["certified_complex_saving"])
    require(rate==Q(84179,50000000), "published target changed")
    require(all(Q(r["saving"])==rate for r in receipt["moments"] if r["side"].startswith("complex")),
            "published target source agreement")
    return rate, receipt


def verify():
    source_hash=verify_sources()
    rate, peer=published_target()
    model=recount(source_data())
    require(model["profile"]!={int(r):n for r,n in peer["profile"].items()},
            "accidentally substituted new PR2284 profile")
    eng=Engines()
    results=[]
    for bad in (False,True):
        root=eng.screen.screen(model["profile"],73,model["W"],bad)
        point=point_screen(eng.screen,model,rate,bad)
        full=full_moment(eng,model,rate,bad,True)
        gate=evaluate("reject_gate",eng,model,rate,bad)
        require(bracket_verdict(rate,root)==point["verdict"]==full["verdict"]==gate["verdict"]=="reject",
                "competitive threshold disagreement")
        require(gate["full_engines"]==0,"competitive early exit absent")
        require(Q(point["moment_minus_one"][0])>0,"missing positive lower bound")
        for lo,hi in full["moment_minus_one"].values():
            require(Q(point["moment_minus_one"][0])<=Q(lo)<=Q(hi)<=Q(point["moment_minus_one"][1]),
                    "competitive quadratic envelope")
        original=full_moment(eng,model,Q(8417,5000000),bad,True)
        require(original["verdict"]=="accept","original accepted rate was not preserved")
        results.append({"surcharge":bad,"root_screen":"reject","point_screen":point,
                        "full":full,"gate":gate,"old_advertised_rate_still_accepted":True})
    return {"status":"PASS_PUBLISHED_COMPETITIVE_THRESHOLD","old_invoice_pr":2260,
            "threshold_pr":2284,"threshold":str(rate),"old_invoice_profile":model["profile"],
            "input_manifest_sha256":source_hash,
            "competitive_source_sha256":hashlib.sha256((HERE/"COMPETITIVE-SOURCE.json").read_bytes()).hexdigest(),
            "models":results,
            "scope":"The old PR2260 invoice cannot meet PR2284's published higher rate. This does not reject PR2284's different improved profile, alter PR2260's original accepted claim, or audit PR2284's supplier."}


def worker(method):
    start=time.perf_counter()
    verify_sources()
    rate,_=published_target()
    model=recount(source_data())
    eng=Engines()
    prepared=time.perf_counter()
    answer=evaluate(method,eng,model,rate,True)
    ended=time.perf_counter()
    require(answer["verdict"]=="reject","competitive timed verdict")
    return {"method":method,"verdict":answer["verdict"],"rate":str(rate),
            "full_engines":answer["full_engines"],
            "preparation_seconds":prepared-start,"arithmetic_seconds":ended-prepared,
            "worker_seconds":ended-start}


def benchmark(args):
    rows=[]
    methods=["full_dual","root_screen","reject_gate"]
    for i in range(args.trials):
        order=methods[i%3:]+methods[:i%3]
        if i%2: order=list(reversed(order))
        row={"trial":i,"order":order,"samples":{}}
        for method in order:
            start=time.perf_counter()
            run=subprocess.run([sys.executable,"-I","-B",str(Path(__file__).resolve()),
                                "--worker",method],capture_output=True,text=True,timeout=30)
            elapsed=time.perf_counter()-start
            require(run.returncode==0,"competitive benchmark failed: "+run.stderr[-1000:])
            result=json.loads(run.stdout);result["end_to_end_seconds"]=elapsed
            row["samples"][method]=result
        rows.append(row)
        print(f"Completed competitive trial {i+1}/{args.trials}",flush=True)
    summary={}
    for method in methods:
        actual=[r["samples"][method]["end_to_end_seconds"] for r in rows]
        baseline=[r["samples"]["full_dual"]["end_to_end_seconds"] for r in rows]
        summary[method]={"trials":len(rows),"end_to_end_median_seconds":statistics.median(actual),
                         "arithmetic_median_seconds":statistics.median(r["samples"][method]["arithmetic_seconds"] for r in rows),
                         "paired_median_seconds_saved":statistics.median(b-a for b,a in zip(baseline,actual)),
                         "paired_median_percent_saved":statistics.median(100*(1-a/b) for b,a in zip(baseline,actual)),
                         "faster_trials":sum(a<b for a,b in zip(actual,baseline))}
    result={"scope":"Conservative old PR2260 invoice, same full preparation charged, at the source-pinned published PR2284 target 84179/50000000; adjacent fresh-process triplets with rotating/reversing order, OS cache not flushed.",
            "workers":len(rows)*3,"summaries":summary,"trials":rows,
            "source_sha256":hashlib.sha256((HERE/"COMPETITIVE-SOURCE.json").read_bytes()).hexdigest()}
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write",action="store_true")
    ap.add_argument("--benchmark",action="store_true")
    ap.add_argument("--worker",choices=["full_dual","root_screen","reject_gate"])
    ap.add_argument("--trials",type=int,default=21)
    ap.add_argument("--output",type=Path,default=HERE/"COMPETITIVE-TIMINGS.json")
    args=ap.parse_args()
    if args.worker:
        print(json.dumps(worker(args.worker)));return
    if args.benchmark:
        require(args.trials>=3,"at least three trials")
        benchmark(args);return
    result=json.loads(json.dumps(verify()))
    path=HERE/"COMPETITIVE-RESULT.json"
    if args.write: path.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")
    else: require(result==read_json(path),"competitive receipt mismatch")
    print("PASS_PUBLISHED_COMPETITIVE_THRESHOLD old_invoice=2260 target_pr=2284 models=2 reject no_rejection_of_new_supplier")


if __name__=="__main__":
    main()
