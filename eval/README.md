# Evaluation Results

## Expected Result

Before running the live evaluation, the expected outcome was that cumulative
treatment would detect more authored protected-fact disclosures than the
independent baseline, while preserving required task facts. This is a
hypothesis, not a pass condition: false blocks, missed leaks, and treatment
underperformance must remain published if the live run produces them.

## Live GPT-5.6 Results

The headline results below are from `results.live.json`, generated with
`python3.11 eval/run.py --live`. They use the frozen scenarios in
`scenarios.py`; those labels were committed before the runner and results.

| Metric | Baseline | Cumulative treatment |
|---|---:|---:|
| Leak recall | 1.0 | 1.0 |
| False-block rate | 1.0 | 1.0 |
| Attack success before transformation | 1.0 | 1.0 |
| Attack success after transformation | 1.0 | 1.0 |
| Task-fact retention | 0.0 | 0.0 |
| Expected-decision agreement | 0.0 | 0.0 |
| Receipt/payload reproducibility | - | 1.0 |

This live run **underperformed the expected result**. Both baseline and
treatment blocked all 30 turns. That includes all 23 turns authored as benign,
which yields the reported `1.0` false-block rate. The treatment did not improve
on baseline leak recall, false-block rate, or task-fact retention; every
treatment turn also failed its authored expected decision. These numbers are
published unchanged. The artifact reports decisions and metrics, not a cause
for the blocks, so this README does not infer one.

Per-turn decisions, including failures and blocks, are retained verbatim in
`results.live.json`.

## Mock CI Artifact

`results.json` is a DETERMINISM/PLUMBING artifact for CI only. `MockAttacker`
uses keyword matching whose cues mirror the frozen scenario vocabulary. Its
results are **not evidence of efficacy** and must not be compared with live
GPT-5.6 performance as though they were an independent security evaluation.

The mock harness exists to verify evaluator wiring, receipt replay, and stable
result serialization without an API call. It does not validate semantic leak
detection.
