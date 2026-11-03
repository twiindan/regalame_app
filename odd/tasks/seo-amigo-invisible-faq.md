# SEO amigo invisible landing — FAQ + FAQPage

Work unit 4 of the SEO plan. Goal: strengthen `/amigo-invisible` (the site's
primary keyword landing) with an FAQ section and `FAQPage` JSON-LD, mirroring
the `/ideas/{slug}` pattern (`seo_content.category_faq()` +
`templates/category_seo.html`).

## Objective and problem
Audit: the landing has ~513 words, no FAQ, no `FAQPage` schema. Existing tests
intentionally pin "no FAQPage on /amigo-invisible"
(`tests/test_seo_landings.py`: `test_shared_metadata_is_valid_and_does_not_invent_claims`
and `test_faqpage_is_confined_to_category_landings`); this work unit changes
that intent explicitly.

## Authorized implementation boundary
- Branch: `feat/seo-amigo-invisible-landing` (already created).
- Files: `seo_content.py`, `main.py` (`/amigo-invisible` route context only),
  `templates/amigo_invisible.html`, `tests/test_seo_landings.py`,
  `tests/baselines/` (only if a rendered baseline regenerates; no
  amigo-invisible baseline exists today), this doc.
- TDD: observe RED (new FAQ tests) before implementing.
- No push, no PR. One work-unit commit, `feat(seo): ...`.

## Facts verified against code (FAQ answers must stay within these)
- Draw: admin-only, needs >= 2 members; random assignment; no self-assignment
  (`services.perform_draw`); respects `GroupExclusion` veto pairs; too many
  vetos can make a valid combination impossible.
- Each participant only sees their own giftee in the group page
  (`main.py` `group_dashboard`: `membership.giftee_id`); results are consulted
  in the app, never sent via WhatsApp/email.
- Every participant needs an account and logs in to join via invite
  code (`/join/{code}` requires login).
- Wish lists: user adds wishes (URL or text); public profile `/p/{user_id}` is
  viewable without an account; reserving a wish requires login; wishlist can be
  shared by email (`/public/share-email`).
- Group creation: admin sets name, date and budget; budget is orientative, the
  app does not control spending.
- Invitations: WhatsApp shares the invite link, not results.

## Tasks
- [x] T1 — RED: add FAQ tests to `tests/test_seo_landings.py` (FAQ presence on
      the page + FAQPage JSON-LD on `/amigo-invisible`); drop `/amigo-invisible`
      from the two FAQPage-prohibition tests (intentional intent change).
- [x] T2 — GREEN: `amigo_invisible_faq()` in `seo_content.py`; pass to route
      context in `main.py`; FAQ section + `FAQPage` JSON-LD in
      `templates/amigo_invisible.html` (same pattern as `category_seo.html`).
- [x] T3 — Full suite `venv/bin/python -m pytest -q --ignore=tests/test_e2e.py`
      green; regenerate baselines only if needed (none needed: no
      amigo-invisible baseline exists).
- [x] T4 — Work-unit commit `feat(seo): ...`; no push.

## Evidence
- Focused suite: `tests/test_seo_landings.py` 78 passed (RED observed first:
  the 2 new FAQ tests failed with StopIteration/missing FAQ section).
- Full suite (excl. e2e): 578 passed.
- Routing note: `gentle-ai-worker` / `gentle-ai-verify` could not launch —
  the session's subagent runtime fails to start (`gentle-engram` extension
  tool-name conflict, pi exits code 1). Implemented and verified inline as
  fallback; both facts recorded here per delegation contract.

## Notes
- Engram mirror unavailable in this session (no memory tools active); this file
  is the durable task record.
