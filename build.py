#!/usr/bin/env python3
"""
Trueline static site generator.

Reads content.json and emits a fast, crawlable, schema-marked static site.
Add a row to content.json -> rebuild -> new page. That's the content system.

Usage:
    python3 build.py            # build ./site
    python3 build.py --inline   # also write self-contained preview files

No third-party dependencies. Python 3.8+.
"""

import json, os, shutil, html, sys, datetime, re, glob
try:
    import markdown as _md          # pip install markdown  (for the blog)
except Exception:
    _md = None

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(ROOT, "site")
ASSETS_SRC = os.path.join(ROOT, "assets")

def load():
    with open(os.path.join(ROOT, "content.json"), encoding="utf-8") as f:
        return json.load(f)

def esc(s): return html.escape(str(s), quote=True)

def money(n):
    return "${:,}".format(int(n))

def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

# ----------------------------------------------------------------------
# shared chrome
# ----------------------------------------------------------------------
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?'
         'family=Space+Grotesk:wght@500;600;700&'
         'family=Inter:wght@400;500;600&'
         'family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">')

def head(b, title, desc, path, jsonld, css_href="/assets/styles.css", robots=None, canonical=None):
    url = canonical or "https://{}{}".format(b["domain"], path)
    blocks = "\n".join(
        '<script type="application/ld+json">{}</script>'.format(json.dumps(j, ensure_ascii=False))
        for j in jsonld
    )
    robots_tag = f'\n<meta name="robots" content="{esc(robots)}">' if robots else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{esc(url)}">{robots_tag}
<meta property="og:type" content="website">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{esc(url)}">
<meta property="og:site_name" content="{esc(b['name'])}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(desc)}">
{FONTS}
<link rel="stylesheet" href="{css_href}">
{blocks}
</head>
<body>"""

def header(b):
    return f"""
<header class="site-head"><div class="wrap">
  <a class="logo" href="/"><span class="mark"></span>{esc(b['name'])}</a>
  <nav class="nav">
    <a href="/pool-service/">Pool</a>
    <a href="/house-cleaning/">Cleaning</a>
    <a href="/find-prices/">Find Prices</a>
    <a href="/check-my-quote/">Check a Quote</a>
    <a href="/find-a-pro/">Find a Pro</a>
    <a href="/texas-price-index/">Price Index</a>
    <a href="/blog/">Blog</a>
    <a href="/for-pros/">For Pros</a>
    <a class="btn btn-primary" href="/#finder">Get your estimate</a>
  </nav>
</div></header>"""

def footer(b):
    return f"""
<footer class="site-foot"><div class="wrap">
  <div>
    <a class="logo" href="/"><span class="mark"></span>{esc(b['name'])}</a>
    <p class="tag">{esc(b['promise'])}</p>
  </div>
  <div>
    <h4>Services</h4>
    <a href="/pool-service/">Pool service</a>
    <a href="/house-cleaning/">House cleaning</a>
    <a href="/lawn-landscaping/">Lawn &amp; landscaping</a>
    <a href="/texas-price-index/">Texas Price Index</a>
  </div>
  <div>
    <h4>Get started</h4>
    <a href="/find-prices/">Estimate a project</a>
    <a href="/find-prices/">Check a quote</a>
    <a href="tel:{esc(b['phone'])}">{esc(b['phone_display'])}</a>
    <a href="mailto:{esc(b['email'])}">{esc(b['email'])}</a>
  </div>
  <div class="foot-legal" style="grid-column:1/-1">
    {esc(b['name'])} — {esc(b['founded_note'])} · Ranges are preliminary and shown with Price Confidence. Not a substitute for a licensed pro's inspection.
  </div>
</div></footer>
</body></html>"""

def lead_form(b, prefill=""):
    return f"""
<form class="intake" id="intake" data-endpoint="{esc(b['form_endpoint'])}" onsubmit="return tlSubmit(this)">
  <label for="q">What's going on with your home?</label>
  <div class="row">
    <input type="text" id="q" name="q" value="{esc(prefill)}"
      placeholder="e.g. My pool needs weekly service, what's fair?" autocomplete="off">
    <button class="btn btn-primary" type="submit">Get your estimate &rarr;</button>
  </div>
  <div class="chips">
    <span class="chip" onclick="tlChip(this)">My pool needs weekly service</span>
    <span class="chip" onclick="tlChip(this)">$14,800 HVAC quote — is that fair?</span>
    <span class="chip" onclick="tlChip(this)">Backyard floods when it rains</span>
    <span class="chip" onclick="tlChip(this)">Move-out clean for a 3-bed</span>
  </div>
</form>"""

TL_JS = """
<script>
function tlChip(el){var i=document.getElementById('q');if(i){i.value=el.textContent;i.focus();}}
function tlSubmit(f){
  var ep=f.getAttribute('data-endpoint')||'';
  var q=(f.querySelector('#q')||{}).value||'';
  if(!ep||ep.indexOf('REPLACE')===0){
    alert("Thanks — this demo isn't wired to a backend yet.\\n\\nYou typed: "+q+"\\n\\nWire data-endpoint on the form to Formspree / Netlify Forms / your CRM to capture leads.");
    return false;
  }
  return true; // real endpoint: let it post
}
</script>"""

# ----------------------------------------------------------------------
# page builders
# ----------------------------------------------------------------------
ICONS = {
 "pool":'<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round"><path d="M3 16c1.5 0 1.5 1.5 3 1.5S10.5 16 12 16s1.5 1.5 3 1.5S16.5 16 18 16s1.5 1.5 3 1.5"/><path d="M3 20c1.5 0 1.5 1.5 3 1.5S10.5 20 12 20s1.5 1.5 3 1.5S16.5 20 18 20s1.5 1.5 3 1.5"/><path d="M8 16V5a2 2 0 0 1 4 0"/><path d="M12 11h-4"/></svg>',
 "clean":'<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 3l-7 7"/><path d="M12 10l-2-2"/><path d="M8 12l-4 8h6l2-6z"/></svg>',
 "leaf":'<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 20A7 7 0 0 1 4 13c0-6 8-9 16-9 0 8-3 16-9 16z"/><path d="M4 20c4-2 7-5 9-9"/></svg>',
}

def home(b, data):
    services = data["services"]
    svc_cards = ""
    for s in services:
        svc_cards += f"""
    <a class="svc-card" href="/{s['slug']}/">
      <div class="ico">{ICONS.get(s['icon'],'')}</div>
      <h3>{esc(s['name'])}</h3>
      <p>{esc(s['short'].capitalize())}</p>
      <span class="go">See fair local pricing &rarr;</span>
    </a>"""
    jsonld = [
        {"@context":"https://schema.org","@type":"Organization","name":b["name"],
         "url":"https://{}/".format(b["domain"]),
         "description":b["promise"],
         "areaServed":{"@type":"State","name":"Texas"},
         "telephone":b["phone"]},
        {"@context":"https://schema.org","@type":"WebSite","name":b["name"],
         "url":"https://{}/".format(b["domain"])}
    ]
    title = f"{b['name']} — {b['tagline']}"
    desc = b["promise"]
    body = f"""
<section class="hero"><div class="wrap">
  <p class="eyebrow">Independent home pricing · {esc(b['metro'])}, {esc(b['state'])}</p>
  <h1>Before you spend money on your home, check here.</h1>
  <p class="sub">{esc(b['promise'])}</p>
  {finder_widget(b,data)}
  <div class="trust-row">
    <span class="ti"><span class="dot"></span><b>Fair local ranges</b> — not national averages</span>
    <span class="ti"><span class="dot"></span><b>One vetted pro</b> — no spam, no bidding war</span>
    <span class="ti"><span class="dot"></span><b>Free</b> for homeowners</span>
  </div>
</div></section>

<section class="section"><div class="wrap">
  <p class="eyebrow">Start here</p>
  <h2>Pick what your home needs</h2>
  <p class="lead">Fair, local, continuously-updated pricing for Central Texas — with an honest confidence level behind every number.</p>
  <div class="svc-grid">{svc_cards}</div>
</div></section>

<section class="section band"><div class="wrap">
  <p class="eyebrow">How it works</p>
  <h2>From "what should this cost?" to a booked pro</h2>
  <div class="steps">
    <div class="step"><div class="n">01</div><h3>Tell us what's going on</h3><p>Describe the problem, the project, or paste a quote you already have.</p></div>
    <div class="step"><div class="n">02</div><h3>See the fair local range</h3><p>Real Central Texas pricing with a confidence level — no false precision.</p></div>
    <div class="step"><div class="n">03</div><h3>Check your quote</h3><p>We tell you whether an estimate you received looks reasonable, and what to ask.</p></div>
    <div class="step"><div class="n">04</div><h3>Meet one vetted pro</h3><p>Matched to your job — not blasted to five companies who'll call all week.</p></div>
  </div>
</div></section>

<section class="section"><div class="wrap" style="text-align:center">
  <h2 style="margin:0 auto">Know the number before you pick up the phone.</h2>
  <p class="lead" style="margin:12px auto 22px">Start with what your home needs.</p>
  <a class="btn btn-pine" href="/find-prices/">Get your estimate &rarr;</a>
</div></section>
"""
    return head(b,title,desc,"/",jsonld) + header(b) + body + cc_data_script(b,data) + CC_JS + TL_JS + footer(b)

def _projects_block(b, data, svc):
    if svc["slug"] != "pool-service" or not data.get("pool_projects"):
        return ""
    rows="".join(
        f'<a class="list-row" href="/pool-service/{p["city"]}/{p["slug"]}/">'
        f'<div><div class="lr-t">{esc(p["name"])} — {esc([c["name"] for c in data["cities"] if c["slug"]==p["city"]][0])}</div>'
        f'<div class="lr-s">Cost, options &amp; what to ask</div></div>'
        f'<div class="lr-p">{money(p["low"])}–{money(p["high"])}<span class="lr-c">{esc(p["unit"])}</span></div></a>'
        for p in data["pool_projects"])
    return f'<h2 style="margin-top:30px">Popular pool projects</h2><div class="list-grid">{rows}</div>'

def service_hub(b, data, svc):
    explicit = [p for p in data["cost_pages"] if p["service"]==svc["slug"]]
    city_by = {c["slug"]:c for c in data["cities"]}
    # explicit pages first, then a templated page for every remaining city
    covered = {p["city"] for p in explicit}
    pages = list(explicit)
    if svc["slug"] in data["price_finder"]:
        for c in data["cities"]:
            if c["slug"] not in covered:
                pages.append(synth_cost_page(data, svc, c))
    rows = ""
    for p in pages:
        c = city_by[p["city"]]
        href = f"/{svc['slug']}/{p['city']}/{slugify(p['segment'])}/"
        rows += f"""
    <a class="list-row" href="{href}">
      <div>
        <div class="lr-t">{esc(p['segment'])} — {esc(c['name'])}</div>
        <div class="lr-s">{esc(c['name'])}, {esc(c['state'])}</div>
      </div>
      <div class="lr-p">{money(p['low'])}–{money(p['high'])}
        <span class="lr-c">{esc(p['unit'])} · {esc(p['confidence'])}</span>
      </div>
    </a>"""
    jsonld=[
      {"@context":"https://schema.org","@type":"Service",
       "serviceType":svc["name"],"areaServed":{"@type":"State","name":"Texas"},
       "provider":{"@type":"Organization","name":b["name"]}},
      _breadcrumb(b,[("Home","/"),(svc["name"],f"/{svc['slug']}/")])
    ]
    title=f"{svc['name']} in {b['metro']}, {b['state']} — Costs, Companies & Get Matched | {b['name']}"
    desc=f"{svc['name']} in {b['metro']}: fair local costs, vetted companies, and get matched with one pro. {svc['intro'][:80]}"
    body=f"""
<div class="wrap"><div class="crumb"><a href="/">Home</a><span>/</span>{esc(svc['name'])}</div></div>
<section class="section" style="padding-top:26px"><div class="wrap">
  <p class="eyebrow">{esc(b['metro'])}, {esc(b['state'])}</p>
  <h1 style="max-width:22ch">{esc(svc['name'])} in {esc(b['metro'])}, {esc(b['state'])}</h1>
  <p class="lead">{esc(svc['hero_q'])} {esc(svc['intro'])}</p>
  <div class="list-grid">{rows}</div>
  {_projects_block(b,data,svc)}
  <div class="method-note"><b>How we price.</b> {esc(data['methodology'])}</div>
</div></section>
<section class="section band"><div class="wrap" style="text-align:center">
  <h2 style="margin:0 auto">Have a {esc(svc['name'].lower())} quote already?</h2>
  <p class="lead" style="margin:12px auto 20px">Paste it in — we'll tell you if it's fair and what to ask before you sign.</p>
  <a class="btn btn-primary" href="/check-my-quote/">Check my quote &rarr;</a>
</div></section>
"""
    return head(b,title,desc,f"/{svc['slug']}/",jsonld) + header(b) + body + TL_JS + footer(b)

CONF_CLASS = {"HIGH":"high","PUBLISHED":"medium","MEDIUM":"medium","DIRECTIONAL":"low","LOW":"low","INSUFFICIENT":"low"}
def conf_class(label): return CONF_CLASS.get(str(label).upper(), "low")

def cost_page(b, data, p, svc, city):
    conf = conf_class(p["confidence"])
    path = f"/{svc['slug']}/{city['slug']}/{slugify(p['segment'])}/"
    scope = "".join(f"<li>{esc(x)}</li>" for x in p["scope"])
    qs = "".join(f"<li>{esc(x)}</li>" for x in p["questions"])
    faqs = "".join(
        f'<details><summary>{esc(f["q"])}</summary><div class="a">{esc(f["a"])}</div></details>'
        for f in p["faqs"]
    )
    faq_ld = {"@context":"https://schema.org","@type":"FAQPage","mainEntity":[
        {"@type":"Question","name":f["q"],
         "acceptedAnswer":{"@type":"Answer","text":f["a"]}} for f in p["faqs"]]}
    bc = _breadcrumb(b,[("Home","/"),(svc["name"],f"/{svc['slug']}/"),
                        (f"{city['name']}",path)])
    title=f"{p['segment']} Cost in {city['name']}, {city['state']} ({p['updated'][:4]}) — {b['name']}"
    desc=f"{p['segment']} in {city['name']} runs about {money(p['low'])}–{money(p['high'])} {p['unit']} (Price Confidence: {p['confidence']}). {p['summary'][:80]}"
    meter = '<span class="m"></span><span class="m"></span><span class="m"></span>'
    body=f"""
<div class="wrap"><div class="crumb">
  <a href="/">Home</a><span>/</span><a href="/{svc['slug']}/">{esc(svc['name'])}</a><span>/</span>{esc(city['name'])}
</div></div>
<section class="cost-head"><div class="wrap">
  <p class="eyebrow">{esc(city['name'])}, {esc(city['state'])} · {esc(p['updated'])}</p>
  <h1>{esc(p['segment'])} cost in {esc(city['name'])}</h1>
  <p class="summary">{esc(p['summary'])}</p>

  <div class="pc {conf}">
    <div class="pc-label">Fair local range</div>
    <div class="range">{money(p['low'])}–{money(p['high'])}<span class="unit">{esc(p['unit'])}</span></div>
    <div class="pc-meter-wrap">
      <div class="pc-meter">{meter}</div>
      <span class="conf-tag">PRICE CONFIDENCE: {esc(p['confidence'])}</span>
      <span class="obs">{p['observations']} local observations · updated {esc(p['updated'])}</span>
      <a class="method-link" href="#method">How we know &rarr;</a>
    </div>
  </div>

  <div class="cta-inline">
    <div>
      <h3>Got a quote for this?</h3>
      <p>Paste it in and we'll show you how it compares to fair local pricing — and what to ask before you sign.</p>
    </div>
    <div class="acts">
      <a class="btn btn-primary" href="/find-prices/">Check my quote</a>
      <a class="btn btn-ghost" href="tel:{esc(b['phone'])}">Call {esc(b['phone_display'])}</a>
    </div>
  </div>
</div></section>

<section class="section" style="padding-top:8px"><div class="wrap">
  <div class="two-col">
    <div class="block">
      <h2>What's included</h2>
      <ul class="scope-list">{scope}</ul>
      <h2 style="margin-top:30px">Questions to ask before you hire</h2>
      <ul class="q-list">{qs}</ul>
    </div>
    <aside class="aside">
      <h3>About {esc(city['name'])}</h3>
      <p>{esc(city['note'])}</p>
    </aside>
  </div>

  <div class="faq" style="margin-top:34px">
    <h2>Common questions</h2>
    {faqs}
  </div>

  <div class="method-note" id="method"><b>How we know.</b> {esc(data['methodology'])}</div>
</div></section>
"""
    return head(b,title,desc,path,[bc,faq_ld]) + header(b) + body + TL_JS + footer(b)

def price_index(b, data):
    # simple hub that lists every priced segment — this is the citable asset
    rows=""
    city_by={c["slug"]:c for c in data["cities"]}
    svc_by={s["slug"]:s for s in data["services"]}
    for p in sorted(data["cost_pages"], key=lambda x:(x["service"],x["city"])):
        c=city_by[p["city"]]; s=svc_by[p["service"]]
        href=f"/{s['slug']}/{p['city']}/{slugify(p['segment'])}/"
        rows+=f"""
    <a class="list-row" href="{href}">
      <div><div class="lr-t">{esc(p['segment'])}</div><div class="lr-s">{esc(s['name'])} · {esc(c['name'])}, {esc(c['state'])}</div></div>
      <div class="lr-p">{money(p['low'])}–{money(p['high'])}<span class="lr-c">{esc(p['unit'])} · {esc(p['confidence'])} · n={p['observations']}</span></div>
    </a>"""
    jsonld=[_breadcrumb(b,[("Home","/"),("Texas Price Index","/texas-price-index/")])]
    title=f"Texas Home-Services Price Index — {b['name']}"
    desc="Independent, continuously-updated fair pricing for home services across Central Texas, with a confidence level behind every number."
    body=f"""
<div class="wrap"><div class="crumb"><a href="/">Home</a><span>/</span>Texas Price Index</div></div>
<section class="section" style="padding-top:26px"><div class="wrap">
  <p class="eyebrow">Independent data</p>
  <h1 style="max-width:20ch">The Texas Home-Services Price Index</h1>
  <p class="lead">Fair local ranges for common home projects across Central Texas — each shown with the number of local observations behind it and an honest confidence level. Updated continuously as we collect real quotes and completed-project prices.</p>
  <div class="list-grid">{rows}</div>
  <div class="method-note"><b>Methodology.</b> {esc(data['methodology'])}</div>
</div></section>
"""
    return head(b,title,desc,"/texas-price-index/",jsonld)+header(b)+body+TL_JS+footer(b)

# ----------------------------------------------------------------------
# BLOG  — drop a .md file in content/blog/, rebuild, done.
# ----------------------------------------------------------------------
def _front_matter(text):
    """Parse optional '--- key: value ---' front matter. Returns (meta, body)."""
    meta = {}
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            for line in text[3:end].strip().splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
            return meta, text[end + 4:].lstrip("\n")
    return meta, text

def _md_html(body):
    if _md:
        return _md.markdown(body, extensions=["extra", "sane_lists", "toc"])
    # minimal fallback if markdown isn't installed
    paras = [p.strip() for p in body.split("\n\n") if p.strip()]
    return "\n".join("<p>{}</p>".format(esc(p)) for p in paras)

def load_posts():
    posts = []
    d = os.path.join(ROOT, "content", "blog")
    if not os.path.isdir(d):
        return posts
    for fp in sorted(glob.glob(os.path.join(d, "*.md"))):
        meta, body = _front_matter(open(fp, encoding="utf-8").read())
        base = os.path.splitext(os.path.basename(fp))[0]
        # filename like 2026-08-08-my-title -> date + slug fallback
        m = re.match(r"(\d{4}-\d{2}-\d{2})-(.+)", base)
        meta.setdefault("date", m.group(1) if m else datetime.date.today().isoformat())
        meta["slug"] = meta.get("slug") or (m.group(2) if m else slugify(base))
        meta.setdefault("title", "Untitled post")
        meta.setdefault("description", "")
        meta.setdefault("meta_title", "")
        meta.setdefault("meta_description", "")
        meta.setdefault("canonical", "")
        meta.setdefault("author", None)
        meta.setdefault("tags", "")
        meta["_html"] = _md_html(body)
        posts.append(meta)
    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts

def blog_index(b, posts):
    cards = ""
    for p in posts:
        cards += f"""
    <a class="list-row" href="/blog/{esc(p['slug'])}/">
      <div>
        <div class="lr-t">{esc(p['title'])}</div>
        <div class="lr-s">{esc(p.get('description',''))}</div>
      </div>
      <div class="lr-p"><span class="lr-c">{esc(p['date'])}</span></div>
    </a>"""
    if not posts:
        cards = '<p class="lead">No posts yet. Drop a Markdown file in <code>content/blog/</code> and rebuild.</p>'
    jsonld = [_breadcrumb(b, [("Home", "/"), ("Blog", "/blog/")])]
    title = f"Blog — {b['name']} · Texas home pricing & advice"
    desc = f"Straight talk on what home services cost in {b['metro']} and how to hire well — from {b['name']}."
    body = f"""
<div class="wrap"><div class="crumb"><a href="/">Home</a><span>/</span>Blog</div></div>
<section class="section" style="padding-top:26px"><div class="wrap">
  <p class="eyebrow">Field notes</p>
  <h1 style="max-width:20ch">Straight talk on what home projects cost</h1>
  <p class="lead">Local pricing, hiring advice, and what our Texas data actually shows.</p>
  <div class="list-grid" style="margin-top:26px">{cards}</div>
</div></section>"""
    return head(b, title, desc, "/blog/", jsonld) + header(b) + body + TL_JS + footer(b)

def blog_post(b, p):
    path = f"/blog/{p['slug']}/"
    tags = [t.strip() for t in p.get("tags", "").split(",") if t.strip()]
    art = {
        "@context": "https://schema.org", "@type": "BlogPosting",
        "headline": p["title"], "datePublished": p["date"],
        "dateModified": p["date"],
        "description": p.get("description", ""),
        "author": {"@type": "Organization", "name": p.get("author") or b["name"]},
        "publisher": {"@type": "Organization", "name": b["name"]},
        "mainEntityOfPage": "https://{}{}".format(b["domain"], path),
        "keywords": ", ".join(tags),
    }
    bc = _breadcrumb(b, [("Home", "/"), ("Blog", "/blog/"), (p["title"], path)])
    title = p.get("meta_title") or f"{p['title']} — {b['name']}"
    desc = p.get("meta_description") or p.get("description", "")
    canonical = p.get("canonical") or None
    body = f"""
<div class="wrap"><div class="crumb"><a href="/">Home</a><span>/</span><a href="/blog/">Blog</a><span>/</span>{esc(p['title'][:40])}</div></div>
<article class="section post"><div class="wrap">
  <p class="eyebrow">{esc(p['date'])}{(" · " + esc(", ".join(tags))) if tags else ""}</p>
  <h1>{esc(p['title'])}</h1>
  <div class="post-body">{p['_html']}</div>
  <div class="cta-inline" style="margin-top:34px">
    <div><h3>Wondering what your project should cost?</h3>
      <p>Get a fair local range — and check a quote you already have — in a couple of taps.</p></div>
    <div class="acts"><a class="btn btn-primary" href="/find-prices/">Get your estimate</a></div>
  </div>
</div></article>"""
    return head(b, title, desc, path, [bc, art], canonical=canonical) + header(b) + body + TL_JS + footer(b)

def _breadcrumb(b, items):
    return {"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
        {"@type":"ListItem","position":i+1,"name":name,
         "item":"https://{}{}".format(b["domain"],path)}
        for i,(name,path) in enumerate(items)]}

# ----------------------------------------------------------------------
# write helpers
# ----------------------------------------------------------------------
def write(path, content):
    full=os.path.join(SITE,path.strip("/"),"index.html") if not path.endswith(".xml") and not path.endswith(".txt") else os.path.join(SITE,path.strip("/"))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full,"w",encoding="utf-8") as f: f.write(content)
    return full

# ======================================================================
# CONSUMER: ZIP + service price finder  ->  easy lead capture
# ======================================================================
def cc_data_script(b, data):
    return ("<script>window.CC_PRICING=" + json.dumps(data["price_finder"]) +
            ";window.CC_ZIPS=" + json.dumps(data["austin_zips"]) +
            ";window.CC_ENDPOINT=" + json.dumps(b["form_endpoint"]) +
            ";window.CC_PHONE=" + json.dumps(b["phone"]) + ";</script>")

def finder_widget(b, data):
    opts = "".join(f'<option value="{s["slug"]}">{esc(s["name"])}</option>' for s in data["services"])
    return f"""
<div class="finder" id="finder">
  <span class="flabel">Find your fair local price</span>
  <div class="frow">
    <select id="cc-svc" aria-label="Service">
      <option value="">Choose a service…</option>{opts}
    </select>
    <input type="text" id="cc-zip" inputmode="numeric" maxlength="5" placeholder="ZIP code" aria-label="ZIP code">
    <button class="btn btn-primary" type="button" onclick="ccFind()">See prices &rarr;</button>
  </div>
  <div class="cc-result" id="cc-result"></div>
</div>"""

CC_JS = """
<script>
function ccMoney(n){return "$"+Number(n).toLocaleString();}
function ccVal(id){var e=document.getElementById(id);return e?e.value:"";}
function ccFind(){
  var svc=document.getElementById("cc-svc").value;
  var zip=(document.getElementById("cc-zip").value||"").trim();
  var out=document.getElementById("cc-result");
  if(!svc){out.innerHTML="<p class='cc-hint'>Please choose a service.</p>";out.style.display="block";return;}
  if(!/^\\d{5}$/.test(zip)){out.innerHTML="<p class='cc-hint'>Enter a valid 5-digit ZIP code.</p>";out.style.display="block";return;}
  var p=window.CC_PRICING[svc]; var inArea=window.CC_ZIPS.indexOf(zip)>-1;
  window.CC_CUR={svc:svc,zip:zip,inArea:inArea,p:p};
  var head;
  if(inArea&&p){
    head="<div class='cc-r-label'>Fair local range \\u2014 "+p.name+" \\u00b7 "+zip+"</div>"+
         "<div class='cc-range'>"+ccMoney(p.low)+"\\u2013"+ccMoney(p.high)+"<span class='u'>"+p.unit+"</span></div>"+
         "<div class='cc-meta'>Price Confidence: "+p.confidence+" \\u00b7 "+p.n+"</div>";
  } else {
    head="<div class='cc-r-label'>"+zip+"</div>"+
         "<div class='cc-range' style='font-size:22px'>We\\u2019re Austin-first today</div>"+
         "<div class='cc-meta'>No local range for your ZIP yet \\u2014 but you can still check a quote, request a pro, or get deal alerts.</div>";
  }
  out.innerHTML="<div class='cc-card'>"+head+ccDoorsHTML()+"<div class='cc-panel' id='cc-panel'></div></div>";
  out.style.display="block"; ccWireDoors();
  out.scrollIntoView({behavior:"smooth",block:"nearest"});
}
function ccDoorsHTML(){
  return "<div class='cc-doors-intro'>That\\u2019s the local range. Want to go further?</div>"+
    "<div class='cc-doors'>"+
      "<button class='cc-door primary' data-door='quote'><span class='d-t'>Is my quote fair?</span><span class='d-s'>Paste a quote you already have \\u2014 get a verdict and what to ask.</span></button>"+
      "<button class='cc-door' data-door='price'><span class='d-t'>Get a real price for my home</span><span class='d-s'>A vetted pro gives you a firm quote. You choose how many.</span></button>"+
      "<button class='cc-door' data-door='alerts'><span class='d-t'>Just send me deals</span><span class='d-s'>Email alerts for specials in your ZIP. No calls.</span></button>"+
    "</div>";
}
function ccWireDoors(){
  document.querySelectorAll("#cc-result .cc-door").forEach(function(btn){
    btn.onclick=function(){
      document.querySelectorAll("#cc-result .cc-door").forEach(function(x){x.classList.remove("open");});
      btn.classList.add("open"); ccOpenDoor(btn.dataset.door);
    };
  });
}
function ccOpenDoor(kind){
  var c=window.CC_CUR, panel=document.getElementById("cc-panel"), svcName=(c.p?c.p.name.toLowerCase():"your service"), h="";
  if(kind==="quote"){
    h="<div class='cc-form'><div class='cc-form-h'>Is your quote fair?</div>"+
      "<p class='cc-form-p'>Tell us what you were quoted and we\\u2019ll compare it to local pricing \\u2014 plus the questions to ask before you sign.</p>"+
      "<input type='text' id='q-amt' placeholder='What were you quoted? (e.g. $14,800)'>"+
      "<input type='text' id='q-scope' placeholder='What\\u2019s the job / what\\u2019s included?'>"+
      "<input type='text' id='q-name' placeholder='Your name'>"+
      "<input type='text' id='q-contact' placeholder='Phone or email'>"+
      "<button class='btn btn-primary'>Check my quote \\u2192</button>"+
      "<p class='cc-consent'>We\\u2019ll send your verdict. We can connect you with one vetted pro for a second-opinion quote \\u2014 only if you ask.</p></div>";
  } else if(kind==="price"){
    h="<div class='cc-form'><div class='cc-form-h'>Get a real price for your home</div>"+
      "<p class='cc-form-p'>A vetted "+svcName+" pro will give you a firm quote for your specific home.</p>"+
      "<input type='text' id='p-detail' placeholder='Your home (size, timing, anything relevant)'>"+
      "<div class='cc-choice'><span class='cc-choice-l'>How many pros can contact you?</span>"+
        "<label class='cc-opt'><input type='radio' name='npro' value='1' checked> One vetted pro <em>(recommended)</em></label>"+
        "<label class='cc-opt'><input type='radio' name='npro' value='3'> Up to three</label></div>"+
      "<input type='text' id='p-name' placeholder='Your name'>"+
      "<input type='text' id='p-contact' placeholder='Phone or email'>"+
      "<button class='btn btn-primary'>Get my price \\u2192</button>"+
      "<p class='cc-consent'>By continuing you agree we can share your request with your chosen pro(s) so they can contact you about this job. No one else.</p></div>";
  } else {
    h="<div class='cc-form'><div class='cc-form-h'>Deals in "+c.zip+"</div>"+
      "<p class='cc-form-p'>We\\u2019ll email you when there\\u2019s a special for "+svcName+" near you. No calls, no pro contact.</p>"+
      "<input type='text' id='a-email' placeholder='Email address'>"+
      "<label class='cc-opt'><input type='checkbox' id='a-consent'> Email me deals for this service in my area. Unsubscribe anytime.</label>"+
      "<button class='btn btn-primary'>Set up alerts \\u2192</button></div>";
  }
  panel.innerHTML=h; panel.style.display="block";
  panel.querySelector("button").onclick=function(){ccSubmit(kind);};
  panel.scrollIntoView({behavior:"smooth",block:"nearest"});
}
function ccSubmit(kind){
  var c=window.CC_CUR, payload={service:c.svc,zip:c.zip,source:kind}, err="";
  if(kind==="quote"){payload.quote_amount=ccVal("q-amt");payload.quote_scope=ccVal("q-scope");payload.name=ccVal("q-name");payload.contact=ccVal("q-contact");if(!payload.quote_amount||!payload.contact){err="Add the quoted amount and your contact.";}}
  else if(kind==="price"){payload.detail=ccVal("p-detail");payload.name=ccVal("p-name");payload.contact=ccVal("p-contact");var r=document.querySelector("input[name=npro]:checked");payload.pros=r?r.value:"1";if(!payload.name||!payload.contact){err="Add your name and contact.";}}
  else {payload.email=ccVal("a-email");var ok=(document.getElementById("a-consent")||{}).checked;if(!payload.email||!ok){err="Add your email and check the box.";}}
  if(err){alert(err);return;}
  var msg={quote:"Quote submitted \\u2713 \\u2014 we\\u2019ll send your verdict.",price:"Request sent \\u2713 \\u2014 your chosen pro(s) will reach out.",alerts:"You\\u2019re subscribed \\u2713 \\u2014 we\\u2019ll email deals in "+c.zip+"."}[kind];
  var ep=window.CC_ENDPOINT||"";
  if(!ep||ep.indexOf("REPLACE")===0){document.getElementById("cc-panel").innerHTML="<div class='cc-done'>"+msg+"<div class='cc-meta' style='margin-top:6px'>Demo mode \\u2014 wire CC_ENDPOINT to capture: "+JSON.stringify(payload)+"</div></div>";return;}
  var f=document.createElement("form");f.method="POST";f.action=ep;for(var k in payload){var i=document.createElement("input");i.type="hidden";i.name=k;i.value=payload[k]||"";f.appendChild(i);}document.body.appendChild(f);f.submit();
}
</script>"""

def find_prices_page(b, data):
    jsonld=[_breadcrumb(b,[("Home","/"),("Find prices","/find-prices/")])]
    title=f"Find home-service prices by ZIP in Austin — {b['name']}"
    desc="Pick your service and enter your ZIP to see the fair local Austin range, then get matched with one vetted pro."
    body=f"""
<div class="wrap"><div class="crumb"><a href="/">Home</a><span>/</span>Find prices</div></div>
<section class="section" style="padding-top:26px"><div class="wrap">
  <p class="eyebrow">Free · {esc(b['metro'])}, {esc(b['state'])}</p>
  <h1 style="max-width:18ch">What should it cost in your ZIP?</h1>
  <p class="lead">Pick a service, enter your ZIP, and see the fair local range — then get matched with one vetted pro. No spam, no bidding war.</p>
  <div style="margin-top:22px">{finder_widget(b,data)}</div>
</div></section>
{cc_data_script(b,data)}{CC_JS}"""
    return head(b,title,desc,"/find-prices/",jsonld)+header(b)+body+footer(b)

# ======================================================================
# PROVIDER: onboarding + lead packages + 24/7 answering add-on
# ======================================================================
def for_pros_page(b, data):
    pp=data["pro_pricing"]
    rows="".join(f'<tr><td>{esc(v["name"])}</td><td class="num">${v["cpl"]}/lead</td></tr>' for v in pp["verticals"])
    packs="".join(
        f'<div class="pack" data-qty="{p["qty"]}" data-disc="{p["discount"]}" onclick="ccPack(this)">'
        f'<div class="pk-name">{esc(p["name"])}</div>'
        f'<div class="pk-qty">{p["qty"]} lead{"s" if p["qty"]>1 else ""}</div>'
        f'<div class="pk-disc">{("save "+str(int(p["discount"]*100))+"%") if p["discount"] else "flat rate"}</div></div>'
        for p in pp["packages"])
    vopts="".join(f'<option value="{v["cpl"]}">{esc(v["name"])} (${v["cpl"]}/lead)</option>' for v in pp["verticals"])
    addons="".join(
        f'<div class="addon"><h4>{esc(a["name"])}</h4><div class="price">${a["price"]}/mo</div><p>{esc(a["desc"])}</p></div>'
        for a in pp["answering"])
    jsonld=[_breadcrumb(b,[("Home","/"),("For pros","/for-pros/")])]
    title=f"Get exclusive Austin leads — {b['name']} for pros"
    desc="Exclusive, booked home-service leads for Austin pros. Pay only for the leads you want. First 5 free."
    body=f"""
<div class="wrap"><div class="crumb"><a href="/">Home</a><span>/</span>For pros</div></div>

<section class="hero" style="padding:56px 0 34px"><div class="wrap">
  <p class="eyebrow">For Austin home-service pros</p>
  <h1 style="max-width:16ch">Exclusive booked jobs. Not shared leads.</h1>
  <p class="sub">{esc(pp['exclusivity'])} Pay only for the leads you want — flat, upfront, no subscription to start.</p>
  <div class="free-banner"><b>Limited time:</b> your first {pp['free_leads']['count']} leads are free — {esc(pp['free_leads']['note'])}.</div>
  <a class="btn btn-primary" href="#signup">Claim 5 free leads &rarr;</a>
</div></section>

<section class="section"><div class="wrap">
  <p class="eyebrow">How it works</p>
  <h2>Answer fast, win the job</h2>
  <div class="steps">
    <div class="step"><div class="n">01</div><h3>Tell us your trade & ZIPs</h3><p>Pick your services and the areas you cover.</p></div>
    <div class="step"><div class="n">02</div><h3>Buy the leads you want</h3><p>Flat price per lead. Choose a pack or pay as you go.</p></div>
    <div class="step"><div class="n">03</div><h3>Get exclusive matches</h3><p>Each lead goes to you alone — never blasted to five pros.</p></div>
    <div class="step"><div class="n">04</div><h3>We can answer for you</h3><p>Optional 24/7 answering books the job before you call back.</p></div>
  </div>
</div></section>

<section class="section band"><div class="wrap">
  <p class="eyebrow">Pricing</p>
  <h2>Flat price per lead — you set the volume</h2>
  <p class="lead">Rates reflect what each Austin vertical's leads are worth. No shared leads, no bidding war.</p>
  <table class="price-table"><tr><th>Vertical</th><th>Price per exclusive lead</th></tr>{rows}</table>

  <div class="pack-selector" style="margin-top:22px">
    <span class="flabel">Estimate your lead budget</span>
    <div class="frow" style="display:flex;gap:10px;margin-bottom:6px">
      <select id="pk-vert" onchange="ccPackCalc()" style="flex:1;font-size:16px;padding:12px;border:1.5px solid var(--limestone-line);border-radius:10px">{vopts}</select>
    </div>
    <div class="pack-grid" id="pk-grid">{packs}</div>
    <div class="pack-out">
      <div><div class="po-total" id="pk-total">$0</div><div class="po-sub" id="pk-sub">choose a pack</div></div>
      <a class="btn btn-primary" href="#signup">Start with this &rarr;</a>
    </div>
    <p class="pilot-note">First {pp['free_leads']['count']} leads free. After that you're only charged when an exclusive, in-area lead is routed to you.</p>
  </div>
</div></section>

<section class="section"><div class="wrap">
  <p class="eyebrow">Add-on</p>
  <h2>24/7 answering — win the 78% who hire the first responder</h2>
  <p class="lead">Most homeowners hire whoever answers first, and most contractors can't. Let us answer, qualify, and book — in English and Spanish — so you don't lose the job while you're on a roof.</p>
  <div class="addon-grid">{addons}</div>
  <p class="pilot-note">Pilot pricing — introductory rates while we measure real call volume, duration, and booking rates. Not a guaranteed long-term price.</p>
</div></section>

<section class="section band" id="signup"><div class="wrap" style="max-width:720px">
  <p class="eyebrow">Get started</p>
  <h2>Claim your 5 free leads</h2>
  <p class="lead">Tell us about your business and share your service pricing (that's what unlocks the free leads and powers your matches).</p>
  <form class="intake" style="margin-top:16px" data-endpoint="{esc(b['form_endpoint'])}" onsubmit="return ccProSubmit(this)">
    <div class="frow"><input type="text" name="biz" placeholder="Business name" style="width:100%"></div>
    <div class="frow" style="margin-top:8px"><input type="text" name="contact" placeholder="Your name & phone/email" style="width:100%"></div>
    <div class="frow" style="margin-top:8px"><input type="text" name="verticals" placeholder="Services you offer (e.g. pool, cleaning)" style="width:100%"></div>
    <div class="frow" style="margin-top:8px"><input type="text" name="zips" placeholder="ZIP codes you serve" style="width:100%"></div>
    <div class="frow" style="margin-top:8px"><input type="text" name="pricing" placeholder="Your typical prices (helps us match & unlocks free leads)" style="width:100%"></div>
    <button class="btn btn-primary" type="submit" style="margin-top:12px">Claim 5 free leads &rarr;</button>
    <p class="pilot-note" style="margin-top:8px">See the routing engine in action on our <a href="/pros/simulator/">lead-routing demo</a>.</p>
  </form>
</div></section>

<script>
var CC_PACK={{qty:0,disc:0}};
function ccPack(el){{document.querySelectorAll('.pack').forEach(function(p){{p.classList.remove('sel')}});el.classList.add('sel');CC_PACK.qty=+el.dataset.qty;CC_PACK.disc=+el.dataset.disc;ccPackCalc();}}
function ccPackCalc(){{
  var cpl=+document.getElementById('pk-vert').value; var q=CC_PACK.qty||0; var d=CC_PACK.disc||0;
  if(!q){{document.getElementById('pk-total').textContent='$0';document.getElementById('pk-sub').textContent='choose a pack';return;}}
  var total=Math.round(cpl*q*(1-d)); var eff=(total/q).toFixed(0);
  document.getElementById('pk-total').textContent='$'+total.toLocaleString();
  document.getElementById('pk-sub').textContent=q+' exclusive leads · $'+eff+'/lead effective';
}}
function ccProSubmit(f){{var ep=f.getAttribute('data-endpoint')||'';if(!ep||ep.indexOf('REPLACE')===0){{alert('Thanks! Demo mode — wire your form endpoint to capture this signup.');return false;}}return true;}}
</script>"""
    return head(b,title,desc,"/for-pros/",jsonld)+header(b)+body+footer(b)

# ======================================================================
# PROVIDER: live lead-routing simulator (prototype of backend logic)
# ======================================================================
def simulator_page(b, data):
    jsonld=[_breadcrumb(b,[("Home","/"),("For pros","/for-pros/"),("Routing demo","/pros/simulator/")])]
    title=f"Lead-routing demo — {b['name']}"
    desc="See how CasaCost routes exclusive leads to pros based on service, ZIP, and paid lead credits."
    body=f"""
<div class="wrap"><div class="crumb"><a href="/">Home</a><span>/</span><a href="/for-pros/">For pros</a><span>/</span>Routing demo</div></div>
<section class="section" style="padding-top:26px"><div class="wrap">
  <p class="eyebrow">How routing works</p>
  <h1 style="max-width:20ch">Exclusive routing by service, ZIP, and paid credits</h1>
  <p class="lead">A lead is matched to <b>one</b> eligible pro — one who covers that service and ZIP and has lead credits remaining. We rotate fairly (least-recently-served first) so everyone who paid gets a fair share, then decrement one credit. This is a working model of the logic a backend runs.</p>

  <div class="sim"><div class="sim-grid">
    <div>
      <h3>Pros &amp; remaining credits</h3>
      <div id="sim-biz"></div>
      <button class="btn btn-ghost" type="button" onclick="simReset()" style="margin-top:8px">Reset demo</button>
    </div>
    <div>
      <h3>Send a lead</h3>
      <div class="sim-controls">
        <div class="frow">
          <select id="sim-svc">
            <option value="pool-service">Pool service</option>
            <option value="house-cleaning">House cleaning</option>
            <option value="lawn-landscaping">Lawn &amp; landscaping</option>
          </select>
          <select id="sim-zip"><option>78749</option><option>78704</option><option>78613</option><option>78660</option></select>
          <button class="btn btn-primary" type="button" onclick="simLead()">Route lead &rarr;</button>
        </div>
      </div>
      <div class="sim-log" id="sim-log"></div>
    </div>
  </div></div>
  <p class="sim-note">Prototype: state is in-memory and resets on reload. In production this logic runs server-side (Supabase + Stripe for credits); the front end never decides routing.</p>
</div></section>

<script>
var SIM_SEED=[
 {{name:"Blue Line Pools", svc:["pool-service"], zips:["78749","78704","78746"], credits:3, served:0}},
 {{name:"Cap City Pool Care", svc:["pool-service"], zips:["78749","78660"], credits:1, served:0}},
 {{name:"Hill Country Mowing", svc:["lawn-landscaping"], zips:["78749","78613","78660"], credits:5, served:0}},
 {{name:"Sparkle Maids ATX", svc:["house-cleaning"], zips:["78704","78749"], credits:2, served:0}},
 {{name:"North ATX Clean Co", svc:["house-cleaning"], zips:["78660","78613"], credits:0, served:0}}
];
var SIM=JSON.parse(JSON.stringify(SIM_SEED));
function simRender(won){{
  var h='';
  SIM.forEach(function(b,i){{
    var zero=b.credits<=0?' zero':''; var win=(won===i)?' won':'';
    h+='<div class="biz'+win+'"><div class="bz-top"><span class="bz-name">'+b.name+'</span>'+
       '<span class="bz-credits'+zero+'">'+b.credits+' credits</span></div>'+
       '<div class="bz-meta">'+b.svc.join(', ')+' · ZIPs '+b.zips.join(' ')+' · served '+b.served+'</div></div>';
  }});
  document.getElementById('sim-biz').innerHTML=h;
}}
function simLog(msg,cls){{var l=document.getElementById('sim-log');l.innerHTML='<div class="'+(cls||'')+'">'+msg+'</div>'+l.innerHTML;}}
function simLead(){{
  var svc=document.getElementById('sim-svc').value, zip=document.getElementById('sim-zip').value;
  // eligibility gate: service match + ZIP match + credits remaining
  var elig=[];
  SIM.forEach(function(b,i){{ if(b.svc.indexOf(svc)>-1 && b.zips.indexOf(zip)>-1 && b.credits>0) elig.push(i); }});
  if(!elig.length){{ simLog('&#9888; Lead ['+svc+' / '+zip+'] &mdash; no eligible pro with credits. Would go to waitlist / notify sales.','no'); simRender(-1); return; }}
  // fair rotation: least-recently-served wins
  elig.sort(function(a,b){{ return SIM[a].served-SIM[b].served; }});
  var win=elig[0];
  SIM[win].credits-=1; SIM[win].served+=1;
  simLog('&#10003; Lead ['+svc+' / '+zip+'] &rarr; <b>'+SIM[win].name+'</b> (exclusive). 1 credit charged, '+SIM[win].credits+' left.','ok');
  simRender(win);
}}
function simReset(){{SIM=JSON.parse(JSON.stringify(SIM_SEED));document.getElementById('sim-log').innerHTML='';simRender(-1);}}
simRender(-1);
</script>"""
    return head(b,title,desc,"/pros/simulator/",jsonld)+header(b)+footer(b)+body

# ======================================================================
# PROGRAMMATIC: auto-generate a cost page for any service x city
# ======================================================================
def synth_cost_page(data, svc, city):
    """Build a templated cost-page dict for a city that has no explicit entry."""
    pf = data["price_finder"].get(svc["slug"], {})
    d  = svc.get("default", {})
    seg = d.get("segment", svc["name"])
    low, high, unit = pf.get("low"), pf.get("high"), pf.get("unit", "")
    return {
        "service": svc["slug"], "city": city["slug"], "segment": seg,
        "low": low, "high": high, "unit": unit,
        "confidence": "INSUFFICIENT", "observations": 0, "updated": "2026-08",
        "summary": f"{seg} in {city['name']}, TX. This range reflects Austin-area operators' published pricing while we gather {city['name']}-specific data — a solid starting point, not a firm local median yet.",
        "scope": d.get("scope", []),
        "questions": d.get("questions", []),
        "faqs": [
            {"q": f"How much does {seg.lower()} cost in {city['name']}?",
             "a": f"Expect roughly {money(low)}\u2013{money(high)} {unit} based on Austin-area operators' published rates. We're still building a {city['name']}-specific sample, so treat this as a starting range and confirm inclusions with each company."},
            {"q": f"Can I get a real {city['name']} quote?",
             "a": "Yes \u2014 see the fair range free, then get matched with one vetted local pro for a firm quote. No spam, no bidding war."},
        ],
        "_templated": True,
    }

# ======================================================================
# INDEXED TOOL: "Is my quote fair?" price checker (SEO landing page)
# ======================================================================
def check_quote_page(b, data):
    svcopts = "".join(f'<option value="{s["slug"]}">{esc(s["name"])}</option>' for s in data["services"])
    faqs = [
        ("How do I know if a home-service quote is fair in Austin?",
         "Compare it to what the same job costs locally \u2014 for the same scope, not just the headline number. Two quotes for 'pool resurfacing' can describe completely different work. Paste your quote and we'll show how it stacks up against Austin pricing and what to ask before you sign."),
        ("Is it free to check my quote?",
         "Yes. Checking your quote against local pricing is free. If you want a second-opinion quote from a vetted pro, that's your choice \u2014 we never blast your info to a pile of companies."),
        ("What should I do if my quote looks high?",
         "Don't assume it's a rip-off \u2014 a higher price can reflect a bigger scope or better materials. Ask what's included, what's excluded, and what the warranty is. We give you the exact questions to ask."),
    ]
    faq_ld = {"@context":"https://schema.org","@type":"FAQPage","mainEntity":[
        {"@type":"Question","name":q,"acceptedAnswer":{"@type":"Answer","text":a}} for q,a in faqs]}
    bc = _breadcrumb(b, [("Home","/"),("Check my quote","/check-my-quote/")])
    title = f"Is my quote fair? Austin home-service price checker — {b['name']}"
    desc = "Paste a home-service quote and see if it's fair for Austin. Free, independent price check against real local data \u2014 plus the questions to ask before you sign."
    faq_html = "".join(
        f'<details><summary>{esc(q)}</summary><div class="a">{esc(a)}</div></details>' for q,a in faqs)
    body = f"""
<div class="wrap"><div class="crumb"><a href="/">Home</a><span>/</span>Check my quote</div></div>
<section class="section" style="padding-top:26px"><div class="wrap">
  <p class="eyebrow">Free price check · {esc(b['metro'])}, {esc(b['state'])}</p>
  <h1 style="max-width:20ch">Is your quote fair? Find out in 30 seconds.</h1>
  <p class="lead">Already have a quote from a contractor? Paste it in. We'll compare it to real Austin pricing and tell you what to ask before you sign \u2014 free, independent, no spam.</p>

  <div class="finder" style="margin-top:22px">
    <span class="flabel">Check your quote against local pricing</span>
    <div class="frow"><select id="cq-svc" aria-label="Service"><option value="">Service…</option>{svcopts}</select>
      <input type="text" id="cq-zip" inputmode="numeric" maxlength="5" placeholder="ZIP"></div>
    <div class="frow" style="margin-top:8px"><input type="text" id="cq-amt" placeholder="What were you quoted? (e.g. $4,500)" style="flex:1"></div>
    <div class="frow" style="margin-top:8px"><input type="text" id="cq-scope" placeholder="What's the job / what's included?" style="flex:1"></div>
    <div class="frow" style="margin-top:8px"><input type="text" id="cq-contact" placeholder="Where do we send your verdict? (phone or email)" style="flex:1"></div>
    <button class="btn btn-primary" style="margin-top:10px" onclick="cqSubmit()">Check my quote &rarr;</button>
    <div class="cc-result" id="cq-result" style="margin-top:14px"></div>
    <p class="cc-consent">We compare your number to local pricing and send your verdict. We can connect you with one vetted pro for a second opinion \u2014 only if you ask.</p>
  </div>
</div></section>

<section class="section band"><div class="wrap">
  <h2>How the price check works</h2>
  <div class="faq" style="margin-top:16px">{faq_html}</div>
</div></section>

<script>
function cqSubmit(){{
  var svc=document.getElementById('cq-svc').value, zip=(document.getElementById('cq-zip').value||'').trim();
  var amt=document.getElementById('cq-amt').value, scope=document.getElementById('cq-scope').value, contact=document.getElementById('cq-contact').value;
  var out=document.getElementById('cq-result');
  if(!svc||!amt||!contact){{out.innerHTML="<p class='cc-hint'>Add the service, the quoted amount, and where to send your verdict.</p>";out.style.display='block';return;}}
  var payload={{service:svc,zip:zip,quote_amount:amt,quote_scope:scope,contact:contact,source:'check-my-quote'}};
  var ep=window.CC_ENDPOINT||'';
  if(!ep||ep.indexOf('REPLACE')===0){{
    out.innerHTML="<div class='cc-card'><div class='cc-done'>Quote submitted \\u2713</div><div class='cc-meta' style='margin-top:6px'>Demo mode \\u2014 wire CC_ENDPOINT to capture: "+JSON.stringify(payload)+"</div></div>";
    out.style.display='block';return;
  }}
  var f=document.createElement('form');f.method='POST';f.action=ep;for(var k in payload){{var i=document.createElement('input');i.type='hidden';i.name=k;i.value=payload[k]||'';f.appendChild(i);}}document.body.appendChild(f);f.submit();
}}
</script>"""
    return head(b,title,desc,"/check-my-quote/",[bc,faq_ld])+header(b)+body+cc_data_script(b,data)+footer(b)

# ======================================================================
# AUTHORING: in-browser "New blog post" builder (noindex studio tool)
# ======================================================================
def studio_new_post_page(b, data):
    title = f"New blog post — {b['name']} studio"
    body = """
<div class="wrap"><div class="crumb"><a href="/">Home</a><span>/</span>Studio</div></div>
<section class="section" style="padding-top:26px"><div class="wrap" style="max-width:820px">
  <p class="eyebrow">Studio · not indexed</p>
  <h1>New blog post</h1>
  <p class="lead">Fill in the fields, paste your content (Markdown or plain text), and download the ready-to-commit <code>.md</code> file. Drop it in <code>content/blog/</code>, push, and it's live.</p>

  <div class="finder" style="max-width:none;margin-top:18px">
    <div class="frow" style="display:block">
      <label class="flabel">Title (the H1 on the page)</label>
      <input type="text" id="b-title" placeholder="What should weekly pool service cost in Round Rock?" style="width:100%" oninput="bSlug()">
    </div>
    <div class="frow" style="display:block;margin-top:10px">
      <label class="flabel">Slug (URL)</label>
      <input type="text" id="b-slug" placeholder="weekly-pool-service-cost-round-rock" style="width:100%">
    </div>
    <div class="frow" style="display:block;margin-top:10px">
      <label class="flabel">Meta title (SEO &lt;title&gt; — leave blank to use the title)</label>
      <input type="text" id="b-metatitle" placeholder="Weekly Pool Service Cost in Round Rock (2026) — CasaCost" style="width:100%">
    </div>
    <div class="frow" style="display:block;margin-top:10px">
      <label class="flabel">Meta description (155 chars)</label>
      <input type="text" id="b-desc" placeholder="What weekly pool service really costs in Round Rock, TX — real local ranges and what to ask." style="width:100%" maxlength="160">
    </div>
    <div class="frow" style="margin-top:10px">
      <div style="flex:1"><label class="flabel">Date</label><input type="text" id="b-date" placeholder="2026-08-10" style="width:100%"></div>
      <div style="flex:1"><label class="flabel">Tags (comma-separated)</label><input type="text" id="b-tags" placeholder="pool, round rock, pricing" style="width:100%"></div>
    </div>
    <div class="frow" style="display:block;margin-top:10px">
      <label class="flabel">Content (Markdown or plain text)</label>
      <textarea id="b-body" rows="12" placeholder="## The standard scope&#10;&#10;Write your post here in Markdown…" style="width:100%;font-family:var(--mono);font-size:13px;border:1.5px solid var(--limestone-line);border-radius:10px;padding:12px"></textarea>
    </div>
    <div class="frow" style="margin-top:12px">
      <button class="btn btn-primary" onclick="bMake()">Generate & download .md &rarr;</button>
      <button class="btn btn-ghost" onclick="bCopy()">Copy to clipboard</button>
    </div>
    <div id="b-out" style="display:none;margin-top:14px">
      <label class="flabel">Preview of your file</label>
      <pre id="b-pre" style="background:var(--ink);color:#CFE0D5;border-radius:10px;padding:14px;overflow:auto;font-family:var(--mono);font-size:12px;white-space:pre-wrap"></pre>
    </div>
  </div>
  <p class="pilot-note" style="margin-top:12px">Local tool — nothing is uploaded from here. For one-click publishing from Google Docs, see <code>tools/gdocs-publish.gs</code>.</p>
</div></section>

<script>
function bSlugify(s){return s.toLowerCase().replace(/['\"]/g,'').replace(/[^a-z0-9]+/g,'-').replace(/^-+|-+$/g,'');}
function bSlug(){var t=document.getElementById('b-title').value;var s=document.getElementById('b-slug');if(!s.dataset.touched)s.value=bSlugify(t);}
document.addEventListener('input',function(e){if(e.target.id==='b-slug')e.target.dataset.touched='1';});
function bFile(){
  var v=function(id){return (document.getElementById(id).value||'').trim();};
  var date=v('b-date')||new Date().toISOString().slice(0,10);
  var slug=v('b-slug')||bSlugify(v('b-title'));
  var fm='---\\n'+
    'title: '+v('b-title')+'\\n'+
    'slug: '+slug+'\\n'+
    (v('b-metatitle')?'meta_title: '+v('b-metatitle')+'\\n':'')+
    'description: '+v('b-desc')+'\\n'+
    'date: '+date+'\\n'+
    'author: '+'CasaCost'+'\\n'+
    (v('b-tags')?'tags: '+v('b-tags')+'\\n':'')+
    '---\\n\\n'+ document.getElementById('b-body').value.trim()+'\\n';
  return {name:date+'-'+slug+'.md', text:fm};
}
function bMake(){var f=bFile();document.getElementById('b-pre').textContent=f.text;document.getElementById('b-out').style.display='block';
  var blob=new Blob([f.text],{type:'text/markdown'});var a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=f.name;a.click();}
function bCopy(){var f=bFile();navigator.clipboard.writeText(f.text).then(function(){alert('Copied '+f.name+' to clipboard.');});document.getElementById('b-pre').textContent=f.text;document.getElementById('b-out').style.display='block';}
</script>"""
    return head(b,title,"Internal authoring tool.","/studio/new-post/",[],robots="noindex,nofollow")+header(b)+body+footer(b)

# ======================================================================
# VENDOR pages: directory + per-vendor profile (signup incentive + branded capture)
# ======================================================================
def _svc_name(data, slug):
    for s in data["services"]:
        if s["slug"]==slug: return s["name"]
    return slug.replace("-"," ").title()

def vendor_profile(b, data, v):
    path=f"/pro/{v['slug']}/"
    verts=", ".join(_svc_name(data,x) for x in v.get("verticals",[]))
    areas=", ".join(v.get("areas",[]))
    specs="".join(f"<li>{esc(x)}</li>" for x in v.get("specialties",[]))
    ld={"@context":"https://schema.org","@type":"LocalBusiness","name":v["name"],
        "description":v.get("blurb",""),"areaServed":[{"@type":"City","name":a} for a in v.get("areas",[])],
        "url":v.get("url","") or None}
    if v.get("phone"): ld["telephone"]=v["phone"]
    ld={k:val for k,val in ld.items() if val is not None}
    bc=_breadcrumb(b,[("Home","/"),("Find a pro","/find-a-pro/"),(v["name"],path)])
    sponsored = v.get("sponsored")
    badge = '<span class="v-badge sponsored">Sponsored</span>' if sponsored else '<span class="v-badge">Listed vendor</span>'
    site_btn = (f'<a class="btn btn-pine" href="{esc(v["url"])}" rel="nofollow noopener" target="_blank">Visit {esc(v["name"])} website &rarr;</a>'
                if v.get("url") else "")
    title=f"{v['name']} — {verts} in Austin | {b['name']}"
    desc=f"{v['name']}: {v.get('blurb','')[:120]}"
    body=f"""
<div class="wrap"><div class="crumb"><a href="/">Home</a><span>/</span><a href="/find-a-pro/">Find a pro</a><span>/</span>{esc(v['name'])}</div></div>
<section class="section" style="padding-top:26px"><div class="wrap" style="max-width:820px">
  <p class="eyebrow">{esc(verts)} · Austin, TX {badge}</p>
  <h1 style="max-width:22ch">{esc(v['name'])}</h1>
  <p class="lead">{esc(v.get('blurb',''))}</p>

  <div class="two-col" style="margin-top:8px">
    <div class="block">
      <h2>Specialties</h2>
      <ul class="scope-list">{specs}</ul>
      <h2 style="margin-top:26px">Get matched with {esc(v['name'])}</h2>
      <p style="color:var(--ink-soft);font-size:15px">Want this pro for your job? Get a fair local range first, then request them directly.</p>
      <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:8px">
        <a class="btn btn-primary" href="/find-prices/">Get matched &rarr;</a>
        {site_btn}
      </div>
    </div>
    <aside class="aside">
      <h3>At a glance</h3>
      <p><b>Services:</b> {esc(verts)}<br>
         <b>Serves:</b> {esc(areas)}<br>
         {("<b>Since:</b> "+esc(v['founded'])) if v.get('founded') else ""}</p>
      <p style="margin-top:10px;font-size:12px;color:var(--ink-faint)">Listing on {esc(b['name'])} is not an endorsement or a quality ranking. {"This is a sponsored placement." if sponsored else ""}</p>
    </aside>
  </div>
</div></section>"""
    return head(b,title,desc,path,[bc,ld])+header(b)+body+footer(b)

def directory_page(b, data):
    provs=data.get("providers",[])
    by={}
    for v in provs:
        for vert in v.get("verticals",["other"]):
            by.setdefault(vert,[]).append(v)
    sections=""
    for s in data["services"]:
        vs=by.get(s["slug"],[])
        if not vs: continue
        rows="".join(
            f"""<a class="list-row" href="/pro/{v['slug']}/">
                  <div><div class="lr-t">{esc(v['name'])}{' · Sponsored' if v.get('sponsored') else ''}</div>
                  <div class="lr-s">{esc(', '.join(v.get('areas',[])))}</div></div>
                  <div class="lr-p"><span class="lr-c">{esc(', '.join(v.get('specialties',[])[:2]))}</span></div>
                </a>""" for v in vs)
        sections+=f'<h2 style="margin-top:26px">{esc(s["name"])}</h2><div class="list-grid">{rows}</div>'
    if not sections:
        sections='<p class="lead">No vendors listed yet.</p>'
    jsonld=[_breadcrumb(b,[("Home","/"),("Find a pro","/find-a-pro/")])]
    title=f"Find a vetted Austin home-service pro — {b['name']}"
    desc="Browse vetted Austin home-service pros by category and area, then get matched with one — no spam, no bidding war."
    body=f"""
<div class="wrap"><div class="crumb"><a href="/">Home</a><span>/</span>Find a pro</div></div>
<section class="section" style="padding-top:26px"><div class="wrap">
  <p class="eyebrow">Directory · {esc(b['metro'])}, {esc(b['state'])}</p>
  <h1 style="max-width:20ch">Find a vetted Austin pro</h1>
  <p class="lead">Browse pros by service and area. Every match is exclusive — one pro, no bidding war. Listings aren't rankings; sponsored placements are labeled.</p>
  {sections}
</div></section>
<section class="section band"><div class="wrap" style="text-align:center">
  <h2 style="margin:0 auto">Run a home-service business?</h2>
  <p class="lead" style="margin:12px auto 20px">Get your own profile page, a link back to your site, and exclusive local leads.</p>
  <a class="btn btn-primary" href="/for-pros/">List your business &rarr;</a>
</div></section>"""
    return head(b,title,desc,"/find-a-pro/",jsonld)+header(b)+body+footer(b)

# ======================================================================
# POOL PROJECT pages (high-value head terms: remodeling/resurfacing/repair/leak)
# ======================================================================
def project_page(b, data, proj):
    city_by={c["slug"]:c for c in data["cities"]}
    city=city_by.get(proj["city"], {"name":b["metro"],"state":b["state"]})
    path=f"/pool-service/{proj['city']}/{proj['slug']}/"
    conf=conf_class(proj["confidence"])
    drivers="".join(f"<li>{esc(x)}</li>" for x in proj.get("cost_drivers",[]))
    qs="".join(f"<li>{esc(x)}</li>" for x in proj.get("questions",[]))
    options=""
    if proj.get("options"):
        rows="".join(f'<div class="opt"><b>{esc(n)}</b><span>{esc(note)}</span></div>' for n,note in proj["options"])
        options=f'<h2 style="margin-top:30px">Your options</h2><div class="opts">{rows}</div>'
    signs=""
    if proj.get("signs"):
        items="".join(f"<li>{esc(x)}</li>" for x in proj["signs"])
        signs=f'<h2 style="margin-top:30px">Signs you need this</h2><ul class="scope-list">{items}</ul>'
    faqs="".join(f'<details><summary>{esc(q)}</summary><div class="a">{esc(a)}</div></details>'
                 for q,a in proj.get("faqs",[]))
    faq_ld={"@context":"https://schema.org","@type":"FAQPage","mainEntity":[
        {"@type":"Question","name":q,"acceptedAnswer":{"@type":"Answer","text":a}} for q,a in proj.get("faqs",[])]}
    svc_ld={"@context":"https://schema.org","@type":"Service","serviceType":proj["name"],
            "areaServed":{"@type":"City","name":city["name"]},
            "provider":{"@type":"Organization","name":b["name"]}}
    bc=_breadcrumb(b,[("Home","/"),("Pool Service","/pool-service/"),(proj["name"],path)])
    # related links
    pj_by={p["slug"]:p for p in data.get("pool_projects",[])}
    rel="".join(
        f'<a class="list-row" href="/pool-service/{pj_by[r]["city"]}/{r}/"><div><div class="lr-t">{esc(pj_by[r]["name"])}</div></div><div class="lr-p"><span class="lr-c">see costs</span></div></a>'
        for r in proj.get("related",[]) if r in pj_by)
    related_block=f'<h2 style="margin-top:34px">Related pool projects</h2><div class="list-grid">{rel}</div>' if rel else ""
    title=f"{proj['name']} in {city['name']}, TX — Cost, Options & What to Ask | {b['name']}"
    desc=f"{proj['name']} in {city['name']}: fair local cost range, what drives the price, and the questions to ask before you sign."
    meter='<span class="m"></span><span class="m"></span><span class="m"></span>'
    body=f"""
<div class="wrap"><div class="crumb"><a href="/">Home</a><span>/</span><a href="/pool-service/">Pool Service</a><span>/</span>{esc(proj['name'])}</div></div>
<section class="cost-head"><div class="wrap">
  <p class="eyebrow">{esc(city['name'])}, {esc(city['state'])} · {esc(proj['updated'])}</p>
  <h1>{esc(proj['name'])} in {esc(city['name'])}, {esc(city['state'])}</h1>
  <p class="summary">{esc(proj['intro'])}</p>

  <div class="pc {conf}">
    <div class="pc-label">Fair local range</div>
    <div class="range">{money(proj['low'])}–{money(proj['high'])}<span class="unit">{esc(proj['unit'])}</span></div>
    <div class="pc-meter-wrap">
      <div class="pc-meter">{meter}</div>
      <span class="conf-tag">PRICE CONFIDENCE: {esc(proj['confidence'])}</span>
      <span class="obs">{proj['observations']} local observations · updated {esc(proj['updated'])}</span>
    </div>
  </div>

  <div class="cta-inline">
    <div><h3>Got a {esc(proj['name'].lower())} quote?</h3>
      <p>Paste it in and we'll show how it compares to local pricing — and what to ask before you sign.</p></div>
    <div class="acts">
      <a class="btn btn-primary" href="/check-my-quote/">Check my quote</a>
      <a class="btn btn-ghost" href="/find-prices/">Get matched</a>
    </div>
  </div>
</div></section>

<section class="section" style="padding-top:8px"><div class="wrap">
  <div class="block">
    <h2>What drives the cost</h2>
    <ul class="scope-list">{drivers}</ul>
    {options}
    {signs}
    <h2 style="margin-top:30px">Questions to ask before you hire</h2>
    <ul class="q-list">{qs}</ul>
  </div>

  <div class="faq" style="margin-top:34px"><h2>Common questions</h2>{faqs}</div>
  {related_block}
  <div class="method-note" style="margin-top:24px"><b>How we price.</b> {esc(data['methodology'])}</div>
</div></section>"""
    return head(b,title,desc,path,[bc,svc_ld,faq_ld])+header(b)+body+footer(b)

def build(inline=False):
    data=load(); b=data["brand"]
    if os.path.isdir(SITE): shutil.rmtree(SITE)
    os.makedirs(SITE)
    # assets
    shutil.copytree(ASSETS_SRC, os.path.join(SITE,"assets"))

    urls=["/"]
    write("/", home(b,data))

    svc_by={s["slug"]:s for s in data["services"]}
    city_by={c["slug"]:c for c in data["cities"]}

    for s in data["services"]:
        p="/{}/".format(s["slug"]); urls.append(p)
        write(p, service_hub(b,data,s))

    # explicit cost pages
    explicit=set()
    for cp in data["cost_pages"]:
        s=svc_by[cp["service"]]; c=city_by[cp["city"]]
        path=f"/{s['slug']}/{c['slug']}/{slugify(cp['segment'])}/"
        explicit.add((cp["service"], cp["city"]))
        urls.append(path)
        write(path, cost_page(b,data,cp,s,c))

    # PROGRAMMATIC: templated cost page for every service x city not covered above
    for s in data["services"]:
        if s["slug"] not in data["price_finder"]:
            continue
        for c in data["cities"]:
            if (s["slug"], c["slug"]) in explicit:
                continue
            cp=synth_cost_page(data,s,c)
            path=f"/{s['slug']}/{c['slug']}/{slugify(cp['segment'])}/"
            urls.append(path)
            write(path, cost_page(b,data,cp,s,c))

    urls.append("/texas-price-index/")
    write("/texas-price-index/", price_index(b,data))

    # pool project pages (high-value head terms)
    for proj in data.get("pool_projects", []):
        pp=f"/pool-service/{proj['city']}/{proj['slug']}/"
        urls.append(pp); write(pp, project_page(b,data,proj))

    # consumer finder + quote checker + provider onboarding + routing demo + studio
    urls.append("/find-prices/");    write("/find-prices/", find_prices_page(b,data))
    urls.append("/check-my-quote/"); write("/check-my-quote/", check_quote_page(b,data))
    urls.append("/for-pros/");       write("/for-pros/", for_pros_page(b,data))
    urls.append("/pros/simulator/"); write("/pros/simulator/", simulator_page(b,data))
    write("/studio/new-post/", studio_new_post_page(b,data))  # noindex: not in sitemap

    # vendor directory + per-vendor profile pages
    if data.get("providers"):
        urls.append("/find-a-pro/"); write("/find-a-pro/", directory_page(b,data))
        for v in data["providers"]:
            vp=f"/pro/{v['slug']}/"; urls.append(vp); write(vp, vendor_profile(b,data,v))

    # blog
    posts = load_posts()
    urls.append("/blog/")
    write("/blog/", blog_index(b, posts))
    for p in posts:
        bp = "/blog/{}/".format(p["slug"])
        urls.append(bp)
        write(bp, blog_post(b, p))

    # sitemap + robots
    today=datetime.date.today().isoformat()
    sm=['<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        sm.append(f"<url><loc>https://{b['domain']}{u}</loc><lastmod>{today}</lastmod></url>")
    sm.append("</urlset>")
    write("/sitemap.xml","\n".join(sm))
    write("/robots.txt",
          f"User-agent: *\nAllow: /\n\n# AI answer engines welcome\nUser-agent: GPTBot\nAllow: /\nUser-agent: PerplexityBot\nAllow: /\nUser-agent: Google-Extended\nAllow: /\n\nSitemap: https://{b['domain']}/sitemap.xml\n")

    # GitHub Pages: custom domain + disable Jekyll (flat root files, not folders)
    with open(os.path.join(SITE, "CNAME"), "w", encoding="utf-8") as _f: _f.write(b["domain"] + "\n")
    open(os.path.join(SITE, ".nojekyll"), "w").close()

    if inline:
        _inline_previews(b,data,svc_by,city_by)

    print(f"Built {len(urls)} pages -> {SITE}")
    for u in urls: print("  ", u)

def _inline_previews(b,data,svc_by,city_by):
    """Self-contained copies (CSS inlined) for quick viewing without a server."""
    with open(os.path.join(ASSETS_SRC,"styles.css"),encoding="utf-8") as f:
        css=f.read()
    def inline(htmlstr):
        htmlstr=htmlstr.replace('<link rel="stylesheet" href="/assets/styles.css">',
                                f"<style>{css}</style>")
        # make root-relative links harmless in a file preview
        return htmlstr
    prev=os.path.join(ROOT,"preview")
    os.makedirs(prev,exist_ok=True)
    with open(os.path.join(prev,"home.html"),"w",encoding="utf-8") as f:
        f.write(inline(home(b,data)))
    cp=data["cost_pages"][0]; s=svc_by[cp["service"]]; c=city_by[cp["city"]]
    with open(os.path.join(prev,"cost-page.html"),"w",encoding="utf-8") as f:
        f.write(inline(cost_page(b,data,cp,s,c)))
    with open(os.path.join(prev,"find-prices.html"),"w",encoding="utf-8") as f:
        f.write(inline(find_prices_page(b,data)))
    with open(os.path.join(prev,"for-pros.html"),"w",encoding="utf-8") as f:
        f.write(inline(for_pros_page(b,data)))
    with open(os.path.join(prev,"routing-simulator.html"),"w",encoding="utf-8") as f:
        f.write(inline(simulator_page(b,data)))
    print("Inlined previews ->", prev)

if __name__=="__main__":
    build(inline="--inline" in sys.argv)
