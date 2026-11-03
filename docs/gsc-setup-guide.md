# Search Console report tool — one-time setup

`tools/gsc_report.py` reads your Search Console data via the API. It runs on
your machine only; nothing ships to production. Two auth options.

## Option A — Service account (recommended, never expires)

1. https://console.cloud.google.com/ -> create (or pick) a project.
2. APIs & Services -> Library -> enable **Search Console API**.
3. IAM & Admin -> Service Accounts -> Create service account (no roles needed).
4. Open the account -> Keys -> Add key -> JSON -> save as
   `tools/gsc_service_account.json` (this path is gitignored).
5. Search Console (https://search.google.com/search-console) -> Settings ->
   Users and permissions -> Add user -> paste the service account email
   (ends in `.iam.gserviceaccount.com`) -> permission **Owner** (required for
   full data).
6. Install local deps once: `venv/bin/python -m pip install -r requirements-search-console.txt`
7. Run: `venv/bin/python tools/gsc_report.py --days 90`

## Option B — OAuth (fallback)

Refresh tokens for OAuth apps in "Testing" mode expire after 7 days; prefer
Option A. If you need OAuth:

1. Same GCP project -> APIs & Services -> OAuth consent screen (External,
   Testing) -> add yourself as test user.
2. Credentials -> Create credentials -> OAuth client ID -> Desktop app ->
   download JSON to `tools/gsc_client_secret.json` (gitignored).
3. Run `venv/bin/python tools/gsc_report.py --oauth` and follow the browser
   consent. The token caches at `~/.config/regalame/gsc_token.json`.

## Notes

- `--site` defaults to `https://regalame.app/`. If your property is a
  **domain** property, pass `--site sc-domain:regalame.app`. Check the
  property card in Search Console to see which one you have.
- Reports print to stdout; use `--out tools/reports/gsc-YYYY-MM-DD.md` to
  save (gitignored).
- `--country` takes ISO 3166-1 alpha-3 codes as the API returns them (`esp` for
  Spain, `arg` for Argentina); the default is `esp`. Omit the filter entirely is
  not supported — pass the code you care about.
