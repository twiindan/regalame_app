# Catalog Editorial Filtering Specification

## Purpose

Centralized, mode-gated enforcement of editorial decisions across all public product surfaces. This capability defines the two filter modes (`off` shadow default, `enforce`), the per-state visibility semantics, correct totals and pagination under filtering, zero-visible category suppression in navigation and the sitemap, graceful blog empty states, and the guarantees that wish lists and the commercial import pipeline are unaffected.

Editorial states, decision records, and the evaluation gate are defined in `product-editorial-classification`.

## Requirements

### Requirement: Filter modes

The system SHALL support two filter modes selected by configuration: `off` (shadow, the default) and `enforce`. In `off`, persisted editorial decisions SHALL have zero effect on any public surface: responses MUST be byte-identical to the behavior this change replaces. In `enforce`, the visibility rules of this specification apply.

#### Scenario: Shadow mode preserves pre-change behavior

- GIVEN mode `off` and products holding any editorial states, including `excluded`
- WHEN any public product surface is requested
- THEN the response is byte-identical to the response produced before editorial filtering existed

#### Scenario: Default mode is off

- GIVEN no filter mode is configured
- WHEN the application runs
- THEN the effective mode is `off`

#### Scenario: Enforce applies visibility rules

- GIVEN mode `enforce`
- WHEN public product surfaces are requested
- THEN the visibility rules of this specification apply

### Requirement: State visibility under enforcement

Under `enforce`, general product surfaces SHALL show only `eligible` products. Products classified `excluded`, products classified `unknown`, and products with no decision SHALL be hidden from every public surface, including context surfaces. Products classified `contextual` SHALL be hidden from general surfaces and visible only on surfaces that explicitly match the product's context.

#### Scenario: General surfaces show only eligible products

- GIVEN mode `enforce` and products classified `eligible`, `contextual`, `excluded`, and one with no decision
- WHEN a general product surface is requested
- THEN only the `eligible` product appears

#### Scenario: Contextual products visible under a matching context

- GIVEN mode `enforce` and a product classified `contextual` with context `bebe`
- WHEN the surface that matches context `bebe` is requested
- THEN the product is visible there

#### Scenario: Contextual products hidden elsewhere

- GIVEN mode `enforce` and a product classified `contextual` with context `bebe`
- WHEN a general surface or a surface matching a different context is requested
- THEN the product is not shown

#### Scenario: Excluded and unknown products are hidden everywhere

- GIVEN mode `enforce` and products classified `excluded` and `unknown`
- WHEN any public surface is requested, general or contextual
- THEN neither product appears

### Requirement: Filtering correctness — totals and pagination

Editorial filtering SHALL be applied to the shared product search path BEFORE totals are computed, so that reported totals, page counts, and page contents reflect only visible products on every surface using that path (dashboard samples, `/catalog`, `/trends`, `/most-desired`, `/bestsellers`, `/ideas/{slug}`, and blog product lists).

#### Scenario: Totals reflect the filtered set

- GIVEN mode `enforce` and a query matching 10 products of which 4 are hidden by editorial state
- WHEN the catalog page is requested
- THEN the reported total is 6

#### Scenario: Pagination reflects the filtered set

- GIVEN mode `enforce` and 12 visible products with a page size of 10
- WHEN page 2 is requested
- THEN page 2 contains the 2 remaining visible products and the total page count is 2

#### Scenario: Pages contain no hidden items

- GIVEN mode `enforce`, a page size of 10, and hidden products interleaved with visible ones
- WHEN page 1 is requested
- THEN it contains exactly 10 visible products with no gaps

#### Scenario: All shared-path surfaces filter

- GIVEN mode `enforce` and a product classified `excluded` that matches every listed surface
- WHEN the dashboard samples, `/catalog`, `/trends`, `/most-desired`, `/bestsellers`, `/ideas/{slug}`, and blog product lists are requested
- THEN the excluded product does not appear on any of them

### Requirement: Zero-visible category suppression

Under `enforce`, navigation categories and the sitemap SHALL NOT include any category whose filtered visible product count is zero. Under `off`, category listings and the sitemap SHALL be unchanged from pre-change behavior.

#### Scenario: Empty category suppressed from navigation and sitemap

- GIVEN mode `enforce` and a category whose products are all hidden by editorial state
- WHEN the navigation and the sitemap are rendered
- THEN the category does not appear in the navigation
- AND the sitemap does not include the category's URL

#### Scenario: Category with visible products is retained

- GIVEN mode `enforce` and a category with at least one visible product
- WHEN the navigation and the sitemap are rendered
- THEN the category appears in both

#### Scenario: Shadow mode keeps all categories

- GIVEN mode `off`
- WHEN the navigation and the sitemap are rendered
- THEN they are identical to pre-change output

### Requirement: Blog lists and hero image fallback

Blog product lists SHALL paginate over the filtered visible set. When filtering empties a blog product list, the post page SHALL render a graceful empty state, and the hero image fallback SHALL NOT be computed from an empty product list.

#### Scenario: Empty blog list renders a graceful empty state

- GIVEN mode `enforce` and a blog post whose product list filters to zero products
- WHEN the post page is requested
- THEN the page renders successfully with an empty-state indication

#### Scenario: Hero image fallback with no products

- GIVEN the same empty blog product list
- WHEN the post page is rendered
- THEN no hero image is derived from a product and the page renders a defined fallback without error

#### Scenario: Hero image from first visible product

- GIVEN mode `enforce` and a blog post whose product list has visible products
- WHEN the post page is rendered
- THEN the hero image fallback uses the first visible product's image

### Requirement: Wish lists are unaffected

Wish list functionality SHALL remain unaffected by editorial filtering: a user MUST be able to add any product to a wish list — including products classified `excluded` or `unknown` — and existing wishes MUST remain visible and functional regardless of their product's editorial state or the filter mode.

#### Scenario: Adding an excluded product to a wish list

- GIVEN mode `enforce` and a product classified `excluded`
- WHEN the user adds it to a wish list
- THEN the wish is created successfully

#### Scenario: Existing wishes survive classification

- GIVEN an existing wish for a product that is later classified `excluded`
- WHEN the user views their wish list under `enforce`
- THEN the wish and its product remain visible and functional

### Requirement: Import pipeline and health metrics are unaffected

Editorial filtering and classification SHALL NOT modify the commercial import pipeline's data or metrics: curation SHALL NOT create, delete, or modify `ProductList` rows, and import health metrics SHALL continue to count unfiltered `ProductList` rows.

#### Scenario: Health metrics count unfiltered rows

- GIVEN mode `enforce` with many hidden products
- WHEN an import runs and health metrics are computed
- THEN the metrics reflect all `ProductList` rows, not the filtered visible set

#### Scenario: Curation does not touch ProductList rows

- GIVEN classification and filtering active in any mode
- WHEN the classification job runs and surfaces are served
- THEN the `ProductList` row set is unchanged

### Requirement: Enforcement activation preconditions

The `enforce` mode MUST NOT take effect until the evaluation gate defined in `product-editorial-classification` has passed with 100% backfill coverage of active products. Until those preconditions hold, the effective filter mode SHALL remain `off` regardless of configuration.

#### Scenario: Enforce without a passing gate behaves as off

- GIVEN the evaluation gate has not passed
- WHEN the filter mode is configured as `enforce`
- THEN public surfaces behave exactly as in mode `off`

#### Scenario: Enforce with incomplete backfill behaves as off

- GIVEN the gate has passed but backfill covers less than 100% of active products
- WHEN the filter mode is configured as `enforce`
- THEN public surfaces behave exactly as in mode `off`

#### Scenario: Enforce after preconditions applies filtering

- GIVEN the gate has passed and backfill covers 100% of active products
- WHEN the filter mode is configured as `enforce`
- THEN the visibility rules of this specification apply
