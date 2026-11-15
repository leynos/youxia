# Import Rust-template repository checks

Status: COMPLETE

## Purpose / big picture

Bring the checks from agent-template-rust PR #168 into Youxia so local Make
targets and CI detect malformed YAML, invalid Actions, shell errors, missing
build capabilities, Markdown drift, unbounded nextest runs, and broken coverage
workflow contracts. Success means the public gates run these checks and
deliberately broken fixtures fail for the expected reasons.

Implementation was approved by the user on 2026-11-14 and is complete.

## Constraints

Work in `/mnt/c/Users/Payton/youxia` on `import-rust-template-repo-checks`,
starting at commit `4ea427a`.

Preserve the dated `nightly-2026-11-12` toolchain, Polonius analysis, current
Cranelift selection, Linux mold linking, and LLVM/lld coverage. Do not import
unrelated release changes, Dependabot grouping or automation, Copier machinery,
Netsuke, Ninja, or the template's nightly-date change. Do not change Rust
application APIs or add application dependencies.

Use the existing Makefile and shared action interfaces. Import the estate
yamllint base verbatim; the local overlay may extend it and add ignores only.
Preflight must not install tools or download a Rust toolchain. Installers are
explicit commands, never dependencies of validation targets.

Keep the six shared reference documents and two tagged dependency guides
unchanged. Formatting existing project guides is permitted where the new
Markdown formatting gate exposes baseline drift. Never edit generated
`typos.toml` manually.

## Tolerances

Exclude this ExecPlan from the following budgets. Allow at most 24 changed
files: up to 1,200 added or changed executable/test lines, 450 configuration
lines, and 250 prose lines. Measure these categories independently using
`git diff --numstat` and review changed lines, including deletions. Imported
scripts count towards executable lines. Spare capacity cannot offset another
category's overrun.

Allow only the tools already selected upstream: yamllint, actionlint,
shellcheck, mdtablefix, nextest, the pinned shared CV-005 checker, and their
existing runtime dependencies. A standard-library Python test harness needs no
new application crate or package manifest. Stop for approval before adding any
other dependency, changing toolchain/backend policy, weakening a shared
contract, or exceeding a budget. Escalate after three unsuccessful attempts at
the same failing milestone or two hours on one milestone.

## Risks

The source PR is open and can change. Severity medium, likelihood high. Import
from its inspected head, not a moving branch, and record any later source
change before using it.

Nextest on this host is 0.9.116. Severity medium, likelihood medium. Exercise
the actual nextest configuration before adopting it; document and explicitly
provision an adequate version if required rather than silently dropping bounds.

The coverage linker `ld.lld` was not found on PATH during reconnaissance.
Severity medium, likelihood high. The coverage preflight must report this; use
the documented OS installation or an existing versioned linker through a narrow
PATH adjustment during validation. Never turn a missing linker into a passing
coverage gate.

The shared checker requires the publisher's `codescene` environment. Severity
medium, likelihood medium. Import the workflow declaration and document the
required main-only environment protection. Repository settings, secret moves,
publishing, and remote dispatch are outside this change. Report unverified
hosted protection separately from local checker success.

A new formatting gate reveals pre-existing Markdown wrapping. Severity low,
likelihood high. Limit normalization to files selected by the same Git-aware
formatter; inspect the diff and preserve vendored guides.

## Progress

- [x] (2026-11-14 22:47Z) Inspect PR #168, current Makefile/workflows,
  build flags, tool availability, and shared checker documentation.
- [x] Draft a bounded import and verification plan.
- [x] Obtain explicit plan approval.
- [x] M1: add failing tooling integration tests and import lint/preflight gates.
- [x] M2: integrate bounded tests, UI selection, Markdown and CV-005 gates.
- [x] (2026-11-14 23:57Z) M3: provision CI prerequisites, document contracts,
  and pass final validation. Commit the validated import as one coherent change.

## Surprises & discoveries

PR #168 changes 71 files, including parent-template tests and release policy.
Youxia is a generated application, so importing the entire PR is inappropriate.

Youxia currently has no tooling harness, nextest configuration, YAML policy, or
workflow-contract configuration. Its Rust test suite contains one stub and one
doctest. There are no `tests/compile_*.rs` targets.

The build already selects Cranelift through Cargo configuration. The upstream
PR also changes frontend threading and backend flag composition; those changes
are not necessary to import its checks and are excluded.

Coverage initially failed because the unchanged Cargo development profile
selects Cranelift independently of RUSTFLAGS. Make coverage and both hosted
coverage steps now explicitly select LLVM through the profile environment
override. A real application fixture rejects a Cranelift mutation and requires
non-zero function execution counts in the resulting LCOV report. This restores
the existing documented LLVM coverage policy without changing development.

The pinned Rust toolchain supplies lld under its target-specific gcc-ld
subdirectory. Local coverage passed with that directory prepended to PATH.
Nextest 0.9.116 accepts both imported profiles; no runner upgrade was needed.

## Decision log

- 2026-11-14: Pin the reference to PR head
  `206c82d52b276903e4f9f1df0ebf85a2938a99bb`; base
  `a377f65bb50a50b9cd803a6ed650ab61591b9c58`. This preserves a reproducible
  source while the PR remains open.
- 2026-11-14: Import generated-project checks and supporting repair commands.
  Reuse upstream shell helpers rather than introduce another preflight
  abstraction. Their permitted callers are Make targets and tooling tests.
- 2026-11-14: Keep the shared workflow rules in their upstream package.
  Configure Youxia through `.github/cv005.toml`; do not copy or weaken rules.
- 2026-11-14: Await approval before implementation, as required by the
  ExecPlan skill's approval gate.

- 2026-11-14: Restore the existing LLVM coverage policy with
  CARGO_PROFILE_DEV_CODEGEN_BACKEND=llvm. Keep the Cargo development profile
  and compiler flags unchanged; document this representation difference.
- 2026-11-14: Keep the index's existing plan link; no document was added or
  renamed during implementation. Normalize only project Markdown and YAML
  whitespace exposed by the new gates, including release.yml whitespace.

## Outcomes & retrospective

Local implementation, negative controls and final review are complete. Hosted
execution and environment protection are outside scope. The completed change
affects 24 non-plan files: 1,108 executable/test changed lines, 143
configuration lines and 230 prose lines, counting additions and deletions
independently of this plan. No budget was exceeded. No Rust API, toolchain pin,
development backend or shared contract was changed. All imported shell scripts
and the estate YAML policy match their upstream source bytes.

## Context and orientation

`Makefile` owns public validation. `.cargo/config.toml` and
`rust-toolchain.toml` own compiler defaults. `.github/workflows/ci.yml` checks
PRs; `coverage-main.yml` owns CodeScene upload and the coverage baseline. A
baseline is the saved coverage measurement used for comparisons.

CV-005 is the shared contract separating PR coverage from main-only CodeScene
publication. Its checker inspects workflow structure; it does not establish
that hosted jobs ran or repository environment protections exist.

`docs/contents.md` indexes project documents. Update `docs/developers-guide.md`
for internal tooling boundaries, `docs/users-guide.md` for public commands, and
`docs/repository-layout.md` for added paths. There is no roadmap or primary
design document in this checkout; do not invent a completed roadmap item.

## Conformance basis

The source is
[agent-template-rust PR #168]( https://github.com/leynos/agent-template-rust/pull/168),
at the head above. Use its `template/Makefile.jinja`, `template/scripts/`,
`template/.config/nextest.toml`, `template/.yamllint*.yml`,
`template/.github/cv005.toml.jinja`, and rendered workflow changes.

The shared checker is pinned upstream at
`38905b4b2caec5b049438e6dc3f3f6b36c04d2df`, in
`leynos/shared-actions/packages/cv005-contracts`. Its README defines the
coverage and environment contract. Local governing references are `AGENTS.md`,
`docs/polonius.md`, and the documentation style guide. No separate terms of
reference or accepted design ADR exists for this import.

Trace the gaps as follows: lint/preflight -> M1 -> failing fixture checks;
bounded tests/Markdown/workflow policy -> M2 -> real public target execution;
CI prerequisites/documentation -> M3 -> actionlint and complete local gates.

## Verification plan

Use executable integration tests in `tests/tooling/`, run by
`python3 -m unittest discover -s tests/tooling -v` and a public
`make test-tooling` target included in `make all`. Keep modules below 400
lines. Use temporary Git repositories, child-process environments and fake
executables; never mutate the harness process environment.

1. Lint propagation: a tracked malformed YAML file, a workflow with an invalid
   action expression, and a shell script containing a ShellCheck defect must
   fail their real public targets. Valid fixtures, paths containing spaces, and
   an empty shell selection must succeed. A missing tool and failed Git
   enumeration must fail with diagnostics. These cases reject a no-op gate,
   swallowed pipeline errors, and unsafe word splitting.
2. Read-only preflight: fake rustup records arguments and checks
   `RUSTUP_AUTO_INSTALL=0`. Missing toolchain/components/linkers fail; a usable
   mold differing from the pin reports the difference without failing, as
   upstream specifies. No check may invoke install/add or curl. Test explicit
   installer checksum rejection with a local fake download; no host-wide tool
   installation is needed.
3. Test routing: a temporary minimal Cargo project with a normal integration
   target and `compile_probe` must run each in its intended lane. Empty UI
   discovery must be an explicit success. The Cargo fallback must retain all
   tests. The exclusion helper must preserve source files, be idempotent, and
   refuse a conflicting default filter instead of replacing it silently.
4. Bounds: use nextest to parse/list the imported profiles and a disposable
   hanging test with temporarily shortened limits to demonstrate termination.
   Assert a non-zero result for the intended timeout and bound the outer
   subprocess too. Configuration inspection complements actual termination; it
   does not substitute for it.
5. Markdown: in a temporary Git repository, an untracked document with bad
   wrapping must fail `check-fmt`, then pass after `fmt`; ignored documents
   stay unselected. Exercise real mdtablefix selection.
6. Workflow policy: run the pinned checker on Youxia and on a temporary copy
   with the PR lane leaking the CodeScene secret. The latter must fail the
   intended contract; restoring the fixture must pass. Do not test the shared
   package's private implementation or freeze literal action SHAs.

These are finite configuration and process contracts; no unbounded proof or
model checker is justified. Assumptions are documented tool interfaces, Bash
and Git behaviour, executable access, and Python 3.11+ for `tomllib`. Hosted
runners and environment settings remain outside local evidence.

## Plan of work

M1 imports `scripts/build-tools-common.sh`, `check-build-tools.sh`,
`install-build-tools.sh`, and `tools/mold/{VERSION,SHA256SUMS}` from the pinned
source. Add executable modes. Add the two yamllint files and public `lint-yaml`,
`lint-actions`, `lint-shell`, and capability targets. Connect checks to the
matching existing build, lint, test, formatting, typecheck and coverage
commands. Retain current compiler flag composition. Add failing tests first,
then implement enough to pass each boundary.

M2 adds `.config/nextest.toml`, `scripts/exclude-ui-targets.sh`, and `test-ui`.
Import the compile-target convention and exclusions for nextest and coverage
without dropping Cargo-fallback tests. Add Git-aware mdtablefix format/check
commands. Configure `.github/cv005.toml` for `leynos/youxia` and the existing
lcov selection. Add `test-workflow-contracts` and include it and the UI/tooling
lanes in `make all`. Use the exact shared checker version from the source PR.

M3 updates CI to install mdtablefix and YAML lint tools before the gates that
need them, use the shared Whitaker installer, and run the workflow and tooling
checks. Run UI tests before coverage in both CI and the publisher, followed by
the idempotent exclusion helper. Add the publisher environment declaration and
any minimal workflow corrections required by the unchanged shared checker.
Preserve action SHA shape checks and the existing coverage publisher ownership.
Do not add unrelated delivery workflows.

Update the three project guides and the index. Document effective inherited
flags, backend/linker routes and why coverage differs; describe installer
versus checker effects, nextest limits and Cargo fallback limitations. Resolve
only actual failures exposed by the imported gates.

## Milestones and plateaus

M1 is complete when real lint targets reject seeded faults and the preflight
reports missing capabilities without mutation. M2 is complete when ordinary, UI
and fallback routes retain the intended tests, timeout negative controls
terminate, Markdown drift fails, and the shared workflow checker passes. M3 is
complete when CI ordering matches the validated local commands, documentation
is accurate, and the full gates pass.

At each boundary confirm the assigned contracts, unchanged compiler policy, no
unapproved dependency or trust boundary, and current trace links. Revert only
the milestone's own changes if recovery is needed. No source API compatibility
layer is required; this is unreleased repository tooling.

## Concrete steps

Run from the repository root after approval. Establish red tests before editing
the gates, then rerun focused tests through red, green, and cleanup. Capture
command exit codes and concise diagnostics in this plan.

```sh
python3 -m unittest discover -s tests/tooling -v
make check-build-tools check-rust-toolchain check-coverage-tools
make lint-yaml lint-actions lint-shell
make test-tooling test-ui test-workflow-contracts
make fmt
make check-fmt lint typecheck test test-ui test-workflow-contracts
make markdownlint nixie
make coverage
git diff --check
```

Expected results are successful exits for valid fixtures and the real checkout,
non-zero exits for each seeded failure, explicit no-op reporting for Youxia's
empty UI selection, and a non-empty `lcov.info` after coverage.

## Validation and acceptance

All six verification obligations must have red/green evidence. Run the complete
public gates after final edits, inspect the complete diff and all file sizes,
then commit coherent milestones only after their checks pass. Do not claim
hosted success from static workflow checks. Do not mark this plan complete
until every acceptance item has evidence or an approved scope amendment.

## Idempotence and recovery

Checks are read-only except build outputs, coverage reports and the established
generated spelling configuration. Run coverage exclusions only in disposable CI
workspaces or tooling fixtures; restore the local nextest configuration after
manual trials. Installers require explicit invocation and may update the chosen
local prefix; never exercise their successful host installation in tests. Clean
up temporary fixtures even after a failing assertion.

## Artefacts and notes

Keep transient logs outside the repository. Record source provenance and
integration decisions in the developer guide. No new standalone architecture
layer or ADR is required for this mechanical tooling import.

## Interfaces and dependencies

The public interface is Make targets and the imported shell entrypoints.
`CHECK_BUILD_TOOLS`, `CHECK_RUST_TOOLCHAIN` and `CHECK_COVERAGE_TOOLS` remain
overridable commands as upstream specifies. Use upstream mdtablefix 0.6.1
provisioning and the PR's full-SHA shared action pins. Keep current Rust
dependencies unchanged.

Revision note (2026-11-14): Draft after inspection of the pinned upstream PR,
Youxia's existing flags and workflows, and local tool availability.
Implementation started after explicit user approval.

Revision note (2026-11-14): M1 and M2 passed their integration checks. The
first suite failed against missing baseline Make targets. The baseline lane
tests failed because compile targets ran with ordinary tests and no UI lane
existed. The shared checker first failed for missing repository configuration.
All 17 current tooling tests pass, including per-test and global timeout
termination, checksum rejection, linker failures, lane selection and a PR
credential leak. Coverage passed after the explicit LLVM override; the
wrong-backend mutation fails with the LLVM-only instrumentation diagnostic.
Final review passed.

Revision note (2026-11-14 23:57Z): Mark complete after `make all typecheck`,
`make markdownlint nixie`, Ruff formatting/lint checks and `git diff --check`
passed. The suite contains 17 tooling tests, one Rust integration test and one
doctest. `make coverage` produced LCOV using the pinned toolchain's lld on
PATH. The pre-existing redundant-homepage Cargo manifest warning remains; all
commands succeed. No hosted workflows, secrets or environment settings were
modified remotely. The existing untracked nohup.out is user-owned and remains
untouched; generated Cargo.lock and lcov.info are excluded from this commit.

Revision note (2026-11-15): The Windows-mounted checkout ignores filesystem
mode differences. Record executable script modes explicitly in Git and verify
them by exporting the index to a temporary Linux directory. Both build and
toolchain preflights pass from that export. No source logic changed.
