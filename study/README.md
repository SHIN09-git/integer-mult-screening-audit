# Quadratic screening on the complete PR2260 pricing invoice

**A measured pricing experiment on one pending supplier, with explicit fallback.**
This follows Aaron Wang / navinor's open handoff in [PR #1669](https://github.com/CrocSwap/integer-mult-bounds/pull/1669): bind one pending fully charged profile, compare the surrogate with complete moment evaluation, and measure the actual work.

The input is Dugongue's [PR #2260](https://github.com/CrocSwap/integer-mult-bounds/pull/2260) at `fde6b107e26a14da5bac5b66913c914708ea6901`. The surrogate is pinned to #1669 at `b910e86383b2270cf14b7b659a808fa0eb075c7d`. Both are retained unchanged. This package does not change the selected frontier, claim a new supplier, or replace its native/physical/all-size proof obligations.

This document was adapted for standalone distribution by JIN HANZHE on 2026-10-22.
The original research date is 2026-10-15; descriptions of pending work refer to that historical snapshot.
Only runnable paths and this notice were changed here. Use the [Chinese entry](../README.md),
[reproduction guide](../REPRODUCING.md), and [authorship disclosure](../AUTHORSHIP.md).
Mathematical results, measurement values and upstream attribution are retained.

## Exact finding

The full reported invoice is recounted from 31,392 literal helper placements in 72 calls, 436 helpers per call. The invoice has width 73, live stock 7,168, paid mass 520,704 and deficit 2,560. Its complete profile, including all local children and owner residuals, is:

| Rank | Count |
| --- | ---: |
| 1 | 176252 |
| 2 | 30096 |
| 3 | 30908 |
| 4 | 10152 |
| 5 | 4493 |
| 6 | 18 |
| 7 | 494 |
| 8 | 576 |
| 32 | 11 |
| 39 | 7 |
| 48 | 2493 |

The native and conservative variants both agree with the retained Mercator and atanh exact moment engines at all three fixed thresholds. The conservative variant includes the full inherited bad-residue surcharge as an exponential term. It contributes to D, E, F and L; it is not just a constant subtracted from the available saving.

| Threshold | Root screen | Both exact engines |
| --- | --- | --- |
| Selected kappa converted through the retained balanced relation | accept | accept |
| PR2260 advertised complex saving 0.0016834 | accept | accept |
| Advertised saving plus 0.00001 | reject | reject |
| Midpoint of the surrogate bracket, separately for each variant | inconclusive | reject |

“Accept” means only that this specified cost moment is strictly below one. It does not establish physical realization or a whole multiplication algorithm. “Reject” means that the same moment is strictly above one at that threshold. An inconclusive result supplies neither conclusion.

The approximate native root interval is [0.00168341128720775, 0.00168342369686303]; the conservative interval is [0.00168341128433076, 0.00168342369398597]. These decimals are rounded for reading only. [RESULT.json](RESULT.json) contains the exact rational endpoints and signs. Both complete engines additionally verify the signs at the two outer screening endpoints. This does not certify the exact 1e-24 root grid.

## Threshold screen and safe fallback

The inherited proof bounds a normalized moment by two quadratic expressions. For positive deficit D, logarithmic moment intervals E and F, and maximum logarithmic rate L,

```text
Q(a) = Elo*a + Flo*a^2/2
U(a) = Ehi*a + Fhi*a^2 / (2*(1-Lhi*a/3))
Q(a)-D <= M(a)-1 <= U(a)-D.
```

The domain checks require nonnegative a, positive D/E, and positive majorant denominator. The inherited screen bisects the two roots. For a single threshold, evaluating these same two expressions is sufficient:

- If Q(a)>D, the moment is strictly above one.
- If U(a)<D, the moment is strictly below one.
- Otherwise, the result is inconclusive, including equality.

This is a direct application of #1669's proved inequalities, not a new approximation theorem. The point variant removes the two 100-step root bisections; it retains the same certified log coefficients and domain checks. The pilot profile identified Fraction arithmetic, log preparation and bisection costs before this single adaptation was chosen.

The measured `reject_gate` policy returns early only for a certified rejection. Both exact engines still run for screen acceptance and inconclusive cases. It therefore preserves the original dual-engine arithmetic for candidates that survive this gate. A complete supplier verification remains necessary even when a cost gate accepts.

## Timing

The actual advertised PR2260 rate is accepted, so the safe gate still runs both exact engines. **No stable end-to-end speedup was found for that real threshold.** The deliberately raised-rate rejection control benefits; it is not a second real candidate or a demonstrated failed supplier.

The first run contains 350 fresh-process samples. Its overlapping end-to-end ranges motivated a separate 168-process follow-up: 21 adjacent A/B pairs for each conservative scenario, alternating which method ran first. The table reports the median of each paired difference/percentage, not a ratio of separately pooled medians.

| Conservative scenario | Gate minus complete dual-engine time, paired median | Paired time change | Gate faster |
| --- | ---: | ---: | ---: |
| Actual advertised rate, accepted | +8.92 ms | 1.90% slower | 7/21 pairs |
| Raised-rate rejection control | -60.85 ms | 14.41% faster | 21/21 pairs |
| Bracket midpoint, exact fallback required | +6.51 ms | 1.52% slower | 8/21 pairs |
| Four constructed thresholds in one batch | -24.25 ms | 4.47% faster | 18/21 pairs |

The batch is a deliberately fixed mixture of two accepts, one early rejection and one inconclusive fallback. It is **not** an estimate of a real search's candidate distribution.

On the actual conservative rate, first-run median arithmetic times were 15.50 ms for the unchanged root screen, 11.19 ms for the direct point screen, 11.92 ms for the existing atanh full evaluator and 74.72 ms for both complete engines. Thus the original screen is not faster than the existing fast evaluator in that arithmetic comparison; removing bisection only brings it close. Source reading and recounting alone took roughly 0.17–0.19 seconds, and total fresh-process runs roughly 0.35–0.44 seconds. Quoting the arithmetic ratio as whole-process acceleration would be misleading.

All raw samples, stage times and environments are in [TIMINGS.json](TIMINGS.json) and [PAIRED-TIMINGS.json](PAIRED-TIMINGS.json); exact harness/input/output hashes are in [BENCHMARK-PROVENANCE.json](BENCHMARK-PROVENANCE.json). No wall-clock value is a mathematical acceptance condition.

Five paths are compared: the unchanged root screen, direct threshold screen, the faster atanh complete engine alone, both complete engines, and rejection gate plus both engines when needed. Each cold sample starts a fresh Python process, verifies all frozen hashes, reads the same sources, recounts every owner placement, imports the same three engines, and performs one threshold decision. The four-threshold batch prepares that same invoice once and reuses its pure logarithm cache and, for screens, its coefficient/bracket result. The original exact caller's pure atanh-log cache wrapper is preserved.

The process launch, imports, source hashing, JSON/decompression, recount and arithmetic are separately recorded. The operating-system file cache is not flushed. Seven repetitions use deterministic shuffled execution order and sequential workers; medians, ranges, interquartile ranges and raw samples are retained. Timing includes neither native circuit reconstruction nor complete physical/precision proof replay. Results describe this machine and fixture, not a general speedup.

## Published competitive target

The final overlap review identified a real higher target in Dugongue's [PR #2284](https://github.com/CrocSwap/integer-mult-bounds/pull/2284), pinned at `e71574b92f6af546013c71293cd03ff58742a1e6`: complex saving **84179/50000000 = 0.00168358**. This follow-up was chosen after the initial four-threshold measurement; those original results, including the unfavorable actual-rate comparison, remain unchanged.

Both native and conservative versions of the **old PR2260 invoice** are strictly rejected at that published higher target by the unchanged root screen, the direct point screen, and both full exact engines. The original PR2260 rate remains accepted. The PR2284 receipt has a different improved profile; that new profile is not substituted, audited or rejected here. This corroborates a rejection already stated by PR2284, with the new evidence being the source-bound surrogate application and its measured work.

A separate conservative-target run used 21 adjacent fresh-process triplets, rotating and reversing the order of full dual-engine evaluation, unchanged root screening, and the direct rejection gate. Each path charges the same source checks, target-source checks, full old-invoice recount and imports.

| Method at published higher target | Arithmetic median | Whole-process median | Median paired time saving | Faster than full dual |
| --- | ---: | ---: | ---: | ---: |
| Both complete exact engines | 61.21 ms | 339.42 ms | reference | — |
| Unchanged PR1669 root screen | 12.32 ms | 288.20 ms | 15.09% | 21/21 |
| Direct point rejection gate | 9.19 ms | 286.78 ms | 14.97% | 21/21 |

The two screening methods have similar whole-process timings here. The smaller arithmetic cost of direct evaluation does not establish an additional whole-process advantage over the original screen. Different runs have different load/cache conditions; use the adjacent comparisons, not cross-run ratios.

[COMPETITIVE-RESULT.json](COMPETITIVE-RESULT.json) contains the exact positive residual bounds, [COMPETITIVE-TIMINGS.json](COMPETITIVE-TIMINGS.json) all 63 samples, and [COMPETITIVE-SOURCE.json](COMPETITIVE-SOURCE.json) the exact target-source pins. This resolves #1669's bounded timing question for one invoice at a real competitive target. It does not estimate savings across a real candidate search or change either PR's supplier-admission status.


## Reproduce

CPython 3.12, standard library only. The original comparison has 18 frozen input files; the competitive follow-up separately pins its target receipt and notice. All are package-local; no network, Git or GPU is needed for direct replay.

```sh
python -I -B study/verify.py
python -I -B study/competitive_target.py
python reproduce.py
python -I -B study/benchmark.py --repetitions 7 --output timings-local.json
python -I -B study/paired_benchmark.py --pairs 21 --output paired-timings-local.json
python -I -B study/competitive_target.py --benchmark --trials 21 --output competitive-timings-local.json
```

The default verifier is read-only. `--write` explicitly regenerates the exact RESULT. The benchmark writes only the requested timing output. Timings are deliberately excluded from the deterministic receipt equality check.

The main replay checks eight threshold/model combinations, 17 new semantic controls and the 12 inherited #1669 controls; the competitive follow-up adds two threshold/model comparisons. The separate source/receipt test rejects four corruptions. Actual engine callbacks are observed to confirm fallback coverage. Controls include omitted owners, width/copy/time/capacity errors, missing local and idle costs, incorrect stock, source/receipt drift, changed counts under a warm logarithm cache, changed width, strict threshold boundaries and invalid surrogate domains. It reruns the complete original PR2260 arithmetic script and requires exact equality with its published receipt, including all 47 outer inequalities and its original rejection controls.

## Scope and overlap

This is a refined `replay-runtime` task, chosen with nonce `311009a0157e09d3b53abfc65e19720f` from canonical main `0fdd7d82de03e43c9e5a1000dfbcd380d1b687d2`, priority revision 4. No selected-root recalculation or P104 composition is proposed.

The entry refresh covered 551 open PRs, 1,063 Discussion body/comment/reply records, and 1,536 local README/TASK/ledger records. The final refresh covered 564 open PRs, 1,078 remote records and 1,538 local records; it identified PR2284's published higher-rate comparison used above. Pagination was complete. Specific all-state PR searches supplement that snapshot. These are metadata/body searches and targeted source reads, not every diff or a novelty guarantee. #2311 addresses PR2260's supplier-admission premises; #1939 optimizes another selected replay stage. Neither supplies this screening/timing comparison. [TASK.json](TASK.json) records dates, source heads and the initial sparse-checkout baseline limitation.

The new recount verifies the source-bound arithmetic profile and the stated owner packing constraints. Native identities, physical charts/controller, precision/tape and all-size/analytic/bit assumptions are inherited. The finite-invoice file is retained and its stock sum cross-checked; its full physical derivation is not repeated. The reported conditional kappa belongs to PR2260, not to this experiment.

## Open next questions

Can the rejection gate reduce total pricing work on a fixed, representative collection of distinct candidate invoices? Freeze the candidate collection before timing, record its rejection and ambiguity rates, then charge the gate and every fallback. The result for a single deliberately too-large threshold is insufficient to predict search-wide savings.

Is a smaller log precision sufficient for exactly the same conservative threshold decisions? First derive outward error requirements from a declared decision margin; retain the present exact fallback. Reducing series length merely because this fixture passes would weaken the contract.

## Credit

Aaron Wang / navinor, with help from chatgpt, supplies the quadratic theorem, exact screen and its controls in #1669. Dugongue and the disclosed OpenAI Codex collaborators supply PR2260's selective-borrowing construction and complete arithmetic package. Cinna Davis / 1337isnot1337's #2226 supplies its preceding borrowing architecture. The frozen notices retain PR1005's owner-plan lineage, the selected bit source, the exact moment engines and outer-assembly lineage, including eumemic, icekylinx, Zhihao Chen and hipotures/RaD.

SHIN09-git's source-bound experiment, point application, controls, timing harness and writing used substantial OpenAI Codex assistance. No independent human, second-agent or proof-assistant review was performed in this round. Apache-2.0; frozen sources and their retained notices remain unchanged.
