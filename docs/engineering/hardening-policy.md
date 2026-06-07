# Hardening Policy

Hardening work protects runtime safety, artifact integrity, and competition compliance.

## Runtime Risks

Prioritize:

- command-rate violations;
- stale telemetry;
- stale camera frames;
- timestamp mismatch;
- UDP frame reassembly corruption;
- NED/body/camera transform mistakes;
- recovery-state bugs;
- gate-loss behavior;
- hidden simulator-only dependencies;
- policy overfitting to deterministic canaries.

## Artifact Risks

Prioritize:

- model or policy hash drift;
- evaluator config drift;
- hidden holdout seed exposure;
- missing crash-regression fixtures;
- missing replay logs;
- generated evidence with host-specific paths;
- missing disclosure ledger updates.

## Compliance Risks

Prioritize:

- undisclosed FLOSS dependencies;
- undisclosed generated-AI use;
- undisclosed model weights;
- unverified competition rules;
- stale schedule or prize claims;
- external data license mismatch;
- accidental raw video/log publication.

## Required Tests

Add targeted negative or regression tests when touching:

- packet assembly;
- telemetry parsing;
- coordinate transforms;
- estimator sync;
- command-rate limiting;
- evaluator promotion rules;
- artifact path handling;
- disclosure or manifest logic.

