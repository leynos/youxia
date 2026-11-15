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
- 2026-11-15: Review feedback requires the public `make test` lane to succeed
  and the guidance to be accurate. Provision mold in Act validation, correct the
  `make test` / `make test-ui` split in `AGENTS.md` and the migration steps,
  and record the resulting budget overruns. The owner's instruction to fix the
  underlying issues and merge is the approval the tolerance requires. The
  previous "24 non-plan files" outcome measurement was wrong and is corrected
  here.
- 2026-11-15: The first full review found that coverage could drop the checked
  linker path and silently instrument compile-time targets, that the fixture
  environment could carry the caller's Git index, that the mold check searched
  the whole workflow rather than the job running `make test`, and that the
  shared test helpers lacked annotations. Fix all four with regression
  fixtures. The resulting executable-line overrun is recorded in Outcomes under
  the same owner-instruction approval.
- 2026-11-15: Rebase onto `main` at `2f9b01e`, which merged the native daemon
  RFC, roadmap and contract documents through PR #6. Resolve
  `docs/repository-layout.md` by keeping main's wrapping and inserting this
  import's path entries, and keep main's
  `.github/workflows/act-validation.yml`, which already installs mold and
  clang/lld. This branch therefore contributes only the workflow test and the
  harness changes from its linker commit, and that commit's message says so.
  Re-measure Outcomes against the new base.

## Outcomes & retrospective

Local implementation, negative controls and final review are complete. Hosted
execution and environment protection are outside scope. The completed change
affects 32 non-plan files: 1,376 executable/test changed lines, 314
configuration lines and 991 prose lines, counting additions and deletions
independently of this plan and classifying `tests/` and `scripts/` as
executable/test, other non-Markdown build and workflow files as configuration,
and Markdown as prose. The 24-file, 1,200-executable-line and 250-prose-line
budgets are exceeded by eight files, 176 lines and 741 lines; configuration
stays within its budget. The import's own lint-formatting repairs account for
one extra file. The remaining growth is the mechanical `mdtablefix` reflow of
the five documents `main` merged after this branch left its original base (RFC
0001, the roadmap, the daemon-design lessons, its execplan and the contracts
README) together with the two shared documents the formatter also rewrapped; no
prose was added or removed. The 2026-11-15 review instructions to fix the
underlying failures provisioned the Act validation linkers, which `main` now
supplies, corrected the test-lane guidance, and required the coverage guard,
per-job workflow check, fixture environment filtering and helper type
annotations that the first full review identified. Reverting a required
formatting repair, leaving hosted CI red, keeping inaccurate guidance, or
leaving those defects unfixed would each defeat the import, so the owner's
instruction is recorded as the approval the tolerance requires. No Rust API,
toolchain pin, development backend or shared contract was changed. All imported
shell scripts and the estate YAML policy match their upstream source bytes.

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

Revision note (2026-11-15 review): Hosted Act validation failed because
`make test` gained the `check-build-tools` prerequisite while that workflow's
`setup-rust` step installed no mold linker. Provision the pinned mold there and
add a tooling test requiring any workflow that runs the public test lane to
install it. The tooling harness now clears `BASH_ENV`, because its startup file
can rewrite `PATH` inside Make recipes and shadow fixture tools, and the
coverage fixture's cold compile receives a bounded multi-minute timeout.
Format, lint, typecheck, unit, tooling, workflow-contract, Markdown and Mermaid
gates pass again.

Revision note (2026-11-15 assessment): CodeRabbit's completeness assessment
raised three items. The file budget was already exceeded and misrecorded; the
corrected measurement is 27 non-plan files with 259 prose lines, recorded in
Outcomes with the owner-instruction approval basis. `AGENTS.md` and the user
guide now describe the `make test` / `make test-ui` split, and the documented
nextest probe carries `RUSTUP_AUTO_INSTALL=0` so it cannot install a toolchain
while selecting the runner. `make coverage` ran against this checkout with the
pinned toolchain's bundled lld on `PATH` and wrote a non-empty `lcov.info` (577
bytes); the stub test exercises no library function, so its three records
report zero hits.

Revision note (2026-11-15 formal review): The coverage recipe prepends the
checked tools directory to `PATH` and refuses to run without nextest, because
only nextest can exclude compile-time targets. The tooling harness drops
`GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE` and object-directory overrides
before initializing a fixture, and its shared helpers carry annotations. The
mold check inspects each job that runs `make test`, with a two-job negative
fixture. The user guide lists `cargo-nextest` and `cargo-llvm-cov` as full-gate
prerequisites. The tooling suite now contains 21 tests.

Revision note (2026-11-15 rebase): `main` advanced to `2f9b01e` while the
branch awaited review, so the branch was rebased and its commits replayed. Two
conflicts were resolved by keeping main's content and adding this import's own
entries: `docs/repository-layout.md` gains the path list for the new
configuration, scripts and tooling tests, and
`.github/workflows/act-validation.yml` keeps main's `install-mold` and
`install-clang-lld` inputs. That workflow already satisfied the earlier
requirement, so this branch contributes the tooling test that enforces it
rather than a duplicate provisioning change.

Revision note (2026-11-15 post-rebase gates): The formatting gate rejected the
documents `main` merged after this branch's original base, because `mdtablefix`
replaces `mdformat` and enforces its own wrapping, list numbering and emphasis
rules. One `make fmt` pass reformatted them, and that reflow is committed on
its own. The ordinary lane test then exceeded the harness's one-minute default:
each fixture compiles from scratch and shares the host's compiler-admission
queue, so the bound measured queue latency rather than the lane.
Compile-carrying lanes now receive a five-minute bound, matching the coverage
fixture. After both repairs the measurement is 32 non-plan files, 1,325
executable/test lines, 143 configuration lines and 991 prose lines. The
CodeScene delta then reported the tooling harness's `make` helper for excess
arguments, so its expected status, bound and environment now travel as a
`CommandOptions` value object shared with `run_command`. Every gate passes on
this tree.

Revision note (2026-11-15 follow-up): CodeRabbit's reconciliation reply found
two remaining gaps. `GIT_COMMON_DIR` now joins the Git overrides the harness
strips, so a fixture cannot commit into the caller's object store, and the
regression check asserts the object-directory entries alongside the index. The
mold check now requires an installation before every test step rather than
anywhere in the job, with a reversed-order fixture covering a late install. The
tooling suite contains 22 tests, and the measurement is 32 non-plan files,
1,424 executable/test lines, 143 configuration lines and 991 prose lines.

Revision note (2026-11-15 second follow-up): The review of the follow-up head
found four more gaps. `CARGO_ENCODED_RUSTFLAGS` and
`CARGO_ENCODED_RUSTDOCFLAGS` now join the stripped build settings, because
Cargo gives the encoded spellings precedence. Timeout cleanup asks with
`SIGTERM` before escalating to `SIGKILL`, so nextest can stop the tests it
started in their own process groups. The timeout fixture rejects a run-wide
"global timeout" when it expects per-test termination. The workflow check reads
commands inside `run: |` blocks as well as inline `run:` lines, with a
block-scalar fixture. The tooling suite contains 23 tests, and the measurement
is 32 non-plan files, 1,376 executable/test lines, 314 configuration lines and
991 prose lines.

Revision note (2026-11-15 nextest pin): The review of the SIGTERM fix asked for
a pinned `cargo-nextest` release. The nextest changelog places the relevant
floor later than the review suggested: `global-timeout`, which
`.config/nextest.toml` sets, arrived in 0.9.100, while 0.9.87 changed Windows
cancellation and a cancellation race. `tools/nextest/VERSION` therefore pins
0.9.100, `scripts/check-build-tools.sh` rejects an older runner in the full and
coverage modes, and the users' and developers' guides state the floor.
`cargo-nextest` remains optional: an absent runner keeps the `cargo test`
fallback. The tooling suite contains 25 tests.

Revision note (2026-11-15 termination grace): Review of the nextest pin found
that the harness waited exactly the longest configured grace period, so it
could kill nextest at the moment nextest escalates. `GRACEFUL_STOP_SECONDS` now
allows fifteen seconds, and a contract test parses every `grace-period` in
`.config/nextest.toml` and requires the harness wait to exceed the longest by
at least five seconds. An end-to-end fixture installs a `SIGTERM` handler that
ignores the signal, which forces nextest's own escalation, and asserts that the
fixture writes no survival marker. The fixture reports readiness before the
harness signals it, so the test cannot pass merely because the runner had not
started. One measured detail is recorded here because it shaped the fixture:
nextest aborts a test binary that dies to `SIGTERM` immediately and reports any
child that ignores the signal as a leaked handle, so the test process itself
has to ignore the signal for the grace and `SIGKILL` path to run at all. The
tooling suite contains 27 tests.
