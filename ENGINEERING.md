# Engineering Rules

**Established:** 2026-07-04
**Applies to:** All work in the Digital Product Factory (github-mcp and future products).
**Status:** Living document. Update only when a real product exposes a gap or a rule actively misleads.

---

## Rule 1 — Every dependency must justify itself

A new dependency (SaaS subscription, library, custom code, new service, new skill) only enters the project if it supports a live product or live development of one. If no live product currently requires it, postpone it.

**Test:** "Does this help ship Product #1 this week?" If no, postpone.

**No custom code until SaaS fails or $1k MRR.** Use existing services over building our own.

---

## Rule 2 — MVP-first (no business before product, no product before core functionality)

1. **Never build the business before proving the product.** Pricing, hosted versions, team plans, Pro features, observability dashboards, marketing automation, analytics, enterprise features — all come AFTER the core product has real users.
2. **Never build the product before proving the core functionality.** A user must be able to install + connect + authenticate + use the core tools + leave feedback before any other feature.

**Ship the smallest useful version first.** Then decide pricing, hosting, Pro based on real usage signals.

---

## Rule 3 — Reality beats planning

Verify before advancing. Smoke tests before new features. Manual testing before declaring something "done."

**If a smoke test fails, stop immediately and debug before writing any new features.**

---

## Rule 4 — Competitive advantage is finding underserved problems, not producing generic digital downloads

The Digital Product Factory is not a digital-download business. We win by finding recurring pain points and shipping defensible recurring products, not by shipping easy one-time downloads.

**Apply the scoring framework** (`scoring-framework.md`) to validate every idea before building.

---

## When to update this file

Add or modify a rule when:
- A real product exposes a gap the current rules do not cover
- A rule causes friction without delivering value
- A new pattern emerges across multiple products that warrants codification

Do NOT update this file just because a new situation feels different. Update only when the rule actively misleads.
