# Trueline — content system + live site (v1)

The Phase-1 **visibility surface**: fast, crawlable, schema-marked cost pages that AI
answer engines and bloggers can cite — generated from one content file so you scale
pages by adding data, not writing HTML.

> **Brand name is a placeholder.** Change `brand.name` in `content.json` and rebuild.
> (`Trueline` = "true line / plumb line" — honesty about cost. Swap freely.)

---

## Run it

```bash
python3 build.py            # builds ./site  (deploy this folder)
python3 build.py --inline   # also writes ./preview/*.html (self-contained, open in a browser)
```

No dependencies. Python 3.8+. Output is plain static HTML/CSS — no build step, no JS framework.

## What it generates

- **Homepage** — the "What's going on with your home?" intake hero (the product thesis, not a stock-photo hero).
- **Service hubs** — `/pool-service/`, `/house-cleaning/`, `/lawn-landscaping/`.
- **Cost pages** — `/{service}/{city}/{segment}/` — the link/social/AEO magnets, each with the **Price Confidence** instrument, "questions to ask," and FAQ.
- **Texas Price Index** — `/texas-price-index/` — the citable-data hub.
- `sitemap.xml` + `robots.txt` (AI crawlers explicitly allowed).

Every page ships: `<title>`/meta description/canonical, Open Graph + Twitter cards, and
**JSON-LD** — `Organization`/`WebSite` (home), `Service` + `BreadcrumbList` (hubs),
`FAQPage` + `BreadcrumbList` (cost pages). The FAQ schema is what surfaces you in AI
answers and Google's "People also ask."

## The content system — how to add a page

Open `content.json` and add one object to `cost_pages`:

```json
{
  "service": "pool-service",
  "city": "cedar-park-tx",
  "segment": "Pool equipment repair",
  "low": 150, "high": 600, "unit": "per visit",
  "confidence": "LOW", "observations": 6, "updated": "2026-08",
  "summary": "…", "scope": ["…"], "questions": ["…"],
  "faqs": [{"q":"…","a":"…"}]
}
```

Rebuild. New page, new sitemap entry, new schema — automatically. Add a `city` to the
`cities` array to open a new market; add a `service` to expand verticals.

**Honesty rule (non-negotiable, per the plan):** `confidence` and `observations` must be
true. LOW is fine — it's *more* trustworthy than competitors' fake precision. Never dress a
thin segment as HIGH. This is the brand.

## Deploy (pick one, all free-tier)

- **Netlify / Vercel / Cloudflare Pages:** drag the `site/` folder in, or point at a repo with build command `python3 build.py` and publish dir `site`.
- **GitHub Pages:** push `site/` to a `gh-pages` branch.

Then set your real domain in `content.json` (`brand.domain`) and rebuild so canonicals/OG/sitemap are correct.

## Wire up lead capture (5 min)

The intake form posts nowhere until you set `brand.form_endpoint` in `content.json` to a
real endpoint — **Formspree**, **Netlify Forms**, or your CRM webhook. Until then it shows a
demo alert. The click-to-call buttons already use `brand.phone`.

## What this is NOT yet (deliberately)

Per the build sequence, these come later and are **not** in v1:
- the live **estimator** (this v1 shows curated ranges from `content.json`, not a model);
- **Check My Quote's** price verdict (the CTA captures the lead; the analysis is Phase 2);
- **speed-to-lead / AI booking**, completed-project pages, provider portal.

v1's job is to get you **live, crawlable, and citable** so links + social + AEO traction
start compounding while the seeding work (canonical specs, permit ingest, surveys) runs on
the critical path.

## Suggested next steps

1. Swap the brand name + domain, wire the form, deploy.
2. Stand up the **social content engine** off these pages: each cost page = a "Guess the Price / Fair or Ripoff" post that links back. (Ask me to build the post-generator next.)
3. Begin seeding pool + lawn segments to raise real `observations` / `confidence`.
4. When a segment clears the data-ready gate, flip its confidence and deepen the page.
