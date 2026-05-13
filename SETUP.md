# Setup — Step by Step

This file is written for an AI agent (or a human) to walk through end-to-end when
setting up this repo for the first time. Each step has:

- **Do** — the exact action
- **Why** — what it unlocks
- **Verify** — how to confirm it worked before moving on

Do not skip a step. If `Verify` fails, fix that step before continuing.

If you are an agent reading this for a user: announce the current step, do it (or
tell the user to do it if it requires their hands on a browser), confirm the
verification passes, then move to the next step.

---

## Prerequisites checklist

You will need accounts and access to:

- [ ] A Shopify store you own (or have collaborator + dev access to)
- [ ] An Anthropic API account → https://console.anthropic.com
- [ ] Python 3.11+ available on this machine
- [ ] `uv` installed (Python package manager) — installed in Step 1
- [ ] Shopify CLI installed — needed for Step 4 (theme pull)
- [ ] A GitHub account (only if you want the weekly auto-run and dev agent)
- [ ] A Slack workspace where you can add an Incoming Webhook (optional)

If any item above is missing, pause and resolve it before starting.

---

## Step 1 — Install `uv` and project dependencies

**Do:**

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# From the repo root, install dependencies
uv sync
```

**Why:** `uv` manages the Python environment. `uv sync` installs everything
listed in `pyproject.toml` into an isolated `.venv`.

**Verify:**

```bash
uv run python -c "import anthropic, requests; print('ok')"
```

You should see `ok`. If you see an import error, re-run `uv sync`.

---

## Step 2 — Create your local `.env`

**Do:**

```bash
cp .env.example .env
```

Open `.env` in your editor. Do not commit this file — it is git-ignored.

**Why:** The agent reads credentials from `.env` at runtime. `.env.example`
contains inline comments explaining each variable.

**Verify:**

```bash
ls -la .env && grep -c "^[A-Z_]" .env
```

The file should exist and contain at least a dozen variable lines. You will fill
in the actual values in the next steps.

---

## Step 3 — Create the Shopify custom app and get an Admin API token

This step is done in the Shopify Admin browser UI, not the terminal.

**Do:**

1. Shopify Admin → Settings → Apps and sales channels → Develop apps
2. If "Develop apps" is not visible, click **Allow custom app development** first
3. Click **Create an app** → name it `CRO Agent` (or anything you like)
4. Click **Configure Admin API scopes**
5. Tick **only** these scopes — nothing else:

   | Scope | Why |
   |---|---|
   | `read_orders` | AOV, revenue, refund rate, repeat customers |
   | `read_checkouts` | Abandoned checkout count |
   | `read_products` | Flag thin descriptions, missing images, OOS variants |
   | `read_customers` | Repeat-customer retention metrics |
   | `read_analytics` | Sessions + CVR via GraphQL (core metrics) |
   | `read_themes` | Only if you want GitHub Actions to auto-pull theme files |

6. Click **Install app** → reveal and copy the **Admin API access token**
   (it starts with `shpat_`). You can only view this once — paste it into `.env`
   immediately as `SHOPIFY_ACCESS_TOKEN`.
7. In `.env` also fill in `SHOPIFY_SHOP_URL` (e.g. `your-store.myshopify.com`).

**Do not** tick any scope that starts with `write_`. The agent is strictly
read-only — granting write scopes adds risk for zero benefit. See
[GUARDRAILS.md](GUARDRAILS.md) for the architectural enforcement.

**Verify:**

```bash
uv run python -c "
import os
from dotenv import load_dotenv
load_dotenv()
url = os.getenv('SHOPIFY_SHOP_URL')
tok = os.getenv('SHOPIFY_ACCESS_TOKEN','')
assert url and url.endswith('.myshopify.com'), 'SHOPIFY_SHOP_URL missing or wrong format'
assert tok.startswith('shpat_'), 'SHOPIFY_ACCESS_TOKEN missing or wrong format'
print('shopify credentials look ok')
"
```

---

## Step 4 — Pull your Shopify theme locally

**Do:**

Install Shopify CLI if needed (https://shopify.dev/docs/themes/tools/cli/install),
then from anywhere on your machine:

```bash
shopify theme pull --store your-store.myshopify.com --path ./theme
```

This is safe — `theme pull` only downloads files. It does not upload or modify
your live theme.

Then set `THEME_DIR` in `.env` to the absolute path of that `./theme` directory.

**Why:** The agent reads `.liquid` files directly off disk to find CRO issues
with file:line citations. It never edits them.

**Verify:**

```bash
uv run python -c "
import os
from dotenv import load_dotenv
load_dotenv()
d = os.getenv('THEME_DIR')
assert d and os.path.isdir(d), f'THEME_DIR not set or not a directory: {d}'
import glob
liquids = glob.glob(os.path.join(d, '**', '*.liquid'), recursive=True)
assert liquids, 'No .liquid files found under THEME_DIR'
print(f'theme ok — {len(liquids)} liquid files found')
"
```

---

## Step 5 — Add your Anthropic API key

**Do:**

1. https://console.anthropic.com → Settings → API Keys → Create Key
2. Paste into `.env` as `ANTHROPIC_API_KEY=sk-ant-...`

**Why:** The agent calls Claude to synthesise the final report from raw findings.

**Verify:**

```bash
uv run python -c "
import os
from dotenv import load_dotenv
load_dotenv()
k = os.getenv('ANTHROPIC_API_KEY','')
assert k.startswith('sk-ant-'), 'ANTHROPIC_API_KEY missing or wrong format'
print('anthropic key format ok')
"
```

---

## Step 6 — Populate the brand context

**Do:**

Open [knowledge/brand.md](knowledge/brand.md) and fill in every section. Treat
the placeholder values as TODOs — replace them with real values for your store.

Sections to complete: business overview, target customer, product range,
competitive landscape, known friction points, prior experiment learnings.

**Why:** Every run reads this file first. If it still contains placeholders, the
agent will flag it and refuse to produce industry-specific recommendations.

**Verify:**

```bash
uv run python -c "
import re, pathlib
text = pathlib.Path('knowledge/brand.md').read_text()
placeholders = re.findall(r'\[Your [^\]]+\]|\[e\.g\.[^\]]+\]', text)
if placeholders:
    print(f'WARNING: {len(placeholders)} placeholders still in brand.md — agent will flag this')
else:
    print('brand.md looks populated')
"
```

A warning here is allowed for a first run, but the agent will call it out.

---

## Step 7 — Seed your hypotheses

**Do:**

Open [knowledge/hypotheses.md](knowledge/hypotheses.md). Add 3–10 hypotheses
about why your store is leaking conversions. Each needs:

- `ID` — sequential (`H-001`, `H-002`, …)
- `Scope` tag — `pdp`, `mini-cart`, `collection`, `homepage`, `checkout`, `site-wide`
- `Statement` — what you suspect
- `Why` — the signal (customer email, session recording, gut feel)
- `Where to look` — which files or metrics
- `Added` — DD-MM-YYYY (today)

**Why:** Hypotheses become investigation priorities. The agent confirms or
refutes each one with data and code citations.

**Verify:**

```bash
grep -c '^- \[' knowledge/hypotheses.md
```

Should print a number ≥ 1 (the count of hypothesis lines).

---

## Step 8 — First dry run

**Do:**

```bash
uv run python scripts/run_agent.py --weekly --dry-run --scope pdp
```

`--dry-run` skips API calls and notifications — it just exercises the script
plumbing and the knowledge-base reads.

**Why:** Catches `.env` typos, missing files, or import errors before you spend
any API quota.

**Verify:** The command exits 0 and prints the steps it would have run. If it
errors, the error message will tell you which `.env` variable or file is wrong.

---

## Step 9 — First real run

**Do:**

```bash
uv run python scripts/run_agent.py --weekly --scope pdp
```

**Why:** This is the real thing — pulls live data, analyses theme files, calls
Claude, writes a report.

**Verify:**

```bash
ls -lt reports/pdp/ | head -5
```

You should see a fresh `DD-MM-YYYY.md` file at the top. Open it — confirm the
report contains:

- Executive summary (3–5 sentences)
- Metrics snapshot with real numbers from your store
- Findings table with file:line citations
- Top 5 actions
- Strategy pulse section

If any section is missing or full of "data unavailable" notes, that points to a
specific scope or env-var issue — re-check Steps 3–5 for the relevant API.

---

## Step 10 (OPTIONAL) — Slack notifications

**Do:**

Pick one of two options (not both):

**Option A — Webhook (simplest):**
1. Create a private Slack channel for yourself (e.g. `#cro-alerts`)
2. Slack → Apps → Incoming Webhooks → Add to Slack → choose that channel
3. Paste the webhook URL into `.env` as `SLACK_WEBHOOK_URL`

**Option B — Bot token + DM (advanced):**
1. https://api.slack.com/apps → Create New App
2. Add `chat:write` scope under OAuth & Permissions
3. Install to workspace
4. Set `SLACK_BOT_TOKEN` (starts `xoxb-`) and `SLACK_DM_USER_ID` in `.env`

**Verify:**

```bash
uv run python scripts/notify.py --test
```

You should receive a test message in Slack.

---

## Step 11 (OPTIONAL) — Email notifications

**Do:**

Fill in `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `NOTIFY_EMAIL` in
`.env`. For Gmail you need an **App Password** (not your account password) —
generate one at https://myaccount.google.com/apppasswords.

**Verify:** Run `scripts/notify.py --test` (same as above). Check your inbox.

---

## Step 12 (OPTIONAL) — GitHub Actions weekly auto-run

Only do this once Step 9 works locally.

**Do:**

1. Push this repo to GitHub (if not already)
2. Repo → Settings → Secrets and variables → Actions → New repository secret
3. Add one secret per variable in `.env.example`:
   `SHOPIFY_SHOP_URL`, `SHOPIFY_ACCESS_TOKEN`, `SHOPIFY_API_VERSION`,
   `ANTHROPIC_API_KEY`, and any notification keys you set up
4. For auto-pulling the theme in CI, also add `SHOPIFY_THEME_ID`
5. Repo → Settings → Actions → General → Workflow permissions →
   **Read and write permissions** (so Actions can commit the report back)
6. Actions → **Weekly CRO Scan** → **Run workflow** → trigger it manually once

**Why:** The Monday 8 AM AEST schedule lives in
[.github/workflows/weekly-scan.yml](.github/workflows/weekly-scan.yml). Until
you set the secrets, the workflow will fail.

**Verify:** The manual workflow run finishes green and commits a new file under
`reports/pdp/`.

---

## Step 13 (OPTIONAL) — Dev agent for theme code changes

Skip this unless you plan to use the agent to write Liquid code changes via PR.

**Do:**

1. Add `SHOPIFY_THEME_REPO` GitHub secret (e.g. `your-org/your-theme-repo`)
2. Create a GitHub PAT with `repo` scope at https://github.com/settings/tokens
3. Add it as `THEME_REPO_PAT` secret
4. Set up branch protection on `main` of your theme repo:
   require PR, require 1 approval (see [GUARDRAILS.md](GUARDRAILS.md))

**Verify:** Create a small test handoff at
`dev-agent/handoffs/DD-MM-YYYY-test.md`, then Actions → **Implement Experiment
(Dev Agent)** → Run workflow → enter the filename. A PR should open against
your theme repo.

---

## You're done

Daily / weekly use looks like:

```bash
# Ad-hoc run focused on something specific
uv run python scripts/run_agent.py --scope pdp

# Or open Claude Code in this directory and prompt naturally
claude
> "Focus on cart drop-off. Re-read knowledge/ and dig into checkout friction."
```

After each completed A/B test, log the result so the agent learns:

```bash
uv run python scripts/log_result.py --import-ab --id PDP-001 \
  --control control.csv --variant variant.csv
```

See the **Logging experiment results** workflow in [CLAUDE.md](CLAUDE.md) for the
conversational version.

---

## Step 14 — Pin to a release tag and stay current

This repo is meant to be cloned per client (see [VERSIONING.md](VERSIONING.md)
for the why). Once you have it working you'll want to (a) stop tracking the
moving `king` branch and pin to a stable release tag, and (b) periodically pull
upstream fixes without losing your local config and reports.

### 14a — Pin to a release tag

**Do:** check what release you cloned from, and pin to a tag rather than the
moving `king` head. From the repo root:

```bash
# List the available release tags
git ls-remote --tags origin | awk -F/ '{print $NF}' | grep -v '\^{}$' | sort -V

# Pin to a specific tag (replace v0.1.0 with the latest you want)
git fetch origin --tags
git checkout v0.1.0
git switch -c king-v0.1.0  # create a local branch off the tag
```

**Why:** the `king` branch moves forward as the upstream maintainer ships
changes. Tags don't. Pinning to a tag means your CI and your local runs only
change when *you* choose to upgrade.

### 14b — Pull upstream improvements when you're ready

**Do (one-time):** add the canonical maintainer repo as a second remote called
`upstream`. Your own client repo stays as `origin`.

```bash
# Replace the URL with whatever the maintainer points you to.
git remote add upstream https://github.com/MAINTAINER/king-cro.git
git remote -v   # confirm: origin is your repo, upstream is the maintainer's
```

**Do (every time you want to upgrade):**

```bash
git fetch upstream --tags
# Look at what changed since your current tag
git log --oneline v0.1.0..upstream/king

# When ready, merge a specific newer tag (not the moving branch)
git checkout king
git merge v0.2.0      # creates a normal merge commit on your king
git push origin king
```

**Why:** merging from a *tag* (not from `upstream/king`) gives you a defined,
auditable change set. Merging from the branch gives you whatever happens to be
on it right now, which is harder to roll back.

### 14c — What if there's a merge conflict?

The only files you should be editing locally are:

- `knowledge/brand.md` — your business context
- `knowledge/hypotheses.md` — your hunches
- `knowledge/history.md`, `knowledge/insights.md`, `knowledge/experiments.md` —
  auto-updated by the agent
- `reports/**` — auto-generated weekly
- `.env` — gitignored, won't conflict
- GitHub Secrets — not in the repo at all

If you have *not* edited code or scripts, conflicts will only ever appear in
your knowledge-base files. Standard fix: `git checkout --ours` on those files
(keep your version of brand.md, history.md, etc.), then re-resolve any
upstream improvements you actually want.

If you *have* edited code (you forked the script), you're on the hook for
maintaining that fork. Try to keep all your customisation in
`knowledge/` and `.env` so this stays painless.

### 14d — Subscribe to release notifications

GitHub → maintainer's repo → **Watch** → **Custom** → tick **Releases only**.
You'll get an email when a new tagged release ships. Most weeks: nothing. Some
weeks: a bugfix worth pulling.

---

## Troubleshooting quick reference

| Symptom | Likely cause | Fix |
|---|---|---|
| `401` from Shopify | Wrong token or missing scope | Re-do Step 3, tick the right scopes |
| `No .liquid files found` | `THEME_DIR` wrong | Re-run Step 4 |
| Report says "data unavailable" everywhere | Missing `read_analytics` scope | Re-do Step 3 |
| Anthropic `invalid_api_key` | Bad key or wrong project | Re-do Step 5 |
| Slack test silent | Channel doesn't allow the webhook | Re-create webhook for a channel you own |
| GitHub Action fails: `permission denied` | Workflow perms not read+write | Step 12, item 5 |
| brand.md placeholders warning | Step 6 not finished | Fill in remaining `[Your …]` blocks |
