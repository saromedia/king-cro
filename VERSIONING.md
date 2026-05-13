# Versioning & Release Policy

This document is the source of truth for how releases are cut, what versions
mean, and how clients should track upstream changes.

Audiences:
- **Maintainer** (the agency / consultant running king-cro for clients): read
  every section.
- **Client** (an end-user store owner whose repo was cloned from this template):
  read [The client contract](#the-client-contract) and
  [Upgrade workflow](#upgrade-workflow).

---

## Why this repo is versioned

king-cro is designed to be cloned/templated per client. Each client repo lives
in **their** GitHub org with **their** secrets and **their** Anthropic key (see
[GUARDRAILS.md](GUARDRAILS.md) for why that boundary matters).

That model is great for data isolation. It's bad for staying in sync — if the
maintainer ships a bugfix and 8 client repos are all on different commits of
`king`, "which version are you on?" becomes unanswerable.

Tags solve this. Every release is a tag. Clients pin to a tag. Upgrades are
deliberate, auditable, reversible.

---

## Version scheme

Semver, with the caveats below:

- **MAJOR** (`v1.0.0` → `v2.0.0`) — breaking changes. Any of:
  - Changes to required `.env` variables (new key required, key renamed)
  - Changes to required Shopify scopes
  - Changes to the structure of `knowledge/` files in a way that breaks
    auto-update (`history.md`, `experiments.md`, `insights.md`)
  - Changes to the public CLI surface of `scripts/run_agent.py` or
    `scripts/log_result.py` (flag renamed, removed, semantics changed)
  - Changes to the report contract in [CLAUDE.md](CLAUDE.md) that would break
    downstream parsing
- **MINOR** (`v0.1.0` → `v0.2.0`) — new features, additive. Examples:
  - A new scope (e.g. activating `mini-cart` checklist in
    [knowledge/playbook.md](knowledge/playbook.md))
  - A new experiment type in the taxonomy
  - A new optional `.env` variable with a safe default
  - A new optional CLI flag
- **PATCH** (`v0.1.0` → `v0.1.1`) — bugfixes, documentation, internal
  refactors. No client action required to take the upgrade.

While the repo is at `v0.x.y`, the API is **not stable** — minor versions can
include small breaking changes if necessary, with a note in the release
description. Once it ships `v1.0.0`, semver is strict.

---

## The client contract

If you are a client running this in your GitHub org:

1. **Pin to a release tag, not the `king` branch.** See
   [SETUP.md Step 14a](SETUP.md). Tags are stable; `king` is the moving
   integration branch and may be broken for short windows.
2. **Read the release notes before pulling a new tag.** The maintainer
   commits to documenting any required action (new `.env` var, new scope,
   knowledge-base migration) in the GitHub Release description.
3. **Test new tags in dry-run before promoting.** From a freshly merged tag:
   ```bash
   uv run python scripts/run_agent.py --weekly --dry-run --scope pdp
   ```
   If dry-run passes, the upgrade is safe to enable for the next scheduled
   weekly run.
4. **Don't edit `scripts/*.py` unless you intend to maintain a fork.**
   Customisation belongs in `knowledge/`, `.env`, and GitHub Secrets. Code
   edits make upstream merges painful.
5. **Keep `knowledge/history.md` archived periodically.** As history grows
   past ~50k tokens it starts eating into the per-run cost (see
   [COSTS.md](COSTS.md)). Archive the previous year to
   `knowledge/history-archive-YYYY.md` and prune.

---

## Upgrade workflow (client side)

See [SETUP.md — Step 14b](SETUP.md) for the full step-by-step. Short version:

```bash
# One-time: add the maintainer's repo as a second remote
git remote add upstream https://github.com/MAINTAINER/king-cro.git

# Each upgrade:
git fetch upstream --tags
git log --oneline v0.1.0..v0.2.0     # what changed
git checkout king
git merge v0.2.0                       # merge the tag, not the branch
git push origin king
```

If you have local code changes, expect merge conflicts in
`scripts/`. If you only have local *knowledge* changes, conflicts will be in
`knowledge/` and easy to resolve with `git checkout --ours`.

---

## Release workflow (maintainer side)

When cutting a new release on the canonical maintainer repo:

### 1. Prepare the release

- Confirm all PRs targeted at this version are merged into `king`.
- Run the full agent locally end-to-end against at least one real test store
  (or a clearly-flagged staging client) before tagging:
  ```bash
  uv run python scripts/run_agent.py --weekly --scope pdp
  ```
- Update [CHANGELOG.md](CHANGELOG.md) (create it on first release) with a
  section for the new version: highlights, breaking changes, required
  migration steps.

### 2. Decide the version bump

Match the scheme above. When in doubt, bump higher rather than lower — clients
prefer to know they're taking a MINOR over being surprised by a hidden break.

### 3. Tag and push

```bash
# From the maintainer repo, on king at the commit you want to release
git checkout king
git pull origin king
git tag -a v0.2.0 -m "v0.2.0 — short summary of headline change"
git push origin v0.2.0
```

### 4. Cut a GitHub Release

```bash
gh release create v0.2.0 \
  --title "v0.2.0 — short summary" \
  --notes-file release-notes-v0.2.0.md
```

Release notes must include:
- **Highlights** — 3–5 bullets, what's new in plain English
- **Breaking changes** — if any. List the required client action
- **Required client migration** — exact commands or file edits clients need
  to run on upgrade. Empty for pure PATCH/feature releases
- **Diff link** — `https://github.com/MAINTAINER/king-cro/compare/v0.1.0...v0.2.0`

### 5. Notify clients

For minor and major releases, post in your shared Slack channel / send the
client list an email pointing at the release notes. Patch releases can be
silent — clients see them via GitHub Watch notifications.

---

## Hotfix policy

If a critical bug is found in a released version:

1. Branch from the affected tag, not `king`:
   ```bash
   git checkout -b hotfix/v0.1.1 v0.1.0
   ```
2. Apply the minimal fix.
3. Tag `v0.1.1` from that branch and push.
4. Merge the hotfix branch back into `king`.
5. Cut a GitHub Release marked **🚨 Hotfix** with explicit upgrade urgency.

Clients on `v0.1.0` should be able to `git merge v0.1.1` cleanly without
taking any unrelated `king` changes.

---

## What "breaking" means in practice

The most common failure mode for clients on upgrade is silent: their reports
still generate, but something is subtly wrong. To prevent this, the
following are treated as breaking regardless of size:

- Anything that changes the **column structure** of
  [knowledge/experiments.md](knowledge/experiments.md) (e.g. inserting a new
  column). The agent's win-rate calculation depends on this layout.
- Anything that changes the **status labels** in
  [knowledge/hypotheses.md](knowledge/hypotheses.md) (`[ ]`, `[~]`, `[✓]`,
  `[✗]`) or in `experiments.md` (`suggested`, `active`, `winner`, `loser`,
  `inconclusive`).
- Anything that changes the **report section structure** defined in
  [CLAUDE.md](CLAUDE.md). If a client builds an internal dashboard parsing
  reports, that's their downstream contract.
- Anything that changes the **DD-MM-YYYY date format**. The whole knowledge
  base depends on this format for cross-file references.

If you have to break one of these, ship a migration script in
`scripts/migrations/` and call it out in red in the release notes.

---

## Current version

The latest released version is recorded by the most recent annotated tag:

```bash
git describe --tags --abbrev=0
```

The first tagged release is `v0.1.0` — see the corresponding GitHub Release
for what it included.
