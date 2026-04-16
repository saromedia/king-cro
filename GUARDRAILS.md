# Agent Guardrails

This document defines what each agent in this system can and cannot do.
These rules are enforced architecturally — not just by instruction.

---

## CRO agent (the analysis agent)

**Can:**
- Read all files in this repository
- Call Shopify Admin API (read-only scopes only)
- Call Shopify GraphQL Analytics API (read-only)
- Call Anthropic API to synthesise reports
- Write files to `reports/`, `knowledge/history.md`, `knowledge/insights.md`,
  `knowledge/experiments.md`, and `dev-agent/handoffs/`
- Send Slack/email notifications

**Cannot:**
- Push or commit to any repository directly (the GitHub Actions workflow does this
  as a separate, explicit, auditable step — not the agent)
- Modify theme files
- Deploy anything
- Change Shopify settings
- Execute arbitrary shell commands

**How this is enforced:**
The CRO agent runs as a Python script (`run_agent.py`). It has no git credentials,
no write access to the theme repo, and no shell execution capability beyond what
the script explicitly calls. The GitHub Actions workflow commits report output files
only — this step is visible in `.github/workflows/weekly-scan.yml` and limited to:
`git add reports/ knowledge/history.md`

---

## Dev agent (the implementation agent)

**Can:**
- Read all files in this repository
- Read theme files (pulled fresh from Shopify CLI before the agent runs)
- Write and edit files within the working directory

**Cannot:**
- Run git commands — git is handled by explicit workflow steps, not the agent
- Create branches — handled by the workflow
- Open PRs — handled by the workflow via `gh pr create`
- Push to any branch — handled by the workflow
- Merge PRs — PRs require human review and approval
- Deploy theme changes — merging a PR does not auto-deploy; Shopify requires
  a separate manual publish step in the theme editor
- Modify any file outside the working directory

**How this is enforced:**
The dev agent runs with `--allowedTools "Read,Write,Edit"` only — no Bash access.
It cannot execute shell commands. All git operations in `implement-experiment.yml`
are explicit workflow YAML steps that you can read and audit. The PR requires
at least one human approval before merge (enforce this via GitHub branch protection).

---

## What "human in the loop" means in practice

| Action | Who does it |
|---|---|
| Suggesting experiments | CRO agent |
| Prioritising experiments | You |
| Writing handoff spec | CRO agent (on request) or you |
| Writing Liquid code | Dev agent |
| Reviewing code | You |
| Merging the PR | You |
| Publishing theme change | You (manual step in Shopify Admin) |
| Enabling the experiment toggle | You (in Shopify theme editor) |

Nothing in this system can affect your live store without a human making at least
two explicit decisions: merge the PR, then enable the setting in Shopify.

---

## Recommended GitHub branch protection rules

Go to your CRO agent repo (and theme repo) →
Settings → Branches → Add rule for `main`:

- [x] Require a pull request before merging
- [x] Require at least 1 approval
- [x] Dismiss stale pull request approvals when new commits are pushed
- [x] Do not allow bypassing the above settings

This means even if an agent somehow attempted a direct push to main, GitHub
would reject it at the API level.
