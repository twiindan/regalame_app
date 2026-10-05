# Product Editorial Classification Specification

## Purpose

Offline, AI-assisted gift-suitability classification of catalog products. This capability defines the persisted editorial decision record (including manual overrides), the input fingerprint that governs when a product must be reclassified, the incremental/resumable/bounded classification job and its failure semantics, the provider integration rules (including data minimization), and the human-labeled evaluation gate that must pass before editorial enforcement may be enabled.

The companion capability `catalog-editorial-filtering` applies these decisions on public surfaces.

## Requirements

### Requirement: Editorial decision record

The system SHALL persist one editorial decision per product, holding: the editorial state (`eligible`, `contextual`, `excluded`, or `unknown`), a context value (required when the state is `contextual`), a reason, the model identifier that produced the decision, the policy/schema version in effect when it was produced, the input fingerprint used, and timestamps stored in naive UTC. The corresponding schema change SHALL be strictly additive: no existing table or column SHALL be altered or dropped.

#### Scenario: Complete decision persisted

- GIVEN the classification job received a valid provider response for a product
- WHEN the decision is persisted
- THEN the record contains the state, a non-empty context when the state is `contextual`, a reason, the model id, the policy version, the input fingerprint, and naive-UTC timestamps
- AND no `Product` or `ProductList` row is modified

#### Scenario: Contextual response without context is invalid

- GIVEN the provider returns state `contextual` with an empty or missing context
- WHEN the response is processed
- THEN the response is treated as invalid and no decision is persisted (failure-not-cached semantics apply)

#### Scenario: Migration is additive

- GIVEN the database at migration head `9f1c7b2a4d3e`
- WHEN the new migration is applied
- THEN only new editorial tables are created
- AND no existing table, column, or row is altered or dropped

### Requirement: Editorial states and semantics

The system SHALL use exactly four editorial states: `eligible` (suitable as a general gift idea), `contextual` (suitable only under a matching context), `excluded` (not suitable as a gift idea), and `unknown` (no valid classification exists). A product without a persisted decision SHALL be treated as `unknown`. `unknown` SHALL never be promoted to any visible state by defaulting, timeout, or absence of evidence.

#### Scenario: Unclassified product behaves as unknown

- GIVEN a newly imported product with no editorial decision
- WHEN any consumer of editorial state reads the product
- THEN the product is treated as `unknown`

#### Scenario: Unknown is never promoted

- GIVEN a product whose classification attempt failed or never ran
- WHEN editorial state is read
- THEN the state is `unknown`, never `eligible` or `contextual` by default

### Requirement: Manual overrides always win

The system SHALL support manual editorial decisions that always take precedence over AI-produced decisions for the same product. A manual override MUST survive reclassification runs, policy version bumps, and catalog imports. The commercial import pipeline MUST NOT write editorial state of any kind.

#### Scenario: Override wins over fresh AI output

- GIVEN a product with a manual override
- WHEN the classification job runs for that product, including when its fingerprint is stale and the AI response disagrees with the override
- THEN the effective decision remains the manual override
- AND the AI output does not replace it

#### Scenario: Override survives import and re-runs

- GIVEN a product with a manual override whose title and category are overwritten by a catalog import
- WHEN subsequent import and classification runs complete
- THEN the override remains in place and remains the effective decision

#### Scenario: Importer writes no editorial state

- GIVEN a normal catalog import run
- WHEN the import completes
- THEN the editorial decision store is unchanged by the import

### Requirement: Input fingerprint governs reclassification

The system SHALL compute an input fingerprint per product from: its normalized title, its last observed single category, the policy/schema version, and the model identifier. A persisted decision whose fingerprint matches the product's current inputs is current; a mismatch marks it stale and the product becomes eligible for reclassification. A change to price, rank, or `scraped_at` MUST NOT change the fingerprint. A change to title or observed category MUST change it. Bumping the policy version MUST invalidate all AI fingerprints.

#### Scenario: Price, rank, and scraped_at changes do not reclassify

- GIVEN a product with a current decision and unchanged title and category
- WHEN an import updates only price, rank, or `scraped_at`
- THEN the fingerprint is unchanged and the next job run does not reclassify the product

#### Scenario: Title change triggers reclassification

- GIVEN a product with a current decision
- WHEN an import overwrites the product's title
- THEN the fingerprint no longer matches and the product is reclassified on the next job run

#### Scenario: Observed category change triggers reclassification

- GIVEN a product with a current decision
- WHEN the product's last observed category changes
- THEN the fingerprint no longer matches and the product is reclassified on the next job run

#### Scenario: Policy version bump invalidates every AI decision

- GIVEN any number of current AI decisions
- WHEN the policy version is bumped
- THEN all AI fingerprints no longer match and the next job run reclassifies all in-scope products
- AND manual overrides remain the effective decisions throughout

### Requirement: Classification job is incremental, resumable, idempotent, and bounded

The classification job SHALL process only products that are pending (no valid decision) or stale (fingerprint mismatch), scoped to active products (`is_active=True`); deactivated products SHALL NOT be classified. It SHALL be resumable across process restarts by persisting progress so that a restarted run does not repeat committed work. Re-running the job SHALL be idempotent: it MUST NOT create duplicate or contradictory decisions. The job SHALL bound its concurrency, its provider request rate, and its wall-clock duration per run; when a bound is reached it SHALL stop cleanly, leaving remaining work to subsequent runs.

#### Scenario: Incremental processing

- GIVEN products with current fingerprints and some pending or stale products
- WHEN the job runs
- THEN only the pending or stale products are sent to the provider

#### Scenario: Resumable across restarts

- GIVEN a job run interrupted after k decisions were committed
- WHEN the job restarts
- THEN it does not re-request the k already-classified products
- AND when the run finishes, every in-scope product holds a valid decision

#### Scenario: Idempotent re-run

- GIVEN a completed backfill with no pending or stale products
- WHEN the job runs again
- THEN zero provider calls are made and no decision rows change

#### Scenario: Bounded rate, concurrency, and wall time

- GIVEN configured bounds for request rate, concurrency, and wall time
- WHEN the job runs against a provider that records call timings
- THEN the request rate never exceeds the configured rate, concurrent requests never exceed the configured concurrency, and the run stops within the wall-time bound with remaining work deferred to a future run

#### Scenario: Backfill scope is active products only

- GIVEN active and deactivated products
- WHEN the job runs
- THEN deactivated products are never sent to the provider

### Requirement: Failure semantics — failures are never cached

Transport errors, timeouts, and invalid or unparseable provider responses MUST NOT persist an editorial decision — in particular, they MUST NOT persist an `excluded` decision. A product with a prior valid decision whose fingerprint is unchanged MUST retain that decision when a transient failure occurs. When the reclassification of a stale product fails, the prior decision SHALL be retained and the product SHALL remain marked for a future run. Retries against the provider SHALL be bounded.

#### Scenario: Transport error on a never-classified product

- GIVEN a product with no decision
- WHEN the provider call fails with a transport error or timeout
- THEN no decision row is persisted and the product remains `unknown` for consumers

#### Scenario: Invalid provider response

- GIVEN the provider returns a malformed or unparseable payload
- WHEN the response is processed
- THEN no decision row is persisted and the product remains `unknown` for consumers

#### Scenario: Prior decision survives a transient failure

- GIVEN a product holding a valid decision whose fingerprint still matches its inputs
- WHEN a job run encounters a transient failure affecting that product
- THEN the existing decision is retained unchanged

#### Scenario: Failed reclassification of a stale product

- GIVEN a stale product holding a prior valid decision
- WHEN its reclassification attempt fails with a transport error, timeout, or invalid response
- THEN the prior decision is retained, no failure-derived state is written, and the product remains marked for a future run

#### Scenario: Retries are bounded

- GIVEN a provider that fails repeatedly for a product
- WHEN the job processes that product
- THEN retries are bounded, the product is left for a future run, and the job continues with other work

### Requirement: Provider integration and data minimization

The job SHALL call the configured OpenAI-compatible provider using the existing production HTTP client, with provider base URL, model identifier, and API key supplied by environment configuration. Requests to the provider SHALL contain only the product's title and observed category. No user data SHALL be stored on a decision record or transmitted to the provider.

#### Scenario: Minimal classification payload

- GIVEN a product being classified
- WHEN the provider request is sent
- THEN the payload contains only the product's title and category
- AND no user data (users, wishes, emails) is present in the payload

#### Scenario: No user data on the decision record

- WHEN a decision is persisted
- THEN the record contains no user identifiers or wish data

#### Scenario: Provider configuration via environment

- GIVEN provider base URL, model, and API key environment variables are set
- WHEN the job starts
- THEN it uses the configured provider endpoint, model, and credentials

### Requirement: Job modes

The job SHALL support a no-network dry-run mode that makes zero provider calls and performs zero writes, and a shadow run mode that makes real provider calls and persists decisions without any effect on public behavior. Enforcement (`enforce`) SHALL be a separate configuration flag, not a job mode.

#### Scenario: Dry-run makes zero calls and zero writes

- GIVEN dry-run mode
- WHEN the job runs
- THEN zero provider calls are made and no data is written

#### Scenario: Shadow run persists decisions only

- GIVEN shadow run mode
- WHEN valid provider responses are received
- THEN decisions are persisted
- AND no public surface behavior changes as a result of the run

### Requirement: Evaluation gate

The system SHALL provide an offline evaluation harness that measures classification quality on a stratified sample of approximately 100 products with human-labeled expected outcomes, stratified across catalog categories. Evaluation SHALL run against persisted decisions and human labels without provider calls. The following thresholds are the adopted defaults, stated as concrete values so they can be tested and later re-tuned by updating this specification:

- Overall agreement between AI decisions and human labels on the sample MUST be at least 90%.
- Of products human-labeled `excluded`, at least 95% MUST be classified `excluded` or `unknown` (at most 5% MAY leak as `eligible`).
- The residual `unknown` share across active products after backfill SHOULD be at most 10%.
- Backfill coverage of active products MUST be 100%.

The gate SHALL report pass or fail, where pass requires all MUST thresholds to hold. `enforce` MUST NOT be enabled until the gate passes.

#### Scenario: Gate passes

- GIVEN a sample evaluation with 92% overall agreement, 3% of human-labeled `excluded` products leaking as `eligible`, an 8% residual `unknown` share, and 100% backfill coverage
- WHEN the gate is evaluated
- THEN the gate reports pass
- AND enforcement MAY be enabled

#### Scenario: Gate fails on agreement

- GIVEN 87% overall agreement with all other thresholds met
- WHEN the gate is evaluated
- THEN the gate reports fail
- AND enforcement MUST NOT be enabled

#### Scenario: Gate fails on excluded leakage

- GIVEN 93% overall agreement but 8% of human-labeled `excluded` products classified `eligible`
- WHEN the gate is evaluated
- THEN the gate reports fail
- AND enforcement MUST NOT be enabled

#### Scenario: Gate fails on incomplete backfill

- GIVEN all agreement thresholds met but backfill covering 97% of active products
- WHEN the gate is evaluated
- THEN the gate reports fail
- AND enforcement MUST NOT be enabled

#### Scenario: Residual unknown share above the soft threshold

- GIVEN a gate whose MUST thresholds are met and whose residual `unknown` share is 14%
- WHEN the gate is evaluated
- THEN the gate reports pass but flags the `unknown`-share threshold as exceeded

#### Scenario: Evaluation is offline

- GIVEN persisted decisions and human labels for the sample
- WHEN the gate is evaluated
- THEN no provider calls are made
