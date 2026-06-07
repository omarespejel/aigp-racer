# AI Grand Prix Upstream Sync Policy

The official simulator and SDK are the contract.

## Source Priority

1. Official AI Grand Prix rules, FAQ, SDK, and technical specification.
2. Official simulator behavior observed through local probes.
3. Elodin harness behavior as practice context.
4. Papers and community writeups as design context.
5. Chat summaries as non-authoritative hints.

## Required Sync Notes

When official SDK or simulator behavior changes, record:

- source URL or local package name;
- version or date;
- observed interface change;
- affected code paths;
- updated validation commands;
- any stale docs or claims removed.

## Simulator-Only State Rule

Do not depend on state that the official competition interface does not expose.

If a practice harness exposes useful extra state, keep it behind test-only or harness-only code and label it clearly.

