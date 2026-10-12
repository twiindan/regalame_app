# Feature: seo-blog-faqs (work unit 6)

Author neutral per-post FAQs to activate the FAQPage JSON-LD hook in
`templates/blog_post.html` (left by PR #77). No `BLOG_POSTS` entry defines
`faq` yet.

## Tasks

- [ ] T1: Add visible FAQ section to `templates/blog_post.html` (same pattern
      as `category_seo.html` lines 84-96) — the hook currently only emits
      JSON-LD; Google requires visible FAQ content.
- [ ] T2: Author 2-3 neutral, factual FAQ entries (`{"q", "a"}`) for each of
      the 12 posts in `blog_config.py`, style matched to
      `seo_content.category_faq`: no invented numbers, no ratings, no
      superlatives, no concrete prices. Each claim checked against the
      post's title/description/criteria.
- [ ] T3: Add the `faq` field to every `BLOG_POSTS` entry.
- [ ] T4: TDD tests: every post emits FAQPage JSON-LD with its FAQ; visible
      answers match the schema; JSON parses. Full suite
      `--ignore=tests/test_e2e.py` green; regenerate
      `tests/baselines/editorial_off_blog.html` with
      `--editorial-update-baselines` (the visible section changes that
      golden page).
- [ ] T5: One commit `feat(seo): ...`. No push, no PR.

## Evidence

(commit hash recorded after T5)
