# Import the native CLI and daemon design documents

## Purpose and outcome

Prepare a reviewable documentation pull request for Youxia that preserves the
initial Rust CLI and daemon architecture, updates the delivery roadmap with
Comenq's implementation lessons, and retains the proposed contracts beside the
documents that reference them. This work adds design material; it does not
implement the daemon or establish its proposed runtime guarantees.

## Context and source material

The source set consists of the 14 November 2026 Lody Rust reimplementation
plan, its later 85-task GIST roadmap, and the accompanying observation,
storage, and configuration contracts. The combined original plan also contains
an obsolete 67-task breakdown. The updated [roadmap](../roadmap.md) is the
single task list.

The initial architecture becomes
[RFC 0001](../rfcs/rfc-0001-native-rust-cli-and-daemon.md), with `Proposed`
status, stable section numbers, and explicit subsequent amendments. The
[lessons document](../lessons-on-daemon-design-and-hot-path-preservation.md)
distinguishes Comenq's merged repairs, reported deployment failure, open
proposals, and requirements inferred for Youxia.

Repository instructions in `AGENTS.md`, the
[documentation style guide](../documentation-style-guide.md), and the
[repository layout](../repository-layout.md) govern this work. The roadmap also
follows the `roadmap-doc` conventions in `leynos/df12-documentation-skills` at
commit `4a28c8953d3ccc2b5369b46cf042b53257d418de`. The technical-design and
df12-copy skills guide preservation, source attribution, and editing.

## Scope and invariants

- Preserve native Ishiban observation as the first useful slice and one hosted
  ACP agent with native Loro synchronization as the second.
- Keep native Flock reading and authoring as separate compatibility gates.
- Add first-spike IPC negotiation, shared-resource isolation, per-incarnation
  recovery, retry-policy persistence, cancellation-safe framing, and reserved
  progress capacity to the relevant contracts and acceptance criteria.
- Keep SQLite as the initial baseline. Qualify Turso without making that
  comparison a prerequisite for the two spikes.
- Preserve source evidence and distinguish proposed targets from measurements.
- Leave implementation code, dependencies, and upstream services outside this
  change. The only continuous-integration edit is the review follow-up repair
  recorded below: the existing `act-validation` job was missing the linker
  inputs that every other workflow already passes.

## Work sequence

1. Recover the exact source documents and inspect repository conventions.
2. Verify the cited Comenq findings and proposal statuses.
3. Import the architecture as an RFC and the contracts as separate files.
4. Update roadmap tasks and cross-references, retaining existing task identities
   wherever practical.
5. Add the lessons document and update documentation navigation.
6. Check the full diff, document structure, citations, links, dependency graph,
   and proposed contract syntax before opening the pull request.

## Acceptance and validation

The documentation set must have resolvable local links and section references,
unique roadmap identifiers, satisfiable dependencies, and an acyclic dependency
graph. Every task must include a design reference and observable acceptance
criteria. All implementation tasks remain unchecked.

Run `make fmt`, `make check-fmt`, `make markdownlint`, `make nixie`, and
applicable spelling checks. Repository instructions also name `make lint` and
`make test`; record unavailable prerequisites without claiming those gates
passed. Validate the JSON Schema against its declared meta-schema, parse the
TOML example, and execute the SQL in a temporary database. Exercise the changed
nullability and immutable-payload constraints as focused contract checks.

Keep transient verification output and environmental limitations in the pull
request or this execution record. Do not add unrelated generated-file changes
or claim runtime performance, crash durability, or interoperability evidence.

## Progress

- [x] Recover the source architecture, roadmap, and contracts.
- [x] Inspect repository conventions and establish the documentation branch.
- [x] Verify Comenq's source revision and merged/open distinctions.
- [x] Complete and cross-review the RFC, roadmap, and lessons document.
- [x] Finish structural and contract checks and record their outcomes.
- [x] Prepare the reviewable documentation branch with validation limits.
- [x] Apply the review follow-up: observation identity, act documentation, and
  the act-validation linker repair.

## Decisions and discoveries

- Keep the initial architecture's substantive sections and source baseline.
  Place later decisions in an explicit amendment section so reviewers can see
  how the proposal evolved.
- Preserve the observation schema identifier. Rename only local example paths
  and the proposed product surface where upstream compatibility is unaffected.
- Use ordinary rowid tables with explicit non-integer key nullability. The
  source draft used `WITHOUT ROWID` without workload measurements.
- Treat a restarted worker as unready until its incarnation reconciles durable
  state. Treat an old CLI/daemon peer as a compatibility question before
  opening an observation stream.

## Outcomes and validation record

The roadmap contains 90 tasks across 26 workstreams and five phases. All 85
previous task identifiers remain present. The additions are 1.4.1–1.4.2 for
negotiation and peer diagnostics, 2.2.6 for durable reconnect/refresh
eligibility, and 5.7.1–5.7.2 for optional Turso qualification. All tasks remain
unchecked. The dependency graph is acyclic, including the conditional support
gates. Neither ACP hosting nor Turso qualification blocks the observer.

The RFC retains the initial architecture's sections 1–12 and all 37 original
source references. Section 13 records subsequent amendments. Cross-review
corrected the ACP queue gate to precede the first hosted agent, and clarified
that early retry tests inject configuration-generation changes before the real
reload interface arrives in task 4.2.4.

Completed checks:

- Markdown formatting with `mdformat --wrap 80 --number`, followed by its check
  mode on changed documents.
- `make markdownlint`, using the installed Markdownlint executable override;
  this also ran the repository's pinned spelling and phrase gate. The generated
  `typos.toml` remained unchanged.
- Local Markdown links, heading anchors, ordered footnote references, task
  identifiers, design references, acceptance criteria, and dependency edges.
- JSON Schema meta-schema validation and eight positive/negative evidence
  examples; TOML parsing and example budget relationships.
- SQLite schema creation for all 11 tables, required key nullability, immutable
  command/outbox guards, transport-receipt constraints, foreign keys, and
  database integrity in a temporary database.
- `git diff --check` and review of the documentation-only change scope.

### Review follow-up

The first review round raised two Minor documentation findings, both fixed and
confirmed resolved on the published head.

- The RFC observation identity now uses
  `(profile_id, workspace_id, session_id)`, matching the `session_projection`
  primary key and the observation dimensions table.
- `docs/repository-layout.md` and `docs/developers-guide.md` now describe what
  the `act-validation` workflow executes, and the workflow passes
  `install-mold` and `install-clang-lld` to `setup-rust` so its cargo
  invocations can link debug builds.

### Current validation

With the pinned nightly toolchain, these gates ran sequentially on that head
and passed:

- `make check-fmt`, `make lint`, `make typecheck`, and `make test` (nextest
  plus doctests).
- `make markdownlint`, including the pinned spelling and phrase gate;
  `typos.toml` remained unchanged.
- `make nixie`, which validated both Mermaid diagrams.
- `actionlint` on the changed workflow.

The hosted `build-test` and `act-validation` jobs also pass.

An earlier draft of this record said `make fmt`, `make check-fmt`, `make lint`,
`make test`, and `make nixie` were unavailable. Those limits applied to that
earlier session only and are superseded by the results above.

Contract checks establish structural validity and selected constraints. Runtime
durability, interoperability, failure recovery, and performance remain proposed
implementation gates.
