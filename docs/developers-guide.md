# Developer Guide

This guide explains the contributor workflow for the generated Youxia project.

## Local Workflow

Use `make all` as the public entrypoint for formatting, linting, and tests.
`make lint` runs YAML, Actions, and shell checks, then rustdoc, Clippy, and
Whitaker. `make test` prefers `cargo nextest run` and falls back to
`cargo test` when cargo-nextest is not available. `make check-fmt` verifies
Rust formatting with `cargo fmt --all -- --check`, and `make fmt` formats Rust
sources with nightly `rustfmt` and Markdown with `mdtablefix`. Both formatting
targets select tracked and untracked Markdown through Git; ignored files are
excluded. `make typecheck` type-checks without building via `cargo check`.
`make audit` derives the Rust workspace root with `cargo metadata`, logs
workspace member manifests, and runs `cargo audit` once from the workspace
root. PR CI skips `make audit` and the audit-only setup when `github.actor` is
`dependabot[bot]`; that keeps whole-lockfile advisories from blocking unrelated
Dependabot PRs while human PRs retain the audit gate. The compensating control
is `.github/workflows/audit.yml`, which runs weekly and can also be triggered
manually. `make coverage` uses `cargo llvm-cov` with `lld`.

GitHub Actions Act validation lives in `.github/workflows/act-validation.yml`.
The main `.github/workflows/ci.yml` workflow deliberately does not run
`make test WITH_ACT=1`; the separate Act workflow installs `act` and runs that
target in parallel. No Make target consumes `WITH_ACT` yet, so the Act job
currently repeats the main test suite rather than running container-backed
checks.

A scheduled `.github/workflows/mutation-testing.yml` workflow also runs
`cargo-mutants` via the shared reusable workflow, daily and on manual dispatch.
It is informational and does not gate pull requests. Dependabot keeps its
pinned reusable-workflow SHA current. See the user guide's "Scheduled Mutation
Testing" section for behaviour, and promote surviving mutants into new tests.

## Tooling

### Polonius borrow checker

This project compiles with the Polonius alpha analysis (`-Zpolonius=next`) on
the dated nightly pinned in `rust-toolchain.toml`. `.cargo/config.toml`
supplies the flag by default; Makefile recipes and workflows that set
`RUSTFLAGS` must re-state it because the environment value overrides Cargo
configuration. See [the Polonius policy](polonius.md) for the borrow-centric
API and audit-tag conventions.

Generated CI and coverage workflows, plus the release workflow rendered for
applications, pass this base flag through the shared `setup-rust` action's
`rustflags` input. Library renders do not include `release.yml`. The pinned
revision must expose that input, and coverage overrides must repeat the
selected base flag alongside their `lld` linker flag. Contract tests should
assert these inputs and combined flags.

Development builds use Cranelift for debug code generation. On Linux targets,
`.cargo/config.toml` configures clang to link with `mold` so debug builds link
quickly. Coverage generation uses `lld` because LLVM coverage tooling expects
LLVM-compatible linker behaviour.

`make all` runs every gate, so it needs the whole tool set installed before the
full generated workflow can run locally on Linux: `clang`, `lld`, `mold`,
`python3` 3.11 or newer, `uv`, `yamllint`, `actionlint`, ShellCheck,
`mdtablefix` 0.6.1, `whitaker`, `cargo-nextest` and `cargo-llvm-cov`.
`make lint` drives the YAML, workflow and shell linters as well as Whitaker,
`make check-fmt` checks the Git-selected Markdown through `mdtablefix --check`
and only `make fmt` rewrites it, and `make test-workflow-contracts` and
`make spelling` fetch their pinned tools with `uv`. The tooling contracts drive
the nextest lanes and `make coverage`, so the runner and the coverage tool are
needed for `make test-tooling`, and therefore for `make all`. `make audit`
additionally needs `cargo-audit`, and the optional `make markdownlint` and
`make nixie` targets need `markdownlint-cli2` and `nixie`; none of those three
belongs to `make all`.

### Repository check boundaries

The tooling import follows agent-template-rust PR #168 at commit
`206c82d52b276903e4f9f1df0ebf85a2938a99bb`. The imported shell helpers belong
to Make's build-tool boundary and its integration tests; use those entrypoints
rather than duplicate pin parsing or installation logic. `make test-tooling`
exercises public targets in temporary repositories with child-only
environments, including real Cargo routing and timeout failures. Its Git
fixtures sanitize an omitted environment, so a caller's `GIT_*` overrides
cannot redirect a child into the caller's repository. The workflow scanner sits
in `tests/tooling/workflow_lane.py`, which reads workflow text without a YAML
dependency; `tests/tooling/workflow_fixtures.py` holds the sample workflows and
`tests/tooling/test_workflows.py` the assertions that exercise them.

The suite is standard-library `unittest`. Example tests carry one case per
contract; `tests/tooling/test_properties.py` adds bounded generated cases from
a fixed seed for the invariants that hold across many inputs, such as a pin
that must round-trip through any padding. Generation stays in the standard
library because the harness takes no third-party dependency. Hypothesis would
replace the handwritten generators with shrinking and better distribution; it
is tracked in [issue #8](https://github.com/leynos/youxia/issues/8), which the
plan gates on owner approval.

`make check-build-tools` checks the pinned toolchain and components, clang, and
mold. `make check-rust-toolchain` checks only Rust; `make check-coverage-tools`
checks Rust, clang, and lld. These commands set `RUSTUP_AUTO_INSTALL=0` and
never install anything. Explicit `make install-build-tools` verifies pinned
mold archives before installing them under `BUILD_TOOLS_PREFIX` (default
`~/.local`) and installs the project's Rust components.
`make install-cranelift` repairs only that backend. The checker reports usable
mold version differences without failing.

`lint-yaml` and `lint-shell` enumerate tracked files with null-delimited Git
output and propagate enumeration errors. Stage new YAML and shell files before
validation. `lint-actions` runs actionlint with ShellCheck on workflow scripts.
Keep `.yamllint-estate.yml` byte-identical to the source policy; the local
overlay may extend it and add ignores only.

Make recipes compose `RUST_FLAGS`, Polonius and linker flags explicitly; an
ambient `RUSTFLAGS` is replaced, not appended. Cargo still selects Cranelift
through `profile.dev`. Coverage sets `CARGO_PROFILE_DEV_CODEGEN_BACKEND=llvm`
to override that profile and uses lld; changing `RUSTFLAGS` alone does not
switch the backend. Both hosted coverage lanes use the same override. The
toolchain pin is unchanged.

`.config/nextest.toml` limits ordinary tests to 180 seconds plus five seconds
of termination grace and the run to 90 minutes. Its `global-timeout` key
requires `cargo-nextest` 0.9.100 or newer, so that release is pinned in
`tools/nextest/VERSION` and `make check-build-tools` rejects an older runner.
The `ui` profile serializes nested Cargo tests, allowing 1,200 seconds plus ten
seconds of grace per test. `tests/compile_*.rs` targets run under
`make test-ui`; ordinary nextest and coverage exclude them. `make coverage`
requires cargo-nextest for that reason and stops with an actionable message
without it. The `make test` Cargo fallback runs them with ordinary tests and
does not provide nextest's bounds or group serialization. CI runs UI tests
before the shared coverage action, then uses `exclude-ui-targets.sh` to narrow
the default profile. That helper preserves source files and refuses an existing
conflicting filter; run it only in disposable workspaces.

`make test-workflow-contracts` invokes the shared CV-005 rules at the
Makefile's pinned revision, configured for this repository in
`.github/cv005.toml`. The publisher alone declares the `codescene` environment.
An administrator must restrict that environment to `main` and make its
CodeScene credential available there. Local contract checks inspect workflow
structure; they do not verify GitHub settings or hosted execution.

## Spelling policy

Markdown uses en-GB-oxendict spelling enforced by the shared
`typos-config-builder` gate. Run `make spelling`.

`typos.toml` is generated output. The gate regenerates it on every run from the
live shared estate dictionary and the `typos.local.toml` overlay, so a word
added to the shared dictionary needs no change here. Because the dictionary is
live, `typos.toml` must never be drift checked in continuous integration. Add
narrow repository-specific identifier, API, proper-name, or fixture exceptions
to `typos.local.toml`; hand-editing `typos.toml` is not supported and any edits
are overwritten on the next run.

### Security audit ignores

Security audit jobs may set `CARGO_AUDIT_IGNORES` for narrowly scoped RustSec
advisories that affect unused or tooling-only dependency paths. Keep each
ignore tied to a documented runtime impact analysis, and remove it when the
affected dependency leaves the graph or the project starts using the advised
runtime path.

## Workflow pins and Dependabot

Dependabot owns the upgrade of GitHub Actions and reusable workflows, including
calls into `leynos/shared-actions`. Contract tests that assert a caller's exact
commit SHA create a lockstep dependency: every time Dependabot opens a bump PR,
the test fails until a human edits the pinned constant to match. That defeats
the purpose of automated dependency updates and turns a routine bump into a
manual chore.

Generated projects keep their `setup-rust` pins in CI, coverage-main, audit,
and act-validation together at one shared full commit SHA. Application projects
also include the release workflow in that set; library projects do not render
the release workflow. Tests check that the references are consistently
full-SHA-pinned without asserting a literal SHA, leaving routine pin bumps to
Dependabot.

The narrow `RUSTFLAGS_PASSTHROUGH_REVISION` exception applies only while no
independent capability probe can establish that the shared `setup-rust` action
accepts the required `rustflags` input. In that case, assert the first revision
that provides the capability and document this boundary beside the test. Remove
the literal revision assertion once an independent capability probe is
available.

Contract tests may still verify the *shape* of a reusable-workflow caller. They
must not verify the specific SHA value.

- Do assert the workflow references the correct reusable workflow path.
- Do assert the ref is pinned to a full 40-character commit SHA, not a
  mutable branch such as `main` or `rolling`.
- Do assert the expected `on:` triggers, least-privilege `permissions:`, and
  the inputs the caller relies on.
- Do not hard-code the current SHA value as an expected string. Match it with
  a pattern instead.
- Do not fail a test purely because Dependabot bumped the pinned SHA.

```python
import re

SHA_RE = re.compile(r"^[0-9a-f]{40}$")

def test_uses_pinned_full_sha(caller_step):
    ref = caller_step["uses"].split("@")[-1]
    assert SHA_RE.match(ref), f"expected a 40-hex commit SHA, got {ref!r}"
```

If a workflow's behaviour genuinely depends on a feature only present from a
particular commit onwards, express that as a comment or a changelog note, not
as a test assertion on the SHA string. The sole exception is the
`RUSTFLAGS_PASSTHROUGH_REVISION` boundary above: until an independent probe can
confirm that `setup-rust` supports `rustflags`, document and assert the first
capable revision. Remove that literal revision assertion once the probe exists.
