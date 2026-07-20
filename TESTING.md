# Manual test pass

Run through this before recording or submitting. It covers the CLI, the local
viewer, file intake, the policy form, and the failure paths that matter for a
tool whose whole claim is that raw data stays local.

Two modes throughout:

- `--mock` needs no API key and never calls OpenAI. The mock client infers
  nothing, so **every decision will be Allow**. Use it to test plumbing.
- `--live` calls GPT-5.6 and costs a few cents. Use it to test detection.

Setup once:

```bash
cd ~/OpenAI-hackathon
python3.13 -m venv .venv
.venv/bin/pip install -e ".[dev,files]"
.venv/bin/python -m pytest -q          # expect: 28 passed
```

---

## 1. Automated suite

```bash
.venv/bin/python -m pytest -q
```

**Expect:** `28 passed`. Any failure stops the pass.

---

## 2. CLI, offline

```bash
DB=/tmp/t1.sqlite3; rm -f $DB

.venv/bin/privilege --mock --db $DB init-engagement \
  --name "manual test" --policy-file policies/restructuring.json
# -> {"engagement_id": "eng_..."}

EID=<paste the id>

printf 'Northwind Freight operates 14 depots in the Baltic corridor.' > /tmp/note.txt
.venv/bin/privilege --mock --db $DB import --engagement $EID --file /tmp/note.txt
# -> {"document_id": "doc_..."}

DID=<paste the id>

.venv/bin/privilege --mock --db $DB preflight --engagement $EID --document $DID \
  --task "Summarize the depot costs."
```

**Expect:** decision `Allow`, and in `final_payload` the real names are gone,
replaced by `[VALUE_1]` and `[VALUE_2]`. This is the core claim. If a real name
appears in `final_payload`, stop and investigate.

```bash
.venv/bin/privilege --mock --db $DB status --engagement $EID
```

**Expect:** `abstract_rules` contains placeholders only, never
"Northwind Freight". `receipts` has one entry.

---

## 3. Receipts exist for every decision

```bash
.venv/bin/privilege --mock --db $DB status --engagement $EID \
  | python3 -c "import json,sys; print(len(json.load(sys.stdin)['receipts']))"
```

**Expect:** a count that grows by one per `preflight`, and by two per
`analyze`. A decision with no receipt is a bug: the audit trail is the product.

---

## 4. File intake

```bash
# Word
.venv/bin/python -c "
import docx; d=docx.Document(); d.add_paragraph('Northwind Freight depot review.')
t=d.add_table(rows=1, cols=2); t.rows[0].cells[0].text='Corridor'; t.rows[0].cells[1].text='Baltic'
d.save('/tmp/brief.docx')"
.venv/bin/privilege --mock --db $DB import --engagement $EID --file /tmp/brief.docx
```

**Expect:** succeeds. Table contents are extracted, not skipped.

```bash
# Unsupported, on purpose
printf 'x' > /tmp/model.xlsx
.venv/bin/privilege --mock --db $DB import --engagement $EID --file /tmp/model.xlsx
```

**Expect:** `error: .xlsx is not supported yet: spreadsheets need per-sheet and
per-cell policy handling` on stderr, exit code 2, no traceback. Same for
`.pptx` and `.png`. An unknown type like `.zip` should say "no local
extractor".

```bash
# Missing file
.venv/bin/privilege --mock --db $DB import --engagement $EID --file /tmp/nope.txt
```

**Expect:** "not a file", cleanly.

---

## 5. Local viewer

```bash
.venv/bin/python -m src.server_http --db /tmp/t2.sqlite3
# open http://127.0.0.1:7077
```

Without an API key, add `PRIVILEGE_MOCK=1` before the command.

**Policy form**

- Switch the "Start from" dropdown across all four templates. Fields repopulate
  each time; "Blank policy" clears them.
- The preview under "What OpenAI would receive as policy" shows placeholders,
  never real names.
- Type a rule mentioning a name **not** in the confidential list, for example
  `The Meridian Capital bid is protected`. **Expect:** the preview turns red and
  warns "These would be sent as written: Meridian Capital".
- Remove it. **Expect:** warning clears.
- Expand "Other names for the same thing, and raw policy". The JSON matches the
  form. Click **Download policy**, then **Import policy** with
  `policies/sale-process.json`. **Expect:** fields repopulate.

**Flow**

- **Create engagement** -> id appears top right.
- Upload `/tmp/brief.docx` via the file picker. **Expect:** extracted text
  appears in the document box and in the "Stays local" column, and the notice
  reports a character count. Nothing has been sent yet.
- **Import locally**, then **Check only**. **Expect:** the "Sent to OpenAI"
  column shows placeholders, never real names. Compare the two columns
  side by side; this is the money shot for the video.
- **Check, then send**. **Expect:** "Restored locally" shows real names back,
  the ledger counter increments, a receipt appears.
- Expand a receipt. **Expect:** the inferences GPT-5.6 actually returned.

**Load existing**

```bash
.venv/bin/python -c "
import sqlite3; print(list(sqlite3.connect('demo/demo-vault.sqlite3').execute('select id from engagements'))[0][0])"
```

Paste that id into "eng_... from a saved vault", click **Load existing**.
**Expect:** eight receipts from the committed live run, including one
`Transform` with one repair round.

---

## 6. The mosaic arc, live

This is the demo. Needs `OPENAI_API_KEY`.

```bash
.venv/bin/python demo/seed.py --live --db /tmp/arc.sqlite3
```

**Expect:** turns 1 to 3 `ALLOW` with prior disclosures climbing 0, 1, 2, then
turn 4 `TRANSFORM` at 3 prior disclosures with at least one repair round.

Live models vary. If turn 4 comes back `ALLOW`, that is a real result, not a
bug: recall in the frozen eval is 0.571, so misses are expected. Re-run to see
the variance rather than assuming something broke.

---

## 7. Failure paths

```bash
# Local commands must not need a key at all
env -u OPENAI_API_KEY -u PRIVILEGE_MOCK .venv/bin/privilege --db $DB \
  status --engagement $EID
```

**Expect:** works. Creating an engagement, importing, and reading status are
entirely local, so they never construct a remote client.

```bash
# No API key, live mode
env -u OPENAI_API_KEY .venv/bin/privilege --live --db $DB preflight \
  --engagement $EID --document $DID --task "Summarize."
```

**Expect:** `error: OpenAI client is unavailable` on stderr and exit code 2.
Nothing is sent. A stack trace here is a bug.

```bash
# Unknown ids
.venv/bin/privilege --mock --db $DB preflight --engagement eng_nope \
  --document doc_nope --task "x"
```

**Expect:** decision `Block` with `"error": "UnknownEngagementError"`. The
preflight loop fails closed rather than raising, because a failure to check
must never become a send.

---

## 8. Nothing confidential is committed

```bash
git ls-files | grep -iE "\.env|api|key|secret|session" || echo "clean"
git ls-files '*.sqlite3'
```

**Expect:** only `demo/demo-vault.sqlite3`, which holds synthetic data. Your
real vault lives at `~/.privilege/vault.sqlite3`, outside the repo.

```bash
.venv/bin/python -c "
import sqlite3
for row in sqlite3.connect('demo/demo-vault.sqlite3').execute('select raw_text from documents'):
    print(row[0][:120])"
```

**Expect:** the invented Northwind scenario, nothing real.
