# Requirements and Success Metrics

## Stakeholder
A business operations or administrative team that needs to review recurring documents faster.

## Problem
Manually reading business documents and copying key fields into another system takes time and can introduce transcription errors.

## Inputs
- Digital PDF or TXT documents in the starter version.
- Synthetic or public data only.

## Outputs
- Extracted text
- Candidate entities: organizations, dates, emails, amounts
- Short baseline summary
- Document-type label
- Schema-validated JSON
- Explicit human-review requirement

## Scope boundaries
- No automatic payments, approvals, or legal/financial decisions.
- No guarantee that extracted fields are correct.
- Scanned PDFs, multilingual documents, tables, and handwriting are outside the first version.

## Initial measurable targets (proposed, not yet achieved)
- 100% of valid sample outputs pass the JSON schema.
- 100% of invalid/empty inputs produce a clear error instead of crashing the UI.
- Measure field-level precision/recall on a manually labelled evaluation set; report actual results, not assumed results.
- Compare baseline and LLM-assisted extraction on the same held-out documents.

## Human review
A user must verify important facts against the source document. Missing or uncertain values should remain blank/unknown rather than being invented.
