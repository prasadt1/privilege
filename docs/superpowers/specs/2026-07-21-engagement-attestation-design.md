# Engagement persistence and document attestation

**Date:** 2026-07-21
**Status:** Approved

## Product boundary

Privilege does not determine whether a document truly belongs to an engagement.
The consultant is the source of truth for that association. Before any
preflight or export can run, the consultant must attest that:

1. the selected document belongs to the selected engagement; and
2. the engagement policy contains the names, aliases, and facts they expect
   Privilege to protect.

A wrong document may proceed after attestation. Results must therefore say
“Allow/Transform under this engagement policy,” not claim universal safety.
The attestation is stored locally and copied into export receipts.

## Engagement lifecycle

- Existing engagements are listed from the local SQLite vault and can be
  resumed without remembering an `eng_…` identifier.
- Policy JSON import/export remains a portability mechanism. Creating a new
  engagement from an imported policy does not restore disclosure history.
- The default vault remains `~/.privilege/vault.sqlite3`.
- Step 2 and later remain locked until an engagement is successfully created
  or resumed.

## New engagement validation

- Templates are structural: restructuring/market exit, sale/M&A, product
  launch under embargo, and blank.
- Templates do not silently seed fictional client identities.
- Client/project name, at least one protected value, and at least one
  inferability rule are required.
- The client/project name is automatically included as a protected value.
- “Why you are using AI” is labelled as an audit note, not an enforced rule.

## Document intake

After local extraction, Step 2 shows:

- the selected engagement;
- the uploaded filename;
- a reminder that Privilege applies only the selected policy; and
- an unchecked consultant-attestation box.

No semantic ownership classifier is added. The document may contain none of the
declared names: that is a legitimate context-only case and the reason for the
semantic attacker. Checking the box records the attestation and unlocks Step 3.

## Enforcement

- Attestation is stored in SQLite by `(engagement_id, document_id)`.
- `export_safe` fails before constructing the remote client when the document
  has no stored attestation.
- The HTTP UI cannot unlock Step 3 until the attestation endpoint succeeds.
- Receipts include `operator_attested: true`.

## Out of scope

- Proving document ownership or engagement membership
- Sending raw documents to a model to classify their client
- Cross-engagement entity detection
- Local NER for undeclared names
- Purpose-based task authorization
