# Integer-multiplication pricing: when does screening save time?

JIN HANZHE · Independent Researcher, Chongqing, China  
Release 1.0.0 · Research 2026-10-15 · Released 2026-10-22  
[中文](README.md) · [Reproduction](REPRODUCING.md) · [Detailed study](study/README.md)

This is a reproducible screening-and-fallback experiment on one complete reported pricing invoice. It applies Aaron Wang / navinor's quadratic bounds from PR #1669 to the fixed old PR #2260 invoice. A higher target from PR #2284 is used without substituting or rejecting PR #2284's improved construction.

At that higher target, the original Windows / CPython 3.12.10 measurements show about 15% paired end-to-end savings versus two complete exact evaluators. At the old accepted target and an inconclusive threshold, screening adds overhead. These are pricing-stage timings, not integer-multiplication runtimes or a new complexity bound.

The package retains all 581 historical fresh-process samples, 31,392 owner placements across 72 calls, exact rational receipts, fallback checks, and source notices. Historical timing percentages are recomputed from paired samples; they are never pass/fail conditions.

A separate 2026-10-22 rerun on Windows / CPython 3.12.14 produced 581 new process samples. At the same higher target, the direct reject gate saved a paired median 16.10%; accepted and inconclusive cases still added overhead. Both runs are preserved separately and audited by the default entry point. See [validation evidence](VALIDATION.md).

## Run offline

Python 3.12, standard library only:

```text
python reproduce.py
python reproduce.py --mode audit
python reproduce.py --mode benchmark
```

The default command validates integrity, recalculates historical timing summaries, replays exact results, and runs the existing negative controls. Audit mode skips arithmetic replay. Benchmark mode also generates 581 new timing samples in a fresh output directory. See [REPRODUCING.md](REPRODUCING.md). No Git, network, third-party library or GPU is required.

## Interpretation

The safe gate exits early only on a certified rejection; surviving and inconclusive cases run both exact engines. An accepted moment does not establish physical realization, precision, arbitrary-size compilation, or a complete multiplication theorem. A single invoice and a post hoc higher threshold do not estimate savings across a representative search.

The retained experiment uses Apache-2.0. Original source notices remain in the package; new release code and documentation use the same license. See [LICENSING.md](LICENSING.md), [NOTICE](NOTICE), and [CITATION.cff](CITATION.cff).

Author/contact: JIN HANZHE, jinhanzhe09@gmail.com. OpenAI Codex assisted this work and is not an author. Independent human verification and peer review are not claimed. Repository: [SHIN09-git/integer-mult-screening-audit](https://github.com/SHIN09-git/integer-mult-screening-audit). Release: [v1.0.0](https://github.com/SHIN09-git/integer-mult-screening-audit/releases/tag/v1.0.0).

