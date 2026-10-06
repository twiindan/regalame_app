# SEO dual landings — approved implementation tasks

## Objective and problem
Align the evergreen homepage with wishlists and add a permanent organizer landing.
The homepage currently mixes a Secret Santa title with a wishlist H1; shared metadata
uses homepage social URLs and unsupported rating/AI claims. Separate intent honestly.
Prior SEO evidence is a limited 12-row homepage export: 148 impressions, one click;
it is not site-wide performance evidence and cannot support ranking guarantees.

## Authorized implementation boundary
- Worktree: `/Users/toni.robres/Pycharmprojects/regalame_gemini3-worktrees/seo-dual-landings`.
- Branch: `feature/seo-dual-landings`; base: `438c97c574fa62d34d04c85683fcc1ebb8e1221f`.
- Preparation-only scope is superseded by explicit T1/T2 implementation and local work-unit commit authorization.
- Single writer; no new review gates, remote work, credential/session inspection or child agents.
- Preserve the original OAuth checkout/index, six dirty paths and untracked `sample.json`.
- Do not initialize, copy or symlink CodeGraph indexes or virtual environments.

## Accepted design and constraints
- `/`: wishlist-first title, description, H1, benefits and contextual organizer link.
- Preserve login/register forms and signed-in `303 /dashboard` behavior (`main.py:149–153`).
- `/amigo-invisible`: permanent public page, readable anonymously and signed in, no auth gate.
- Use `templates/amigo_invisible.html`; link to wishlists and relevant Christmas guidance.
- Add a related organizer link in `templates/blog_post.html` only for
  `regalos-amigo-invisible-10-euros` (existing slug in `blog_config.py`).
- Honest organizer copy: admin creates a group with date and descriptive budget;
  WhatsApp shares an invitation link; email invitations depend on Resend configuration.
- Participants need accounts; admin triggers a draw with at least two participants;
  self-assignment is excluded, additional exclusions can make a draw impossible.
- Results are not delivered through WhatsApp/email; public wishlists allow anonymous
  viewing, while reservations require login.
- No guaranteed chat privacy, universal store-link support, unsupported AI or free-forever promises.
- No draw/chat/catalog fixes, profile sitemap policy changes, or new dependencies.
- UI copy stays neutral Spanish; technical documentation stays English; Jinja2/HTMX only.

## Tasks and acceptance
- [ ] **T1 — Honest wishlist and organizer landings.** Update `templates/index.html`,
  add the public route in `main.py` and new template, and add scoped contextual links.
  Add `tests/test_seo_landings.py` covering distinct titles/descriptions/H1s, truthful
  capability copy, anonymous/signed-in organizer access, homepage redirect/forms,
  reciprocal links, and presence/absence of the blog link by slug.
  Implementation and functional checks complete; delivery checkbox remains open pending work-unit commit.
- [ ] **T2 — Explicit page identity and trustworthy shared metadata.** Add opt-in absolute
  self-canonical context for the two landings only; align their canonical, `og:url`
  and `twitter:url` using normalized `DOMAIN_URL`, without query/session fragments.
  Update `templates/base.html` to remove unsupported global aggregateRating and AI
  assertions; retain unrelated page identity behavior without blanket canonicals.
  Add `/amigo-invisible` to `main.py:91–145` sitemap; test unique inclusion, configured
  domain/trailing slash, JSON-LD validity and unrelated page metadata regressions.
  Implementation and functional checks complete; delivery checkbox remains open pending work-unit commit.

- [x] T1/T2 implementation verified with observed strict TDD evidence below.
- [x] Functional verification complete; parent repeated the exact safe-prefix focused command: **29 passed in 0.57s**.
- [x] Native review capture and acknowledgment complete for the bound snapshot below.
- [ ] Task delivery/work-unit commit pending; no commit identity exists for this change.

## Verification and evidence
- Strict TDD source: `openspec/config.yaml:11` (`strict_tdd: true`) and `:49` (`apply.tdd: true`).
- Runner `P`: `/Users/toni.robres/Pycharmprojects/regalame_gemini3/venv/bin/python`;
  run in this worktree, never copy/symlink the runner or install unless dependencies are missing.
- Local safety prefix: `env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin PYTHON_DOTENV_DISABLED=1 DATABASE_URL=sqlite:///:memory: PYTHONDONTWRITEBYTECODE=1`.
- Baseline/full check: `P -m pytest -q --ignore=tests/test_e2e.py`: **336 passed in 7.96s**.
- Focused future check: `P -m pytest -q tests/test_seo_landings.py`; record expected RED,
  minimal GREEN and refactor results for both tasks, then rerun the full check with the safety prefix.
- Review intentional `tests/baselines/editorial_off_*.html` changes for all nine existing
  surfaces in `tests/test_editorial_filtering.py:395–426`; never blindly regenerate to hide regressions.
- Runtime harness: local TestClient HTML/XML/JSON-LD assertions; no live service/network checks.
- T1: expected RED **4 failed, 11 passed** (missing route/link); minimal GREEN **15 passed in 0.46s**.
  Test selector corrected to identify the wishlist CTA, not the separate login CTA; unused import removed.
  Refactor inspection: thin route and existing layout retained; no further source refactor needed.
- T2: expected RED **10 failed, 19 passed**; minimal GREEN **29 passed in 0.57s**.
  Refactor: conditional Jinja/XML whitespace cleaned before snapshot alignment and final checks.
- Nine expected golden failures observed; semantic patches applied first, then exact render whitespace/EOF aligned.
  Verified diff: shared schema only elsewhere; home copy/canonical, scoped blog link, one sitemap URL; **9 passed**.
- Final safe-prefix checks: focused **29 passed in 0.58s**; full **365 passed in 8.57s**; `git diff --check` clean.
- Runtime TestClient: query-bearing landings 200 with one H1 and matching clean identity; signed-in home 303, organizer 200, unknown route 404.

## Bound native review and deployment limits
- Parent-reported assessment: medium workload; all 16 intended paths staged; original dirty OAuth checkout status unchanged.
- Exact native consent granted. First review had no capturable result; retained bound STATUS reoffered the identical slot.
- One allowed fresh retry completed all 16 paths; capture admitted approved with no required correction.
- Acknowledgment succeeded: `gentle-ai.review-acknowledged/v1`; authority burned: `review-adb25910cc01e0d6`.
- Reviewed target: `sha256:57de324c3e7e00587b2faab3837ecd0a9bb62d05311b5bd444def89a4bac14ba`.
- Nonblocking advisories retained, not implemented: `R3-domain-url-empty` (`main.py:164`, empty/malformed configured DOMAIN_URL can emit relative canonicals)
  and `R3-env-coupled-default` (default-domain test/environment coupling). No further review or correction authorized.
- Before deployment, require valid nonempty `DOMAIN_URL=https://regalame.app`, or leave it unset to use the documented default.
  Production configuration has not been verified. E2E is excluded per CI; no browser visual, CWV or production check was performed.
- This documentation-only handoff is outside the acknowledged target; approval is bound to that snapshot, not a global approval.

## Delivery forecast and next step
Forecast **315–395 authored additions plus deletions**, including this initial document:
document 68; landings/routes/links 102–132; metadata/sitemap 35–45; tests 110–150.
Reviewed snapshot: **340 authored lines** (314 additions, 26 deletions); **114 generated lines** across nine goldens; **454 total**; 16 changed paths.
Generated golden updates are separately reported in full snapshot identity and reviewed.
T1 and T2 may form one coherent work unit with both observed checks, not artificial file slices.
Delivery strategy: **ask-on-risk**; 400 lines is advisory per task, not a cap or reason to minify/omit tests.
If actual authored changes exceed 400, report the exact count for the parent delivery decision before commit.
Rollback boundary: these landing routes/templates/links, metadata/sitemap edits and paired tests/snapshots only.
Next: create the authorized local work-unit commit; PR/push remain pending exact destination and existing GitHub CLI session authorization. Deployment requires separate authorization.
