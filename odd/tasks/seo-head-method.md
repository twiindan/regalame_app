# SEO: HEAD support on GET routes

Work unit 7 of the SEO roadmap (`feat/seo-head-method`).

## Objective, problem, and why

Every HTML route declared with `@app.get` returns 405 to HEAD (diagnosed in
production at https://regalame.app and reproduced locally with TestClient:
`curl -I https://regalame.app/` → 405). Static mounts answer 200 because
Starlette core adds HEAD to GET routes; FastAPI's `APIRoute` does not.
Crawler validators and uptime monitors use HEAD, so the site fails their
pre-flight checks.

## Verified version facts (fastapi 0.124.2 / starlette 0.50.0 in ./venv)

- `FastAPI.__init__` in this version exposes neither `api_route_class` nor
  `default_router_class`; the documented app-wide way to install a custom
  `APIRoute` subclass is `app.router.route_class = ...` right after
  construction (before routes are registered).
- `fastapi/openapi/utils.py` iterates `route.methods` unfiltered: naively
  adding `"HEAD"` to `self.methods` leaks HEAD operations into the OpenAPI
  schema and produces duplicate operation-ID warnings. Rejected.
- Starlette 0.50.0 strips the body for HEAD **only** in `FileResponse`
  (`send_header_only`); the base `Response` sends the full body. Stripping
  must therefore happen in the route itself, not delegated to Starlette.
- `starlette.routing.Route.handle` 405s when `scope["method"]` is not in
  `self.methods`, and `Route.matches` returns `Match.PARTIAL` for a
  path-match/method-mismatch. Both must be overridden.

## Approved design

`HeadOnGetAPIRoute(APIRoute)` in `main.py`:

- `matches`: upgrade `Match.PARTIAL` to `Match.FULL` when the request method
  is HEAD and the route serves GET. `self.methods` stays `{"GET"}` so the
  OpenAPI schema is untouched.
- `handle`: for HEAD on a GET route, copy the scope with `method="GET"` and
  forward to the handler with a `send` wrapper that zeroes
  `http.response.body` payloads. Content-Length and all other headers are
  preserved (RFC 9110: HEAD reports GET's metadata without the body).
- POST-only routes are untouched: their routes never serve GET, so
  `matches`/`handle` fall through to the Starlette default (405 + `Allow`).

Scope: local implementation, TDD, tests, one work-unit commit on
`feat/seo-head-method`. Not authorized: push, PR.

## Tasks

- [ ] T1 (RED): `tests/test_head_method.py` — HEAD /, /sitemap.xml,
      /blog/{real-slug} → 200 with empty body and GET-identical
      Content-Length; HEAD on POST-only route → 405 with `Allow: POST`;
      OpenAPI schema contains no HEAD operations.
- [ ] T2 (GREEN): implement `HeadOnGetAPIRoute`, wire
      `app.router.route_class`, keep tests green.
- [ ] T3: full suite `pytest --ignore=tests/test_e2e.py` green.
- [ ] T4: single commit `fix(seo): ...`.

## Evidence

- (pending)
