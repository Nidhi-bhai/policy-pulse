# PolicyPulse

PolicyPulse turns public Indian government notices into a short business brief for MSMEs, traders, exporters, and investors. Each brief says what the official text says, which sector keywords matched, and what to read before you act. It always links the source. It does not invent rates, deadlines, or legal effects.

The site is static HTML in `docs/`. A daily GitHub Actions job refreshes the archive.

## What it reads

| Source | Public page |
| --- | --- |
| PIB | [English press releases](https://www.pib.gov.in/allRel.aspx?reg=3&lang=1) and the [press-release RSS](https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3) |
| RBI | [Press releases](https://rbi.org.in/pressreleases_rss.xml) and [notifications](https://rbi.org.in/notifications_rss.xml) |
| SEBI | [RSS](https://www.sebi.gov.in/sebirss.xml) and the [circulars listing](https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=1&ssid=7&smid=0) |
| CBIC / GST | [GST portal tickers](https://cbic-gst.gov.in/tickers.html) |
| DGFT | [Trade notices](https://www.dgft.gov.in/CP/?opt=trade-notice), [notifications](https://www.dgft.gov.in/CP/?opt=notification), [public notices](https://www.dgft.gov.in/CP/?opt=public-notice) |
| Gazette | [eGazette homepage](https://egazette.gov.in/) recent extraordinary and weekly issues |

Items are stored in `data/items.json` with the source URL and date. `data/archive/YYYY-MM.json` keeps a growing month-by-month history. A later run merges by id and does not drop older items.

## Pages

- Latest feed, plus sector pages for exports, agriculture, MSME, banking, GST, pharma, and startups
- One SEO page per notice
- `feed.xml` and `sitemap.xml`
- Free daily digest signup (mailto placeholder, or a Google Form / Formspree URL)
- Pro weekly sector brief at $9/month via PayPal

## Run it locally

Python 3.11 or newer. No third-party packages.

```bash
python scripts/ingest.py
python scripts/build_site.py
python -m unittest discover -s tests
```

Open `docs/index.html`.

## PayPal and the digest

`docs/config.js` (seeded from `web/config.js`) holds public placeholders:

- `PAYPAL_CLIENT_ID`
- `PLAN_ID` for a $9/month subscription plan
- `DIGEST_FORM_ACTION` for a static form endpoint
- `DIGEST_MAILTO` for the mail-draft fallback

Do not commit secrets. The checkout button stays off until the PayPal values are filled in.

## Optional model notes

Set the repository secret `POLICYPULSE_LLM_API_KEY` if you want a model note on new items. Optional companions: `POLICYPULSE_LLM_BASE_URL`, `POLICYPULSE_LLM_MODEL`, `POLICYPULSE_LLM_MAX`. The ingest and the site both work with the secret unset. A model note is discarded when it introduces a number that was not in the source text.

## GitHub Pages

The workflow `.github/workflows/daily-ingest.yml` runs every day at 02:20 UTC, commits the archive, and deploys `docs/` with GitHub Pages. Enable Pages with **GitHub Actions** as the source (Settings → Pages). The project URL is:

https://nidhi-bhai.github.io/policy-pulse/

## Who built it

Built by [Nidhi Karuturi](https://github.com/Nidhi-bhai).
