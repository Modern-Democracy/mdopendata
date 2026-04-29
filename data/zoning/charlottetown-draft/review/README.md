# Charlottetown Section-Equivalence Review Ledger

This directory stores diffable review decisions for current-versus-draft Charlottetown section-equivalence work.

`section-equivalence-review.csv` is the audit ledger for manual decisions applied to `zoning.section_equivalence`. Database review updates should be represented here so they can be reviewed in Git before or alongside database changes.

The initial ledger backfills 35 accepted `same_topic` decisions from the database. These decisions used the review batch `2026-04-29-exact-title-same-topic-text-ge-0.75`, meaning exact title match, generated `same_topic` equivalence type, and text similarity at or above `0.75`.

The second ledger batch, `2026-04-29-remaining-same-topic-ledger-review`, records accepted review decisions for the remaining 41 generated `same_topic` candidates before database updates. Rows in this batch intentionally retain `db_review_status` as `candidate` until an apply step updates `zoning.section_equivalence`.

The third ledger batch, `2026-04-29-renamed-or-restructured-ledger-review`, records manual decisions for all 26 generated `renamed_or_restructured` candidates before database updates: 10 accepted, 7 rejected, and 9 marked `needs_review`.
