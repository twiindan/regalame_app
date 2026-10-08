# Export private Search Console analytics locally

This isolated CLI exports final query/page analytics for **`sc-domain:regalame.app`**.
It does not integrate with the application, discover credentials, or change production dependencies.
Implementation checks are not proof of real consent or Search Console access; T2 records that separately.

## Quick path

1. Install only into the local development environment:

   ```bash
   venv/bin/python -m pip install -r requirements-search-console.txt
   venv/bin/python -m jobs.search_console --help
   ```

2. Use the explicitly selected Google **desktop** client. All three paths must be
   absolute, distinct, outside the repository, and free of symlink components.
   Existing parent directories must be owned by the current user with mode `0700`;
   existing files must be regular, owned by the current user, mode `0600`, and not hardlinked.
   A missing final parent directory is created with `0700` if its parent exists.
   Writable ancestors are rejected except root-owned sticky temporary directories.
   Do not discover another client or silently change an authorized destination.

3. After the implementation checks and authorized-runtime gates, run this template
   in a private local terminal. Substitute the selected client privately; never put
   its actual filename in shared logs, repository artifacts, or recorded evidence.

   ```bash
   venv/bin/python -m jobs.search_console \
     --client-secret "<OAUTH_DESKTOP_CLIENT_JSON>" \
     --token "<PRIVATE_EXTERNAL_DIRECTORY>/search-console-token.json" \
     --output "<PRIVATE_EXTERNAL_DIRECTORY>/search-console-export.json" \
     --property "sc-domain:regalame.app"
   ```

The first run opens the default browser for consent, listens only on `127.0.0.1`
with an ephemeral port, and waits up to 180 seconds for the callback. Authorization
URLs are not printed. Official-library state validation and S256 PKCE remain enabled.
Only `webmasters.readonly` is requested. The scope is account-wide, not property-scoped;
the CLI rejects any property other than the exact one above.

## Repeat runs and failures

- Repeat the same command to reuse the private token, refreshing when necessary.
- An unusable or revoked session does not silently open the browser. Rerun with
  `--reauthorize` when ready for consent; the token is replaced only after success.
  This replaces local state, not the existing Google grant; revocation is separate.
- The CLI prints only a generic success or sanitized error, never rows or filenames.
  Exit status is `0` on success, `1` on export failure, `2` for invalid CLI syntax.
- OAuth exchange, refresh, and API requests have 30-second network timeouts.
  Requests do not follow redirects or use ambient `.netrc` credentials/proxies.
  HTTP timeouts bound connect/read inactivity, not the entire export's wall-clock duration.
- Check private-path permissions and the authorized account's exact-property access
  before retrying. Do not enable HTTP/debug logging or publish private export contents.
- JSON writes use a private temporary file, flush/fsync, and atomic replacement.
  Existing exports remain untouched when querying fails. This is a single-user CLI;
  do not run concurrent writers against the same token/output paths.

## Interpret the export correctly

The date range is **90 inclusive calendar days ending yesterday in America/Los_Angeles**.
The export is a combined full-property baseline with five independent sections:

- `totals` — site-wide totals, no dimensions.
- `byDate` — dimension `date`.
- `topPages` — dimension `page`.
- `topQueries` — dimension `query`.
- `queryPage` — dimensions `query` and `page`.

Each section is its own query, issued in that order, and all of them share the same
`startDate`, `endDate`, `type=web`, and `dataState=final`, so the sections are
directly comparable. Every section paginates independently: it advances `startRow`
with `rowLimit=25000` and stops on a short/empty page. The JSON records the section
dimensions under `section_dimensions`, the rows under `sections`, plus the exact
property, dates, settings, timezone, and limitations.

Search Analytics returns **top rows, not guaranteed exhaustive data**. Anonymized
queries are omitted for privacy, and recent final days can be absent due to reporting
latency. Pagination does not remove those limits. An empty successful export is
not evidence of an authentication failure.

## Verification and rollback

```bash
venv/bin/python -m pytest -q tests/test_search_console.py
venv/bin/python -m pytest -q --ignore=tests/test_e2e.py
```

Tests use only synthetic files, fake OAuth/API boundaries, and an offline state/PKCE
check. No browser, real credentials, or Google authentication is used in tests.
Remove the CLI, its tests, isolated requirements, this guide, and feature-specific
ignore rules to roll back repository behavior. Private files and grant revocation
require separate explicit authorization; never delete them as repository cleanup.

References: [OAuth library](https://github.com/googleapis/google-auth-library-python-oauthlib),
[Search Analytics query](https://developers.google.com/webmaster-tools/v1/searchanalytics/query).
