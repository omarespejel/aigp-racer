# Research Operating Notes

This folder defines how `aigp-racer` runs as a research lab.

The central rule is:

> Issues are hypotheses, not task buckets.

Each issue must be able to terminate. It should produce one of:

- `GO`: continue because evidence supports the next step.
- `NO_GO`: stop because the falsifying condition was met.
- `NARROW_CLAIM`: continue only with a smaller claim.
- `FOLLOWUP_ISSUE`: park a scoped follow-up outside the current PR.
- `KILL`: remove the direction from active planning.

## Lanes

- Default lane: conservative solver and official interface compatibility.
- Experimental lane: AutoRaceEvolve, learned policies, estimator variants, and speed experiments.
- Claim lane: paper/public/benchmark language only after evidence promotion.
- Hardening lane: runtime safety, artifact integrity, path safety, and compliance.

## Evidence Format

Prefer this shape:

```text
docs/engineering/<topic>-YYYY-MM-DD.md
docs/engineering/evidence/<topic>-YYYY-MM-DD.json
docs/engineering/evidence/<topic>-YYYY-MM-DD.tsv
```

Generated evidence must be deterministic unless the file explicitly documents why not.

