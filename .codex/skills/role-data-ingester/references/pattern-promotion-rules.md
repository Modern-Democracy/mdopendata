# Pattern Promotion Rules

Use this reference before promoting observed municipal document patterns.

## Lifecycle

```text
observed -> candidate -> approved -> deprecated
```

## Promotion Criteria

Promote `observed` to `candidate` only when at least one is true:

- the same pattern appears across multiple source documents
- the pattern is structurally important for routing or extraction
- a reviewer explicitly marks it as candidate-worthy
- the pattern explains a repeated parser failure mode

Promote `candidate` to `approved` only when:

- required cues are documented
- positive examples are linked
- nearby negative examples or non-matches are considered where available
- expected routing or extraction behavior is specified
- accepted variation is explicit
- QA can test the pattern with discriminating evidence

Mark `deprecated` when:

- the pattern is replaced by a safer pattern
- cues were too broad or caused false positives
- the source template changed materially
- the pattern belongs to a source-specific exception rather than a reusable class

## Anti-Coercion Rules

- Do not approve a pattern from one page unless a reviewer explicitly scopes it as source-specific.
- Do not use a candidate pattern for automatic routing.
- Do not merge two patterns only because their normalized labels are similar.
- Do not discard raw labels when normalizing pattern names.
