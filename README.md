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

Items are stored in `data/items.json` with the source URL and date. `data/archive/YYYY-MM.json` keeps a growing month-by-month history. A later run merges by id and does not drop older items. The public feed updates daily. The archive includes a 2023–26 backfill, and each notice is labeled with the date on the official document.

DGFT listings are fetched with a browser User-Agent, a homepage cookie, retries, fallback URLs, and a curl retry when Python is refused. If every endpoint fails, the run keeps the DGFT rows already in the archive and logs that. The Sources page shows the latest ingest result.

## Pages

- Latest feed, plus sector pages for exports, agriculture, MSME, banking, GST, pharma, and startups
- One SEO page per notice
- `feed.xml` and `sitemap.xml`
- Free daily digest signup. The form opens a mail draft to nidhi69n@gmail.com. It is hidden if that address is missing. A `DIGEST_FORM_ACTION` URL posts the form instead.
- Pro is a one-time $9 PayPal payment for a link to the unlisted weekly Pro brief page, updated every Monday; no renewal, no account. The link is left out of the sitemap, disallowed in robots.txt, and marked noindex. After payment the browser stores the link and the PayPal order id.

## Run it locally

Python 3.11 or newer. No third-party packages.

```bash
python scripts/ingest.py
python scripts/build_site.py
python -m unittest discover -s tests
```

Open `docs/index.html`.

## PayPal and the digest

`docs/config.js` holds the public PayPal client id. The button captures a one-time $9 order. The PayPal secret stays out of the repository. There is no plan id.

- `PAYPAL_CLIENT_ID` turns on the $9 PayPal button
- `DIGEST_MAILTO` is `mailto:nidhi69n@gmail.com?subject=PolicyPulse%20digest`
- `DIGEST_FORM_ACTION` is an optional static form endpoint for the daily digest
- `PRO_BRIEF_PATH` is the unlisted weekly brief, shown after PayPal captures the order

The brief slug lives in `web/pro-slug.txt`. Set the repository secret `POLICYPULSE_PRO_SLUG` only when a build should publish a different path. The next archive commit will contain that path, because GitHub Pages serves the files in `docs/`.

## Optional model notes

Set the repository secret `POLICYPULSE_LLM_API_KEY` if you want a model note on new items. Optional companions: `POLICYPULSE_LLM_BASE_URL`, `POLICYPULSE_LLM_MODEL`, `POLICYPULSE_LLM_MAX`. The ingest and the site both work with the secret unset. A model note is discarded when it introduces a number that was not in the source text.

## GitHub Pages

The workflow `.github/workflows/daily-ingest.yml` runs every day at 02:20 UTC, commits the archive, and rebuilds `docs/`. GitHub Pages publishes that folder from `main`. The project URL is:

https://nidhi-bhai.github.io/policy-pulse/

## Who built it

Built by [Nidhi Karuturi](https://github.com/Nidhi-bhai).
