# Changelog

## 0.2.0 — finite auditable decision models

- Introduce `raiffa.model/2.0` and its packaged JSON Schema: finite influence
  diagrams, information arcs, perfect recall, sourced parameters, and unit checks.
- Add bounded exact policy enumeration, policy risk profiles, first-order CDF
  dominance, certified affine switching regions, joint/partial perfect
  information, finite study EVSI, and independent net-value research ranking.
- Add immutable hash-linked model revisions, frozen local source artifacts,
  replayable analyses, conflict checks, `doctor`, and revision comparisons.
- Add `guide`, state-derived `next`/`status`, `risk`, deterministic HTML/SVG/JSON
  reports, and local proposed Treffen/Vorhersage handoff artifacts.
- Successful CLI responses retain `data` and `warnings` inside a versioned
  envelope. Parser and domain failures now use structured JSON on stderr.
- Add two synthetic LEG-01 fixtures and an executable end-to-end tutorial.
- Preserve legacy tree commands and project state. Legacy `evpi` now rejects
  unsupported multi-node sums; nested legacy EVPPI and unimplemented regret
  criteria fail explicitly. Legacy `dominated_branches` means inferior expected
  utility, not stochastic dominance; use the new model workflow for CDF checks.

This is the finite first slice of [the successor specification](docs/spec-v2.md).
Continuous simulation, nonlinear/multiattribute utility, general nonlinear
sensitivity, native package adapters, and EDSL instrument make/ingest remain
future work. Reports disclose omitted challenge analyses. No automatic migration
of legacy numeric inputs to provenance-typed models is performed.
