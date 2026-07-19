# Evaluation Results

## Expected Result

Before running the live evaluation, the expected outcome was that cumulative
treatment would detect more authored protected-fact disclosures than the
independent baseline, while preserving required task facts. This is a
hypothesis, not a pass condition: false blocks, missed leaks, and treatment
underperformance must remain published if the live run produces them.

## Live GPT-5.6 Results

> **This run is INVALID and is retained only as a record of a failed attempt.**
> It is not evidence about the approach, in either direction. See "Why this run
> is invalid" below. A valid live run is pending.

The run below used `eval/run.py --live` against the frozen scenarios in
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

### Why this run is invalid

No model call in this run ever succeeded. The evidence is unambiguous:

- All 30 turns returned `rounds: 0` — meaning failure occurred on the first
  call, before any inference was attempted.
- All 30 turns carry `payload_hash` = `e3b0c442...b855`, which is
  `sha256("")`. An empty payload is reachable only from the fail-closed
  exception handler in `src/preflight.py`, never from a completed preflight.
- Baseline and treatment are identical on every metric. The two modes differ
  only in whether prior disclosures are supplied to the attacker, so identical
  results mean neither mode reached the attacker at all.

Cause: the client defaulted to a model slug that the API does not serve, so
every request raised before inference. Fail-closed behaviour then converted
each failure into a `Block`.

**What this run does and does not show.** It does not show that cumulative
checking underperforms — the approach was never exercised. It does confirm one
designed property: under total remote failure, the system blocked all 30 turns
and emitted no payload. Nothing leaked when the model was unreachable.

A separate defect this exposed: `_turn_record` in `run.py` did not capture
`result.error`, so all 30 turns reported `error: None` and a complete outage
was serialized as a clean metrics table. An evaluator that cannot distinguish
a policy Block from an infrastructure failure is not trustworthy, and this is
being fixed before any valid run is published.

Per-turn decisions are retained verbatim in `results.live.json`.

## Mock CI Artifact

`results.json` is a DETERMINISM/PLUMBING artifact for CI only. `MockAttacker`
uses keyword matching whose cues mirror the frozen scenario vocabulary. Its
results are **not evidence of efficacy** and must not be compared with live
GPT-5.6 performance as though they were an independent security evaluation.

The mock harness exists to verify evaluator wiring, receipt replay, and stable
result serialization without an API call. It does not validate semantic leak
detection.
