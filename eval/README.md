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
| Pending live run | - | - |

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
