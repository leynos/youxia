# Add the Linux component architecture

## Outcome and scope

Create a proposed architecture for `youxia`, `youxiad`, `magitek`, `arun`, and
`murder`. Preserve the selected Lody client contracts while replacing internal
supervision with systemd services and cgroup v2 resource controls. Document
process survival, transport recovery, and ACP recovery separately.

This change adds design material and updates its indexes and conflicting
planning statements. It implements no daemon, protocol, or service unit and
does not mark implementation tasks complete.

## Inputs and constraints

- User brief dated 2026-11-17: Linux host, systemd, cgroups, slices,
  compatibility rather than structural replication, and `murder` as the Flock
  implementation.
- Earlier project decision: `arun` owns the enduring agent connection and raw
  output buffering; ACP interpretation stays in `youxiad`; agent survival after
  `arun` death is outside scope.
- Youxia baseline: `f6f4b46aac1f758b47036efe0af5e50e0362c866`, RFC 0001,
  roadmap phases 1, 3, and 4, and the Comenq lessons.
- Lody documentation: open PR 1 at
  `da27f215df33d6ee5938461d6c060acb959dd1fb`, describing upstream Lody
  `61bd9701a5ed6899a9f42787df682acfc3fd7d4b`.
- Magitek: draft design PR 1 at
  `bfef49cbf10912ccf8ed246d4760bbb21f96c01b`; Wireframe RFCs at
  `6ad888595cf912e8424ea6e7573af7f76b096282`.
- Technical design document and df12 copy skills; repository documentation
  style guide and `AGENTS.md`.

The design skill's auxiliary anatomy, research, and editing reference files
were unavailable through both its resource provider and installed package. The
main skill and repository style guide supply the applicable workflow and
editing rules. No missing reference changes the requested scope.

## Outline and deliverables

1. Problem, evidence status, scope, terminology, and compatibility matrix.
2. Component ownership and Linux topology.
3. Launch, transport, recovery, and shutdown contracts.
4. Durable state, native replication, budgets, and observability.
5. Alternatives, migration, acceptance evidence, and dependency gates.

Produce an architecture design, a proposed supervision ADR, a separate `arun`
transport contract, and a parseable Linux resource example. Draft diagrams as
external working artefacts, validate them, and incorporate them in the design.
Amend RFC 0001 explicitly and reconcile the affected existing roadmap tasks.

## Acceptance criteria

- Each component has one named owner for process, protocol, and durable state.
- Compatibility preserves externally observable contracts without copying
  watchdog topology or assuming undisclosed cloud behaviour.
- No text equates byte replay, pipe writes, or unit readiness with ACP recovery
  or exactly-once effects.
- A daemon restart cannot stop independent runs through dependencies or shared
  runtime-directory cleanup; `arun` death ends its run.
- Limits include application retention and aggregate host resources. Same-user
  cgroups do not claim hostile-code isolation.
- Relative links, Markdown, Mermaid, and the TOML artefact validate.
- An independent review checks lifecycle, protocol, and compatibility claims.
- The resulting pull request records completed checks and concrete limitations.

## Progress

- [x] Inspect source revisions, current repository guidance, and implementation.
- [x] Research Lody compatibility, Magitek boundaries, and Linux supervision.
- [x] Present the section outline and delivery approach.
- [x] Draft and validate contracts and diagrams.
- [x] Draft the design and ADR; reconcile existing documents.
- [x] Complete independent review, editing, and documentation validation.
- [x] Publish the documentation branch and pull request.
- [x] Address review feedback and revalidate the documentation.

## Validation record

Completed on 2026-11-17:

- `make markdownlint` passed across all 26 Markdown files, including the pinned
  spelling gate. Dictionary regeneration produced no repository diff.
- `make nixie` passed for all four repository Mermaid diagrams with Nixie's
  native Merman renderer, including both new architecture diagrams. Standalone
  drafts also rendered before incorporation.
- The exact Markdown formatting/check steps from `make fmt` and
  `make check-fmt` passed with mdtablefix 0.6.1. The full `make fmt` target
  initially stopped because the drafting shell did not expose `rustup` on
  `PATH`; the Markdown step ran directly. A later managed-environment shell
  resolved the pinned toolchain, and `make check-fmt`, `make lint`,
  `make typecheck`, and `make test` all passed. No Rust source or build
  configuration changed.
- One-off checks verified 102 local link targets/anchors, numeric footnote
  references, TOML parsing, and memory, swap, task, raw-spool, transport,
  replica, and combined admission relationships.
- `git diff --check` passed.
- Independent Lody, Linux, and Magitek reviews identified gaps in revocation,
  completed-run recovery, retained disk accounting, logical-frame abandonment,
  terminal execution containment, and swap/admission composition. The amended
  contracts resolve each finding; focused rechecks reported none outstanding.
- Review feedback identified the missing direct index link to the runner
  transport contract. `docs/contents.md` now lists that contract alongside the
  contracts index, and the Markdown gates were re-run after the edit.

Runtime qualification scenarios in the design remain planned evidence, not
executed tests of this documentation change. No service was installed, no agent
ran, and no deployed compatibility or performance claim was made.

## Delivery

Published as [Youxia PR 11](https://github.com/leynos/youxia/pull/11) from
`docs/linux-component-architecture`. The pull request remains open for review;
this design does not constitute an accepted or implemented runtime.
