# Repository Instructions

This repository is an autonomous drone-racing research lab for AI Grand Prix.

It is not run like a normal feature repo. Every non-trivial change must answer:

> Did this strengthen, falsify, or narrow the racing thesis?

The working thesis is that we can build a low-latency autonomous racing stack where
the live runtime is small and deterministic, while WorldForge and AutoRaceEvolve
operate offline as the evidence, replay, optimization, and regression lab.

## Core Boundaries

- Treat live flight code as safety- and correctness-critical runtime code.
- Keep the flight runtime small, deterministic, and low-latency.
- Do not put LLMs, large video models, learned world-model rollouts, DecisionTrace generation, or WorldForge evaluation in the live control path.
- Treat WorldForge as offline replay, evaluation, DecisionTrace, regression, and AutoRaceEvolve infrastructure.
- Preserve competition compliance evidence from day one: FLOSS dependencies, generated-AI usage, model weights, data sources, simulator sources, and license notes.
- Prefer reproducible artifacts over claims: every promoted controller or policy needs logs, metrics, hashes, evaluator configuration, and a regression result.
- Before changing architecture, update the relevant issue or handoff doc under `docs/` or `.codex/`.

## Four Research Lanes

1. **Default lane**
   - Conservative baseline behavior.
   - Official AI Grand Prix interface compatibility.
   - No experimental claim promotion.
   - Round-1 valid-run baseline, packet parsing, schemas, reproducibility, CI, and docs.

2. **Experimental lane**
   - Frontier work such as AutoRaceEvolve, learned CTBR policies, estimator variants, racing-line search, Elodin-vs-official simulator comparisons, and aggressive speed schedules.
   - Must be labeled experimental.
   - Cannot silently become default behavior.

3. **Claim lane**
   - Any statement intended for paper, blog, public docs, sponsor update, benchmark table, or competition positioning.
   - Results may be promoted only after checked evidence, exact commands, source citations, non-claims, and artifact discipline.

4. **Hardening lane**
   - Runtime safety, command-rate limits, MAVLink behavior, UDP reassembly integrity, timestamp freshness, path safety, artifact integrity, disclosure, model/data provenance, and regression resistance.

## Trusted-Core Paths

Changes under these paths require stronger validation and review discipline:

- `solver/**`
- `mavlink/**`
- `vision/**`
- `perception/**`
- `estimation/**`
- `planning/**`
- `policies/**`
- `evolve/**`
- `worldforge_bridge/**`
- `scripts/**`
- `tests/**`
- `.github/workflows/**`
- `.github/ISSUE_TEMPLATE/**`
- `.github/instructions/**`
- `.coderabbit.yaml`
- `.pr_agent.toml`
- `docs/engineering/**`
- `docs/security/**`
- `DISCLOSURE_LEDGER.md`

## Forbidden Claims Without Evidence

Do not claim:

- we can win AI Grand Prix;
- a speedup;
- a reliability rate;
- a latency bound;
- physical-drone transfer;
- simulator-to-real transfer;
- state-of-the-art performance;
- production readiness;
- official SDK compatibility;
- correct velocity telemetry handling;
- safe learned policy behavior;
- validated world-model advantage;
- AGIBOT or Go2 benchmark superiority;
- WorldForge is part of the live flight runtime.

Allowed language for early work:

> This is an experimental AI Grand Prix autonomy lab. The early objective is to build a reproducible low-latency racing stack, identify where failures occur, and promote only measured claims with exact artifacts and non-claims.

## Issue Discipline

Issues are hypotheses, not task buckets.

Every research or hardening issue must include:

- thesis or observed risk;
- why it matters;
- smallest falsifying experiment or smallest fix;
- GO gate;
- NO-GO gate;
- required artifacts;
- non-claims;
- exact local validation commands.

Allowed outcomes:

- `GO`
- `NO_GO`
- `NARROW_CLAIM`
- `FOLLOWUP_ISSUE`
- `KILL`

Failed experiments are useful. Do not rewrite a `NO_GO` as progress.

## Validation Discipline

Local first. GitHub Actions are not the normal research loop.

Start with the narrowest relevant local commands:

```bash
git diff --check
./scripts/aigp_local_gate.sh
```

Add targeted checks for the touched surface:

- UDP frame reassembly tests for `vision/**`.
- PnP geometry tests for `perception/**`.
- telemetry parsing and timestamp-sync tests for `mavlink/**` and `estimation/**`.
- command-rate and stale-data tests for `solver/**`.
- evaluator immutability and hidden-seed checks for `evolve/**`.
- artifact no-drift checks for evidence under `docs/engineering/evidence/**`.

## Bot Review Policy

Qodo and CodeRabbit are cheap adversarial reviewers, not authorities.

Classify every bot finding:

- `must_fix`: real runtime, safety, correctness, artifact, path-safety, compliance, or test-gap issue.
- `evidence_needed`: plausible finding; reproduce locally before accepting or rejecting.
- `stale_or_false_positive`: reply with evidence; do not churn code.
- `followup_issue`: valid but outside scope; open an issue with GO/NO-GO framing.
- `ignore`: style-only with no correctness, safety, compliance, or research impact.

Do not merge with unresolved `must_fix` or `evidence_needed` findings.

## Merge Discipline

- Start from a clean worktree off `origin/main`.
- Use one branch per PR.
- Keep PRs tightly scoped.
- Use normal PRs, not drafts, when bot review is expected.
- Do not merge while Qodo, CodeRabbit, or human review threads are actionable.
- Wait 5 minutes after latest reviewer activity before merging.
- Use rebase merge.
- No merge commits.
- No auto-merge until the repo has stable CI and review behavior.
- Record exact local validation commands in the PR body.

Normal merge:

```bash
gh pr merge <PR> --rebase --delete-branch
```

If the GitHub CLI merge path is blocked by local multi-worktree state, use the API with an exact head SHA:

```bash
gh api -X PUT repos/OWNER/REPO/pulls/PR_NUMBER/merge \
  -f merge_method=rebase \
  -f sha=EXACT_HEAD_SHA
```

## Evidence Rules

Any frontier or claim-lane result needs checked-in evidence:

- human note in `docs/engineering/`;
- machine-readable JSON under `docs/engineering/evidence/`;
- TSV/CSV when useful;
- exact reproduction commands;
- artifact digests for large or external files;
- mutation, negative, or no-drift gates when applicable;
- explicit non-claims.

Evidence generation should be deterministic:

- sorted JSON keys;
- fixed float formatting;
- no wall-clock timestamps in generated JSON unless the timestamp is the measured object;
- no host-specific paths unless explicitly labeled;
- `git diff --exit-code` after regeneration when the artifact should be stable.

