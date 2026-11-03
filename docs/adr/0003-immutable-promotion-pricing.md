# ADR-0003: Immutable promotion sources and exact pricing

Status: Accepted

Related issue: [#26](https://github.com/rafaself/atf-ai-engineer-challenge/issues/26)

## Context

Catalog and promotion facts must reflect the supplied data without modifying source files or rewriting historical order totals.

## Decision

Validate the category, product, and promotion inputs before atomically replacing the catalog snapshot. Preserve source values and store inactive promotions. Use the supplied active flag only; do not infer campaign dates. For available products, an eligible promotion takes precedence; otherwise, an explicitly requested PIX payment gets 5% off. Discounts do not stack, unavailable products receive no discount, and integer-centavo arithmetic rounds half-up. Calculate payable-price filtering and quotes from one current catalog snapshot.

## Consequences

Pricing remains deterministic and requires no separate rules engine or database. Historical order totals and supplied source files remain unchanged.
