# Deploying CasaCost to GitHub Pages (custom domain: casacost.com)

The site is static and served from the **root** of `casacost.com`, so no path changes
are needed. GitHub Actions rebuilds and publishes on every push.

## One-time setup

### 1. Push the repo
Commit the **source** (you don't commit `site/` — the action builds it):
```
build.py  content.json  assets/  content/blog/  data-kit/  .github/  DEPLOY.md  README.md
```
Push to the `main` branch of a new GitHub repo (any name — the custom domain makes the
repo name irrelevant to your URLs).

### 2. Turn on Pages via Actions
Repo → **Settings → Pages → Build and deployment → Source: GitHub Actions**.
The included workflow (`.github/workflows/deploy.yml`) will run `python3 build.py` and
deploy the `site/` folder. Watch it under the **Actions** tab.

### 3. Point the domain at GitHub
At your DNS registrar for `casacost.com`, add:

| Type  | Host | Value |
|-------|------|-------|
| A     | @    | 185.199.108.153 |
| A     | @    | 185.199.109.153 |
| A     | @    | 185.199.110.153 |
| A     | @    | 185.199.111.153 |
| CNAME | www  | `YOUR-USERNAME.github.io` |

(The four A records are GitHub Pages' current IPs. AAAA/IPv6 records are optional.)

### 4. Set the custom domain in the repo
Repo → **Settings → Pages → Custom domain** → enter `casacost.com` → Save.
Then check **Enforce HTTPS** (it may take a few minutes for the certificate to provision).

The build already writes a `CNAME` file (`casacost.com`) and a `.nojekyll` file into
`site/` automatically, so GitHub serves the domain correctly and doesn't run Jekyll.

## Day-to-day

- **Publish a blog post:** add a markdown file to `content/blog/`, commit, push. The site
  rebuilds and deploys itself in ~1 minute.
- **Update pricing / add a cost page:** edit `content.json`, commit, push.
- **Change the brand or domain:** edit `brand` in `content.json`. If you ever move off
  `casacost.com`, update `brand.domain` so canonicals, sitemap, and the CNAME follow.

## The one thing GitHub Pages can't do: forms

Pages is static-only, so the three-door capture and the pro signup won't persist until you
point them at a form backend. Set `brand.form_endpoint` in `content.json` to one of:
- **Formspree** — paste your form URL; works instantly with the existing forms.
- **A serverless function** (Cloudflare Workers / Netlify Functions) if you want custom logic.

Until then the forms run in demo mode (they show the payload they *would* send).

> Note: real lead **routing**, **paid credits**, and **accounts** still need the Supabase +
> Stripe backend we scoped — that's independent of where the front end is hosted.

## Alternative hosts (optional)

If you'd rather not manage the backend gap separately, **Netlify** or **Cloudflare Pages**
host this identically (point them at the repo, build command `python3 build.py`, publish
dir `site`) and Netlify includes free form handling that closes the capture gap in one step.
