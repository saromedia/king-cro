# Handoff Spec Template

Copy this file to `dev-agent/handoffs/DD-MM-YYYY-[experiment-id].md` when requesting
implementation of a CRO experiment.

The CRO agent writes these specs. The dev agent reads them.

---

# Handoff: [Experiment ID] — [Experiment Name]

**Date:** DD-MM-YYYY
**Requested by:** CRO agent / owner
**Status:** pending | in-progress | pr-open | merged | cancelled

## Experiment context

| Field | Value |
|---|---|
| Experiment ID | e.g. PDP-17 |
| Type | e.g. ux |
| Zone | e.g. buybox |
| Test mode | solo / concurrent / sequential |
| Hypothesis | e.g. Showing the price in the ATC button reduces hesitation at click |
| What to measure | e.g. ATC click rate, conversion rate |

## What to build

[Clear description of the feature or change. Written so a developer with no CRO
context can implement it correctly.]

Example:
> Add a schema toggle called "Show price in ATC button" (default: off).
> When enabled, the Add to Cart button should display the variant price alongside
> the button label: "Add to Cart — $49.99". Price should use the `money` filter
> and update dynamically when the variant changes.

## Files likely affected

- `sections/main-product.liquid` — ATC button markup
- `snippets/product-form.liquid` — if form is extracted to a snippet

*(Dev agent should verify these against the actual theme before implementing.)*

## Acceptance criteria

- [ ] Schema toggle exists in the section settings
- [ ] Default is off (does not change live behaviour until toggled)
- [ ] Price updates when variant is switched (no page reload required)
- [ ] Works on mobile (375px)
- [ ] No visual regression on existing button when toggle is off
- [ ] PR opened with description matching the required format

## Notes / constraints

[Anything the dev agent should know. e.g. "The theme uses a custom ATC component
in snippets/buy-buttons.liquid — check there first."]

## Out of scope

[Explicitly list what NOT to do, to prevent scope creep.]

e.g. Do not change button colour, size, or any other attribute.
