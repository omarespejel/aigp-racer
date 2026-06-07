# Reproducibility Policy

Every non-trivial PR must include exact local validation commands.

The baseline local gate is:

```bash
git diff --check
./scripts/aigp_local_gate.sh
```

## Deterministic Evidence

Generated evidence should use:

- sorted JSON keys;
- stable indentation;
- fixed float formatting;
- no wall-clock timestamps unless timestamps are the measured object;
- no host-specific paths unless explicitly labeled;
- stable schema versions.

If generated evidence should not drift, regenerate it and run:

```bash
git diff --exit-code docs/engineering/evidence/<artifact>.json
```

## Required Evidence For Claims

Frontier or claim-lane work must include:

- human-readable engineering note;
- machine-readable JSON;
- exact commands;
- environment details;
- source citations when external claims are involved;
- artifact digests when large or external files are referenced;
- non-claims.

## GitHub Actions Role

GitHub Actions are a safety net, not the normal research loop.

Do not use a green CI badge as evidence that:

- a policy is reliable;
- a simulator run is valid;
- a latency target holds;
- an external competition claim is current;
- a world-model method is useful.

