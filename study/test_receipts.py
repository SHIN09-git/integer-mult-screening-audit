"""Source-integrity and altered-receipt controls, including optimized Python."""
from pathlib import Path
import copy
import json
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from experiment import read_json, require, verify_sources


def main():
    expected = read_json(HERE/"RESULT.json")
    controls = []
    with tempfile.TemporaryDirectory(prefix="pending2260-mutation-") as directory:
        root = Path(directory)
        shutil.copytree(HERE/"inputs", root/"inputs")
        shutil.copy2(HERE/"INPUTS.json", root/"INPUTS.json")
        verify_sources(root)
        target = root/"inputs/pr2260/owners/OWNERS.json.gz"
        target.write_bytes(target.read_bytes()+b"modified")
        try:
            verify_sources(root)
        except ValueError as error:
            require("frozen input changed" in str(error), "wrong source failure")
            controls.append("frozen-owner-bytes")
        else:
            raise ValueError("source corruption accepted")
        mutations = [
            ("source_manifest", lambda r: r.__setitem__("input_manifest_sha256", "0"*64)),
            ("inconclusive_as_accept", lambda r: r["cases"][1]["thresholds"][3].__setitem__("root_screen", "accept")),
            ("skipped_survivor_engines", lambda r: r["cases"][1]["thresholds"][1]["reject_gate"].__setitem__("full_engines",0)),
        ]
        for name, change in mutations:
            modified = copy.deepcopy(expected)
            change(modified)
            receipt = root/(name+".json")
            receipt.write_text(json.dumps(modified),encoding="utf-8")
            child = subprocess.run([sys.executable,"-I","-O","-B",str(HERE/"verify.py"),
                                    "--result",str(receipt)],capture_output=True,text=True,timeout=90)
            require(child.returncode != 0 and "result receipt mismatch" in child.stderr,
                    "wrong mutated receipt rejection: "+name+" "+child.stderr[-500:])
            controls.append(name)
    print("PASS_PENDING2260_SOURCE_RECEIPT_CONTROLS "+",".join(controls))


if __name__=="__main__":
    main()
