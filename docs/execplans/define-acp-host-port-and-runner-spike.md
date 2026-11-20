# Define the ACP host port and runner spike

## Outcome and scope

Clarify the application-owned Agent Client Protocol (ACP) host port, its
provisional `acpsdk` adapter, and its later Magitek adapter. Add an early local
`arun`/`youxiad` experiment with observable acceptance criteria, while
preserving the qualified hosting and fleet gates.

The user requested documentation pull requests against Youxia and Magitek on
2026-11-20. This plan covers the Youxia changes. It adds no runtime, installed
configuration, service, or implemented capability.

## Inputs and constraints

- Youxia base: `00eb09cc95f2d7b453a2433ef6439a4a96fcc9be`.
- Magitek base: `2296f8ac5d550a2f5706952fb6a641179605dfa5`, especially design
  §§7–10 and its Wireframe qualification gates.
- Existing Youxia architecture §§3, 6–9, and 12; RFC 0001 §§13–14;
  [runner transport contract](../contracts/arun-transport.md); roadmap §§1.3
  and 3.2; and ADR 0001.
- Repository `AGENTS.md`, documentation style guide, and technical design,
  roadmap, and df12 copy skills. The existing brief authorizes this scoped
  design amendment and both PRs.

The repository already assigns protocol work to an adapter, but names Magitek
directly in the daemon topology and gates the runner behind its qualification.
The new contract makes that seam explicit without moving ACP into `arun` or
claiming that an SDK wrapper supplies Magitek's planned retention guarantees.
The independent Magitek change retains ownership of its generic library API and
dependency qualification.

## Outline and deliverables

1. Add a semantic port contract: ownership, operations, capability evidence,
   unavailable outcomes, profiles, adapter selection, and shared witnesses.
2. Record the proposed adapter decision in ADR 0002 and reference it from
   the existing architecture, transport contract, RFC amendment, and indexes.
3. Add roadmap step 1.5 for contract, runner, SDK adapter, daemon integration,
   and failure evidence. Keep it independent of Murder, cloud compatibility,
   the observation spike, and Magitek implementation.
4. Connect promotion and Magitek replacement to the existing hosting gates.
   Keep every runtime task unchecked.

## Acceptance criteria

- The domain owns the port vocabulary; concrete SDK/Magitek types stay in
  adapters. The daemon owns policy, durable effects, and recovery.
- `arun` owns raw transport and one execution; its protocol cannot depend on
  the selected ACP engine.
- Capability support, negotiation, host services, policy, readiness, and
  qualification have distinct meanings. Unavailable features produce explicit
  outcomes, and mandatory correctness does not become an optional feature.
- Adapter changes use fresh protocol generations or new runs. No text promises
  hot-swapping a surviving conversation or crash-restored ACP state.
- The early spike has a dependency path from the tooling baseline to one
  local agent, with no cloud writes or production qualification claim.
- New tasks cite their contracts and measurable witnesses; dependencies have
  no cycles or references to nonexistent tasks.
- Markdown formatting, lint, spelling, diagrams, relative links, and the full
  diff receive review before publication. Runtime tests remain future work.

## Progress

- [x] Inspect current repositories, contracts, guidance, and skill references.
- [x] Agree the cross-repository ownership and document outline from the brief.
- [x] Draft the contract and ADR, then reconcile architecture and roadmap.
- [x] Review both changes together for semantic and dependency consistency.
- [x] Run documentation checks and record their actual scope.
- [x] Prepare the paired PR contents and cross-repository references.

## Validation and delivery record

Validation on 2026-11-20:

- The exact Markdown formatting and check portions of `make fmt` and
  `make check-fmt` passed with mdtablefix 0.6.1. Full Rust-toolchain targets
  were unavailable in the editing environment; no substitute command claimed to
  validate Rust source.
- `make markdownlint`, including the pinned spelling gate, passed across
  all 29 Markdown files. Dictionary regeneration introduced no tracked change.
- `make nixie` passed with its documented Merman renderer.
- Relative file/anchor checks and `git diff --check` passed. Task IDs are
  unique; explicit task dependency references resolve without cycles.
- Independent cross-repository review found no remaining blockers. It exposed
  a potential circular prerequisite around a published Magitek release; task
  3.2.6 now permits a pinned candidate and joint pre-release qualification.

The pull request records publication and CI status, with a link to its paired
Magitek change. No runtime source changed, no agent ran, and no runtime
qualification result follows from these documentation checks.
