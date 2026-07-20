# Example policies

Starting points, not rules. Every engagement is different.

Use one with the CLI:

```bash
privilege --mock init-engagement --name "My review" --policy-file policies/restructuring.json
```

Or open the local UI, expand "Other names for the same thing, and raw policy",
and choose **Import policy**.

## Writing your own

Four fields matter.

**`protected_values`** are the names and terms that must never leave your
machine. They are replaced locally with `[VALUE_1]`, `[VALUE_2]`, and so on,
in the order you list them.

**`abstract_rules`** describe what must not become *inferable*. Write them in
plain English using real names. Any protected value inside a rule is replaced
with its placeholder before OpenAI sees it, so
`"Northwind Freight withdrawing from the Baltic corridor is protected"`
is transmitted as `"[VALUE_1] withdrawing from the [VALUE_2] is protected"`.

Anything in a rule that is **not** on the protected list is sent as written.
The local UI warns about capitalised terms that survive abstraction, which is
usually a name you meant to protect and forgot.

**`aliases`** map a short form to a protected value, so "Northwind" and
"Northwind Freight" share one placeholder. Each alias must point at a value in
`protected_values`.

**`allowed_purpose`** records why you are using AI on this engagement. It is
kept with the policy for your own audit trail.

## These files contain real names by design

A filled-in policy lists exactly what you consider confidential. Keep it beside
your vault, not in a shared repository. The examples here are synthetic.
