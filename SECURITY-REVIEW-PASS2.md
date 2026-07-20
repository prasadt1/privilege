# Privilege — security review pass 2 (fix verification)

**Date:** Mon 20 Jul 2026  
**Posture:** Assume each fix is wrong until demonstrated otherwise.  
**Constraints:** `eval/scenarios.py` frozen; eval not re-run; `--mock` only; `src/` not modified.

---

## Baseline

| Check | Result |
|---|---|
| Expected pytest count | 43 |
| **Actual** | **43 passed** in 0.59s |

### Test inversion honesty

Compared prior adversarial assertions to current `tests/test_adversarial_security.py`:

| Former buggy assertion | Current assertion | Honest upgrade? |
|---|---|---|
| Case/linebreak/concat **leak** (name remains) | `test_declared_values_are_masked_despite_case_and_spacing` — name must be gone | **Yes** — stronger confidentiality property |
| `"port"` mutates `"important"` | `test_short_protected_value_does_not_mutate_unrelated_words` — boundaries | **Yes** — stronger integrity property |
| Concurrent access **raises** errors | `assert not errors` and `len(entries) == 120` | **Yes** — stronger correctness + completeness |
| Abstract-rule unlisted nouns leak | **Unchanged** — still documents known accepted gap | **Yes** — not weakened/deleted |
| Web `survivingNames` lowercase miss | **Unchanged** — still documents UI gap | **Yes** — not weakened/deleted |

No evidence that failing tests were deleted or softened solely to go green.

---

## FIX 1 — Sanitizer (`src/sanitize.py`, `_value_pattern`)

### What holds

Against the original failure class, the fix **holds**:

- Case: `northwind freight` → masked  
- Line break: `Northwind\nFreight` → masked  
- Run-together: `NorthwindFreight` → masked  
- Extra spaces / many newlines between words → masked  
- Longest-wins with prefix still works  
- `"port"` no longer mutates `"important"` / `"report"`; standalone `port` still masks  
- Declared values with regex metacharacters (`Acme (EU)`, `foo.bar`, `a+b`, `x*y`, `end$`) are escaped and mask correctly  
- `\s*` does **not** bridge non-whitespace tokens (`Northwind secret Freight` stays unmerged)  
- Catastrophic-backtracking probe and a long multi-word value completed in milliseconds  

### What still breaks (residual bypasses)

These are **document-path** leaks of a *declared* value — worse than the accepted abstract-rules limitation, because the operator was told declared names are masked.

#### Medium — Unicode / invisible-character bypasses
**`src/sanitize.py:24-40`**

| Attack | Input idea | Result |
|---|---|---|
| Cyrillic lookalike | `Аcme Corp` (U+0410 + `cme`) | **Unmasked** |
| Fullwidth | `Ｎｏｒｔｈｗｉｎｄ　Ｆｒｅｉｇｈｔ` | **Unmasked** (NFKC form *would* mask) |
| Zero-width space | `Northwind\u200b Freight` | Prefix masks as short value; **`Freight` remains** |
| Zero-width joiner | `Northwind\u200dFreight` | Same class — short match / remainder leak |
| Combining diacritic | `Freigh\u0301t` | **Unmasked** two-word form |

**Failure scenario:** A PDF or pasted memo uses a lookalike or ZWSP inside a client name that appears on the protected list in ASCII. Local sanitize leaves a readable form in `final_payload` → OpenAI receives a real identity despite a declared mapping.

No UI “green safe” banner for this path; the “Sent to OpenAI” column would show the leak if inspected carefully. Still a false sense of safety if the operator trusts “I put it on the list.”

#### Low — Punctuation variants of multi-word names
If protected value is `Acme Corp` (space):

- `Acme-Corp` → `[B]-Corp` (only short alias/prefix path)  
- `Acme. Corp` → `[B]. Corp`  

If the declared value itself is `Acme-Corp`, hyphen form **does** mask. Not a regression vs old exact match (old also missed `Acme-Corp` when only `Acme Corp` was listed).

#### Low — `restore()` is not surface-faithful
**`src/sanitize.py:70-76`** still literal-replaces placeholders with the **canonical** mapping key.

Round-trip examples:

| Input | After sanitize → restore |
|---|---|
| `northwind freight leaving` | `Northwind Freight leaving` (casing normalized) |
| `Northwind\nFreight leaving` | `Northwind Freight leaving` (newline lost) |
| `NorthwindFreight leaving` | `Northwind Freight leaving` (space inserted) |

**Not an OpenAI leak** (outbound text stays placeholder). Local restored analysis can disagree with the source document. Integrity/UX, not the central outbound claim.

### Under-mask vs prior correct masks

Exact ASCII forms that previously masked still mask (including `(Northwind Freight)`). No ASCII regression found in that direction.

---

## FIX 2 — Concurrency (`src/store.py`, shared lock on `_read` / `_write`)

### What holds

- Re-ran the original stress shape (3 writers × 40, 3 readers × 40): **`concurrency_errors = 0`**, **`ledger_rows = 120`**.  
- `list_receipts` on 500 rows × 20 calls ≈ **0.009s** — not visibly slow for the local viewer.  
- Public methods take the lock sequentially (`get_engagement` then `_write`); they do **not** nest lock acquisition on the happy path.

### Residual notes (not current breaks)

- `threading.Lock` is **non-reentrant**. A same-thread nested acquire blocks (confirmed with timeout probe). Today’s call graph avoids nesting; a future refactor that calls `_read`/`_write` while already holding `_lock` would deadlock.  
- Single shared connection + one lock is sufficient to stop the prior `InterfaceError` / torn-row class under this stress. No torn read reproduced after the fix.

**Verdict: FIX 2 holds** against the original finding.

---

## FIX 3 — Upload cap (`src/server_http.py`, `MAX_REQUEST_BYTES`)

### What holds

- Claimed size `> 25 MB` is rejected before `read`.  
- Missing `Content-Length` → `read(0)` → JSON error (fail closed for parse, not a size bypass).  
- Undersized lying `Content-Length` → truncated JSON → error.  
- Standard `BaseHTTPRequestHandler` path does not usefully accept chunked request bodies here; missing CL does not stream unlimited JSON successfully.

### What breaks

#### Medium — Negative `Content-Length` bypasses the cap
**`src/server_http.py:94-101`**

```python
length = int(self.headers.get("Content-Length", "0"))
if length > MAX_REQUEST_BYTES:  # -1 > MAX is False
    raise ValueError(...)
return json.loads(self.rfile.read(length))  # read(-1) ⇒ read until EOF
```

**Failure scenario:** Client sends `Content-Length: -1` (or other negative) and an arbitrarily large body. Cap check does not fire; `read(-1)` consumes the entire stream. Demonstrated: negative CL successfully parsed a 1000+ character JSON body.

Memory is therefore **not** strictly bounded by `MAX_REQUEST_BYTES` under adversarial headers.

#### Low — Expansion within the cap remains
Even a *legal* ≤25 MB request is still base64 JSON → decoded bytes → temp file → extractor strings: multiple in-memory copies. Cap reduces blast radius; it does not make peak RSS ≈ wire size.

**Verdict: FIX 3 partially holds** (honest oversize CL blocked; **negative CL defeats it**).

---

## FIX 4 — Early block receipt (`src/service.py`, `_blocked_before_check`)

### What holds

When client construction raises `PreflightError`:

- `decision == "Block"`  
- `final_payload == ""` (cannot Allow / cannot send)  
- `receipt_id` is non-null for a known engagement  
- `export_receipt(receipt_id)` returns a real receipt with `decision: Block` and empty outbound payload  

**Verdict: FIX 4 holds.**

---

## Central claim (re-tested)

> Raw documents, real identities, aliases, mappings, and restored output never leave the device. OpenAI receives only sanitized text, abstract policy rules containing no real values, and prior sanitized payloads.

| Path | Pass-2 result |
|---|---|
| ASCII case / linebreak / concat declared names | **Held** (fixed) |
| Declared names with Unicode / ZWSP / fullwidth tricks | **Still falsifiable** (Medium) |
| Abstract rules with unlisted nouns | Known accepted gap — not re-litigated |
| Restored output to OpenAI | **Held** |
| Rewrite reinjection | **Held** (prior test still green) |
| Operator shown “safe” while real value transmitted | Still the **web heuristic / abstract-rules** class (accepted). **No new “safe banner + document leak” UI path found** beyond trusting the protected list against Unicode. |

Nothing found that is *worse than* the abstract-rules gap **and** pairs with an explicit green “safe” UI signal, except: **trusting declared-value masking against Unicode-obfuscated document text** (document path, not abstract rules).

---

## Eval integrity

`eval/README.md` claims all **37** sanitized texts (30 disclosures + abstract rules) are byte-identical under old exact `replace` vs current `sanitize`.

**Independent verification:** `compared: 37`, **`differences: 0`**.

Claim **holds**. Published live numbers still describe sanitizer behavior on this frozen corpus; the fix changes cases the eval does not contain.

---

## Summary scorecard

| Fix | Verdict |
|---|---|
| 1 Sanitizer (original ASCII/spacing class) | **Holds** |
| 1 Sanitizer (Unicode / ZWSP / fullwidth) | **Does not fully hold** — residual Medium bypasses |
| 2 Concurrency lock | **Holds** (0 errors; 120/120 rows) |
| 3 Upload byte cap | **Partial** — negative `Content-Length` bypass |
| 4 Early block receipt id | **Holds** |
| Eval byte-identity claim | **Holds** (0/37 diffs) |
| Test inversions | **Honest** |

### Ranked residual findings (pass 2 only)

1. **Medium** — `server_http.py:94-101`: negative `Content-Length` → unbounded `read(-1)`.  
2. **Medium** — `sanitize.py:24-40`: Unicode lookalikes / ZWSP / fullwidth / combining marks bypass declared-value masking.  
3. **Low** — `sanitize.py:70-76`: restore normalizes casing/spacing vs original surface form (local integrity only).  
4. **Low** — non-reentrant lock footgun if nested `_read`/`_write` is introduced later.

No `src/` changes made in this pass.
