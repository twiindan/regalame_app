# SEO absolute BreadcrumbList JSON-LD URLs

Work unit 3 of the persisted SEO plan (`odd/tasks/seo-improvements.md` line of work). Inherited
follow-up from `odd/tasks/seo-absolute-canonicals.md`: "absolute URLs in `blog_post.html`
BreadcrumbList items".

## Verified reality (audit correction)

The inherited finding is stale. The only template emitting `BreadcrumbList` is
`templates/partials/breadcrumbs.html`, and its JSON-LD already normalizes every `item` through
`social_url(crumb.url)` — committed that way in `7fdf08c` (feat(seo): per-page structured data
and breadcrumbs), before the canonical work unit. `blog_post.html` and `category_seo.html` feed
the partial relative `crumbs` (input, by design); the emitted JSON-LD is absolute. A scan of all
eight golden baselines found zero relative `url`/`item`/`mainEntityOfPage` values in any JSON-LD.
Other ItemLists use Amazon product URLs (absolute) or `request.url` (absolute).

## Scope decision

No production template change is warranted (adding `social_url` in the calling templates would be
redundant). Real gap: the SEO landing tests pin breadcrumb names/positions but never pin URL
absoluteness, so a refactor could silently reintroduce relative JSON-LD URLs with a green suite.

- Close as **verification + regression pin** via TDD: new assertions require every
  `BreadcrumbList` `item` (and the CollectionPage `ItemList` `url`s already absolute by data) to
  start with `public_origin()`.
- RED is observed by mutation: temporarily bypass `social_url()` in the partial, watch the new
  pins fail, restore, watch them pass.
- No baseline regeneration needed (no rendered-output change).

## Out of scope

- `rel=prev/next` relative hrefs in `category_seo.html` (link rel, not JSON-LD; deprecated by
  Google anyway).
- Amazon affiliate URLs inside ItemList schema.

## Tasks

- [x] Add absolute-URL breadcrumb JSON-LD pins to `tests/test_seo_landings.py`; observe RED via
      controlled mutation of `templates/partials/breadcrumbs.html`.
- [x] Full suite green (`--ignore=tests/test_e2e.py`): 577 passed.
- [x] One work-unit commit on `feat/seo-breadcrumbs-absolute`.

## Evidence

- Tests: pins added to `test_blog_post_emits_blogposting_and_matching_breadcrumbs` (every
  BreadcrumbList `item` starts with `public_origin() + "/"`) and
  `test_category_emits_collectionpage_itemlist_and_breadcrumbs` (ItemList `url`s absolute
  `https://`). RED observed by mutation: bypassing `social_url()` in the partial made the blog
  post pin fail while the suite stayed green without it; partial restored, pins green.
- No baseline regeneration: no rendered-output change (verified all 8 golden baselines already
  carry zero relative JSON-LD URLs).
- Commit: `fb8d85a` — test(seo): pin absolute BreadcrumbList JSON-LD URLs
