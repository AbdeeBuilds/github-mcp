# Research Methodology

**Date established:** 2026-07-04
**Applies to:** All work in the Digital Product Factory.
**Status:** Living document. Update only when a rule actively misleads, not when a new situation feels different.

---

## 1. Problem-First Philosophy

**Stop searching for products. Start searching for problems.**

**Old approach (rejected 2026-07-04):**
- Brainstorm 5 product ideas
- Score and pick the best
- Hope there's a real market

**New approach (current):**
- Find 10 real problems people complain about
- Match each to a product concept
- Score and pick the best problem to solve
- **Validate the problem before building**

**Why the shift:**

Product-first thinking optimizes for "what can we build?" which biases toward easy-to-build commodities (prompt packs, PDFs, templates). These have:
- Low recurring usage
- No moat
- Commoditized competition
- One-time revenue

Problem-first thinking optimizes for "what hurts people most?" which biases toward recurring pain points with defensible solutions. These have:
- High recurring usage
- Real moat potential
- Validated demand (people complaining = demand)
- Recurring revenue

### Product concept constraints

When matching a validated problem to a product concept, apply these constraints:

- **Solve in the simplest way** — 10× better, not 10× more features
- **Prefer recurring, automated solutions** over one-time downloads
- **Prefer tools people use weekly or daily** over tools they use once
- **Prefer tools with moat potential** (data, integration, switching cost, network effect)

---

## 2. The 5 Research Questions

Every recommendation must answer these 5 questions (plus the Solo Founder Velocity filter, §4):

1. **Who** has this problem? (specific demographic, role, industry)
2. **How often** do they experience it? (daily, weekly, monthly, per-event)
3. **How painful** is it? (inconvenience, costs time, costs money, blocks work)
4. **Why are existing solutions inadequate?** (too expensive, too complex, doesn't fit, etc.)
5. **Why would someone choose our solution?** (10× better, niche-specific, etc.)

If you cannot answer all 5 in one sentence each, the problem is not researched enough.

**Sources for problem signals** (in rough priority order):

1. **Reddit** — r/SaaS, r/indiehackers, r/sales, r/sysadmin, r/accounting, r/freelance, r/smallbusiness, r/devops, r/programming, plus role-specific subreddits
2. **Hacker News** — "Ask HN" threads, "Show HN" complaints, "What's your biggest pain at work?"
3. **Twitter/X** — complaints about specific tools, "I wish X existed" posts, workflow threads
4. **LinkedIn** — "What's your biggest challenge" posts, role-specific complaints
5. **G2 / Capterra reviews** — 2-3 star reviews of competitor products (gold for pain signals)
6. **Apify / IndieHackers** — what people are building and why
7. **Customer support tickets** of existing products (if accessible)
8. **Your own experience** — what slows you down at work, daily, weekly, monthly

**Monitoring cadence** (deferred — do not set up before Product #1 ships):

When the first product is live and we have budget, set up:
- 5-10 subreddits per product category being explored
- 3-5 Twitter/X accounts (industry leaders in target verticals)
- 1-2 G2 review feeds (top competitors in target categories)
- 1 Hacker News weekly digest
- 1 Indie Hackers digest

Cron schedule: weekly digest, monthly deep scan of all sources.

---

## 3. Pre-Screen for Recurring

Before investing in a full landing page, pre-screen each candidate problem for recurrence. Ask:

- Do people complain about it **more than once**? (per person)
- Does the **same person** hit it **repeatedly**? (not a one-time fix)
- Is it **frequent enough** that they'd pay to solve it? (daily, weekly, monthly)

**If no to any of these → deprioritize.** A problem that occurs once per person per lifetime is not a business; it's a one-time product with no recurring revenue.

This pre-screen is a fast filter before the full §4 opportunity scoring. It can be done in 5-10 minutes per problem from the §2 source list.

---

## 4. Opportunity Scoring Methodology

Use `scoring-framework.md` v3 for the complete 11-criteria scoring system. The summary:

**11 criteria, weighted to 100:**

| Criterion | Weight | 0 means | 5 means | 10 means |
|---|---|---|---|---|
| **Demand** | 15% | No one complains | Some discussion, a few paid alternatives | Many complain, many pay, recurring asks |
| **Moat / Defensibility** | 15% | Commodity, anyone can copy | Some defensibility (integration, data, brand) | Network effects, deep lock-in, regulatory moat |
| **Solo Founder Velocity** | 20% | Months of work, needs team | Tight, requires expert solo founder | 1 week or less, any competent solo founder |
| **Recurring Usage** | 10% | One-time purchase, no return | Used monthly | Used daily or per-event |
| **Automation Potential** | 10% | 1:1 human time per sale | Mostly automated | Fully automated delivery, zero ops |
| **Competition** | 5% | Zero competitors (red flag) | 3-7 solid competitors (sweet spot) | 20+ competitors, hard to differentiate |
| **Revenue potential** | 5% | $0-100/month realistic | $1k-3k/month | $10k+/month |
| **Difficulty** | 5% | Months of expert work | A few weekends | A weekend build |
| **Time to ship** | 5% | > 30 days | 7-14 days | ≤ 7 days |
| **Maintenance** | 5% | Daily ops, live support | Weekly check-in | Set and forget |
| **Strategic value** | 5% | One-off, no reuse | Some reuse | Skills for 5+ future products |

**Weighted total** = sum of (score × weight) / 10 = score out of 100.

**Auto-reject rules** — reject without further consideration if ANY of:
- Demand < 4
- Recurring Usage < 5
- Moat < 4
- **Solo Founder Velocity < 6**
- Total weighted score < 65

---

## 5. Solo Founder Velocity Filter

A hard engineering filter. Question: **"Can one person realistically build, launch, and validate this in under 14 days?"**

| Score | Meaning |
|---|---|
| 0-3 | Not realistic for a solo founder in 14 days. Needs team. |
| 4-5 | Very tight, only possible for expert solo founders with significant shortcuts. |
| 6-7 | Doable for a competent solo founder, may require scope cuts. |
| 8-9 | Comfortably shippable in 14 days. |
| 10 | 1 week or less. |

For Product #1 selection, velocity is the heaviest-weighted criterion (20%) and is a hard auto-reject at <6.

**Rationale:** "Easy to build" is no longer the goal. The factory wins on finding underserved problems, not on shipping fast. Solo Founder Velocity is the only criterion that respects both speed (the solo constraint) and value (problems worth solving are often not trivial).

---

## 6. Validation Process

**Do not build a product until validation passes.**

For each candidate, run this 1-2 day validation cycle:

1. **Build a 1-page landing page** that promises the product
2. **Drive 50-200 targeted visitors** from one channel
3. **Measure conversion** (email signups, "I would pay" responses, pre-orders)
4. **Pass = ≥5% email conversion OR ≥10 explicit "I would pay" responses**
5. **Below threshold = kill and try the next candidate**

**Channels to drive traffic** (pick one per attempt):

- Reddit — most relevant subreddit for the persona
- Hacker News — Show HN or Ask HN
- Twitter/X — personal network or targeted hashtags
- LinkedIn — relevant groups
- Personal network — DMs to 20-50 likely users
- Niche community — Discord, Slack, forum, subreddit

**Time budget:** 1-2 days per validation attempt. Do not over-engineer the landing page.

---

## 7. Landing Page Methodology

The landing page is the validation tool, not the product page. Keep it simple.

**Required elements:**

- **Headline** — the problem in the customer's words
- **Subhead** — the promise (what the product does, in one line)
- **Email capture form** — single field
- **Optional: pre-order / "I would pay" button** — for paid validation

**Excluded from MVP validation pages:**

- Pricing (unless explicitly testing price point)
- Testimonials (you have none)
- Long feature lists
- Multiple CTAs
- Heavy design / animations

**Recommended structure:**

1. "Do you struggle with [problem]?" (headline)
2. "We built [solution] to help." (subhead)
3. "Get notified when we launch → [email]" (CTA)
4. (Footer: contact info, plain text only)

**Tech stack for validation pages** (all free tiers, defer until needed):

- Carrd or Framer — page builder
- Cloudflare Pages — hosting
- Buttondown — email capture

**Time budget:** 2-4 hours per page. No code reviews, no design polish.

---

## 8. Kill Criteria

Kill the product / idea if ANY of:

**At scoring time (before building a landing page):**

- Demand < 4
- Recurring Usage < 5
- Moat / Defensibility < 4
- Solo Founder Velocity < 6
- Total weighted score < 65

**At validation time (after running a landing page):**

- Email conversion < 5% after 200+ targeted visitors
- Fewer than 10 "I would pay" responses
- Zero pre-orders (if pre-order test was run)

**Post-launch (after MVP ships):**

- Day 30 — < 10 active users with no growth trend
- Day 60 — < 50 active users OR clear churn
- Day 90 — revenue < $100 OR clear "no one would pay" signal
- At any point — refund rate > 30% (product is broken, not undersold)

**When killed:**

1. Capture learnings in the product doc (`product-1-shortlist.md` or successor)
2. Update the scoring weights if the framework misled
3. Move to the next-ranked candidate in the shortlist
4. Do NOT revisit the killed idea for at least 6 months (unless the market shifts)

---

## 9. What "Good" Looks Like

A well-researched problem (i.e., ready to invest in a landing page) satisfies ALL of:

- **≥10 mentions** in the last 30 days in target sources (per §2)
- **≥3 paid alternatives** already exist (validates willingness to pay)
- **Clear weakness in existing solutions** — complaints about price, complexity, or missing features
- **Recurring use case** — daily, weekly, or per-event (passes §3 pre-screen)
- **Defensible solution possible** — at least one of: data moat, integration moat, switching cost, or network effect

If any of these are missing, the research is not done. Go back to §2 sources and dig deeper.

---

## When to update this file

Add or modify a methodology rule when:

- A validation pass gives a clear signal that the rule was wrong
- The rule actively misleads (predicts success, actual outcome is failure, or vice versa)
- A new pattern emerges across multiple validations

Do NOT update this file just because a new situation feels different. Update only when the rule actively misleads.
