# Austin Data Collection Kit (v2 — investment-grade standard)

Updated to the audit's evidence standard. The goal is the first **auditable** local
price dataset — traceable, scope-matched, and honest about what each number measures.

## The three files
- **`canonical-specs.csv`** — standardized job definitions. Read first. Every observation
  maps to one `spec_id`, or it doesn't aggregate.
- **`observations-template.csv`** — one row per price point. Copy to `observations-austin.csv`.
- **`segment-targets.csv`** — progress tracker + the confidence-tier rules.

## Five price measures — never pool them
Advertised, quoted, contracted, final-invoiced, consumer-reported are **different
questions**. Compute medians per `spec_id` **and** per `price_type`. A "$99 starting"
advertised price and a $310 final invoice are not the same fact.

| Measure | Answers | Evidence | Don't confuse with |
|---|---|---|---|
| Advertised | what a provider publicly offers | rate card / checkout | typical paid price |
| Quoted | offered for a stated scope | dated written estimate | final invoice |
| Final-invoiced | what the homeowner paid | invoice / payment record | permit valuation or list price |
| Permit valuation | declared construction value | city permit record | completed cost |
| Consumer estimate | broad planning range | model over raw obs | a contractor quote |

## Permit valuation is NOT a price
Austin permits expose a `valuation` field, but the dataset does **not** establish it as a
paid final cost. Log permits in a **separate scope/intent table** as a weak project signal —
never in the price file, never weighted against invoices. (Correcting the earlier kit, which
mis-weighted it.) Before relying on it at all, get City Development Services' definition of
`valuation` and run a matched sample of 100 permits vs. final invoices by type.

## Confidence tiers (per spec_id, per price_type, scope-matched only)
- **INSUFFICIENT** < 10 → show "not enough local data yet"
- **DIRECTIONAL** 10–24 → rough range, labeled directional
- **PUBLISHED** 25+ → median + P25 + P75 + date range + scope
- **HIGH** 50+ **and** ≥40% tier A/B **and** no dominant provider
Use robust medians/percentiles, not means (emergencies/upgrades skew the tail).

## Source tiers
A = final invoice · B = written quote · C = provider public price · D = consumer self-report ·
E = aggregator estimate. Tier A/B are what earn a HIGH label.

## Where to get it (Austin)
- **Provider public prices (tier C):** capture verbatim from company pages (e.g. productized
  offers like Cowboy Pools; published guides like Bluewater). Record price_type=advertised.
- **Surveys (tier C):** phone/email 20+ companies per spec against the exact scope.
- **Written quotes (tier B):** solicit real bids for a representative property.
- **Final invoices (tier A):** friendly-contractor history dumps + consented homeowner uploads. Gold.
- **Permits:** `data.austintexas.gov` Issued Construction Permits — scope/intent signal only.

Spread ZIPs across Austin (78749, 78745, 78704, 78748, 78702, 78717, 78723, 78735).

## Then stop collecting desk data and run the primary tests
More price rows alone won't de-risk the business. In parallel, run the tests that answer the
open questions:
1. **Provider willingness-to-pay** — present exclusive vs. max-three vs. booked-appointment
   price cards to real contractors. This is the #1 risk; do it early.
2. **Response-time mystery shop** — 100 providers, business hours / evening / weekend.
3. **Quote-upload test** — do homeowners upload, and does it change who they pick?
4. **Max-three routing pilot** — 50 real leads, transparent rules, measure accept→book→close.

## Honesty rule
`confidence` and `observations` in `content.json` must be true, and follow the tiers above.
Pre-launch figures currently in the site are **illustrative placeholders** — replace them
with collected data before promoting any number as an Austin fact.
