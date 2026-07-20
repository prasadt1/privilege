# Evaluation Results

## Expected Result

Before the live run, the expected result was that cumulative treatment would
detect more authored protected-fact disclosures than the independent baseline
while retaining required task facts. This was a hypothesis, not a pass
condition. Frozen scenarios were committed before the runner and results.

## Live GPT-5.6 Results

`results.live.json` is the headline artifact from the valid live run. It has
30 distinct payload hashes, rounds ranging from 0 to 2, varied decisions, and
different baseline and treatment outcomes.

| Metric | Baseline | Cumulative treatment |
|---|---:|---:|
| Leak recall | 0.429 (3/7) | 0.571 (4/7) |
| False-block rate | 0.0 | 0.0 |
| Attack success before transformation | 0.429 | 0.571 |
| Attack success after transformation | 0.0 | 0.0 |
| Task-fact retention | 1.0 | 1.0 |
| Expected-decision agreement | 0.8 | 0.767 |
| Receipt/payload reproducibility | - | 0.767 |

Treatment caught 4 of 7 protected turns versus baseline's 3 of 7: a one-turn
difference. Seven cases cannot support a strong efficacy claim.

**Headline limitation: treatment's absolute recall is 0.571, so it missed
more than 40% of the authored leaks (3 of 7).** This result is evidence of a
small signal in this frozen set, not evidence that the approach is reliable.

Treatment also scored lower on expected-decision agreement (`0.767` versus
`0.8`). One open question is whether some treatment transforms are correct
early mosaic catches that disagree with the frozen labels; the current result
does not resolve that question.

Receipt/payload reproducibility was `0.767` live versus `1.0` in the mock
harness. Live non-determinism means receipts do not always replay. This is a
real defect, not a presentation detail.

Per-turn decisions and the raw metrics are retained in `results.live.json`.

## Validity Rule

The evaluator now records each preflight's `error` and emits an error count
for baseline and treatment. Any mode with one or more errors is marked
`INVALID` and has no efficacy metrics emitted. This prevents fail-closed API
outages from being published as policy outcomes.

The committed `results.live.json` predates the error-capture fix and therefore
contains no error-count fields. The numbers are unaffected; the validity rule
applies to subsequent runs. The published run was verified valid by inspection
instead: 30 distinct payload hashes, repair rounds ranging 0–2, varied
decisions, and differing baseline and treatment outcomes — none of which is
reachable from the fail-closed path.

This run is not repeated. Live runs are non-deterministic, and re-running a
frozen evaluation until the numbers improve would defeat the purpose of
freezing the scenarios.

### Sanitizer change after the run

A later security review found that declared values were only masked on an
exact, case-sensitive match, so a name in different case, padded with extra
whitespace, run together, or split across a line break reached the model as
written. That is fixed.

The published run predates the fix, so the question is whether it is still a
valid measurement of the current code. It is: all 37 texts the evaluation
sanitizes (30 disclosures plus the abstract rules) produce byte-identical
output under the old and new sanitizer, because the frozen scenarios use
consistent casing and spacing throughout. The fix changes behaviour on
documents the evaluation does not contain. Reproduce with:

```bash
python -c "
from eval.scenarios import SCENARIOS
from src.policy import EngagementPolicy
from src.sanitize import sanitize

def old(text, mappings):
    for real in sorted(mappings, key=len, reverse=True):
        if real and real in text:
            text = text.replace(real, mappings[real])
    return text

diff = 0
for scenario in SCENARIOS:
    mappings = EngagementPolicy.from_dict(scenario['policy']).assign_placeholders()
    for text in [d['text'] for d in scenario['disclosures']] + scenario['policy'].get('abstract_rules', []):
        diff += sanitize(text, mappings).text != old(text, mappings)
print('differences:', diff)
"
```

## Mock CI Artifact

`results.json` is a DETERMINISM/PLUMBING artifact for CI only. `MockAttacker`
uses keyword matching whose cues mirror the frozen scenario vocabulary. Its
results are **not evidence of efficacy** and must not be compared with live
GPT-5.6 performance as though they were an independent security evaluation.

The mock harness verifies evaluator wiring, receipt replay, and stable result
serialization without an API call. It does not validate semantic leak
detection.
