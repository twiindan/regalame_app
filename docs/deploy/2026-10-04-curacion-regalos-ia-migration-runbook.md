# Migration runbook — `b3d9f1a7c250` add editorial decision tables

Work Unit 1 / PR 1 of `curacion-regalos-ia`. This is the CI-external verification
gate for the strictly additive migration that adds `editorial_decision` and
`editorial_gate_state`. Alembic is **never** run in CI (`tests/conftest.py` uses
`SQLModel.metadata.create_all`), so this runbook is the only executable proof
that the migration applies and reverts cleanly against Postgres.

- Revision: `b3d9f1a7c250`
- Down revision: `9f1c7b2a4d3e` (verified head before this change)
- Migration file: `alembic/versions/b3d9f1a7c250_add_editorial_decision.py`
- Nature: strictly additive — `upgrade()` performs only `op.create_table` and
  one `op.create_index`; no existing table, column, or row is touched.

## Preconditions

- A **snapshot/clone of production Postgres** (never run this blind on prod).
- `DATABASE_URL` (or the project's configured database URL) pointing at the
  snapshot.
- The deploy commit checked out.

## Steps

1. **Apply the migration.**

   ```bash
   alembic upgrade head
   ```

2. **Assert the new tables exist and the existing ones are unchanged.**

   ```sql
   \d+ editorial_decision
   \d+ editorial_gate_state
   \d+ product
   \d+ productlist
   ```

   Expected:
   - `editorial_decision` exists with `product_id` non-null and a **unique
     index** (`ix_editorial_decision_product_id`); the AI-side and `manual_*`
     columns are nullable.
   - `editorial_gate_state` exists with `gate_passed`, `coverage_ratio`,
     `unknown_ratio`, `policy_version`, `model_id`, `evaluated_at`,
     `updated_at` non-null and `overall_agreement` / `excluded_leak_ratio`
     nullable.
   - `\d+ product` and `\d+ productlist` are **byte-for-byte unchanged**
     (same columns, types, constraints, indexes as before this revision).

3. **Exercise a read route** against the running app to confirm normal catalog
   serving is unaffected (shadow default: `EDITORIAL_FILTER_MODE` unset ⇒
   `off`). Example: request `/`, `/catalog`, and one `/ideas/{slug}` page; all
   must render exactly as before.

4. **Revert one revision and assert the reverse is clean.**

   ```bash
   alembic downgrade -1
   ```

   Then assert:
   - `editorial_decision` and `editorial_gate_state` are **dropped**.
   - `\d+ product` and `\d+ productlist` are still unchanged and their data is
     intact (`SELECT count(*) FROM product;` unchanged from before).

5. **Re-apply and confirm idempotence of the forward path.**

   ```bash
   alembic upgrade head
   ```

   Both tables exist again; existing product data is untouched.

## Rollback

For behavior rollback, `alembic downgrade -1` is available and verified here,
but it is **not required**: flipping `EDITORIAL_FILTER_MODE` to `off` (or
`DELETE FROM editorial_gate_state`) reverts all public behavior instantly while
the (empty) tables remain inert.

## Record

Paste the observed command output for steps 1–5 into the PR description. PR 1
must not merge to `main` until this runbook has been executed on the snapshot.
