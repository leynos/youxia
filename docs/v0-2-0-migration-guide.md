# Migration guide: v0.1.0 to v0.2.0

## Who should read this

Read this guide if you rendered a Youxia project before v0.2.0 and keep its
`Makefile`, `.config/nextest.toml`, `scripts/`, `tests/tooling/` and `tools/`
pins alongside your own code. The release imports the Rust-template repository
checks, so the public gates now lint YAML, GitHub Actions workflows and shell
scripts, format Git-selected Markdown, and separate compile-time test targets
into their own lane. A project that consumes the rendered crate without keeping
those build files has nothing to migrate.

## Impact at a glance

| Priority | Area           | What to do                                                                                                                               |
| -------- | -------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| Required | Gate tools     | Install `yamllint`, `actionlint`, ShellCheck, `mdtablefix` 0.6.1, `uv` and Python 3.11 or newer.                                         |
| Required | Test lanes     | Run `make test-ui` for `tests/compile_*.rs`, which `make test` now leaves to that lane.                                                  |
| Required | Build files    | Copy the v0.2.0 `Makefile`, `.config/nextest.toml`, `scripts/`, `tests/tooling/` and `tools/`.                                           |
| Required | Test runner    | Install `cargo-nextest` 0.9.100 or newer; the tooling contracts drive the nextest lanes and `make coverage` refuses to start without it. |
| Required | Coverage tools | Install `cargo-llvm-cov`; the tooling contracts run `make coverage`, so `make all` needs it.                                             |
| Optional | CodeScene      | Adopt the CodeScene upload workflow if the project publishes code health.                                                                |

_Table 1: Obligations when moving from v0.1.0 to v0.2.0._

## 1. Install the gate tools

`make lint` now checks configuration before it builds documentation:

- `yamllint`, installed with `uv tool install yamllint`.
- `actionlint`, installed from its release page.
- ShellCheck, installed with the operating system's package manager.
- `mdtablefix` 0.6.1 or newer, used by `make fmt` and `make check-fmt`.
- `uv` and Python 3.11 or newer, used by the tooling tests.

`make check-build-tools` reports missing linkers and toolchains, and the
individual `make check-rust-toolchain` and `make check-coverage-tools` targets
narrow that report. Checks never install anything; `make install-build-tools`
and `make install-cranelift` are the explicit install steps.

## 2. Run the compile-time lane separately

Under `cargo-nextest`, the default profile excludes `tests/compile_*.rs` so
that compile-fail contracts cannot flood the ordinary run. Run the lane
explicitly:

### Before

```sh
make test
```

### After

```sh
make test
make test-ui
```

An empty lane is an explicit success, so the extra target is safe in a project
with no compile-time contracts.

## 3. Read what each target now runs

An existing target can fail on something it never checked before, so read the
row for every target the project already calls.

| Target           | New behaviour                                                                                                          |
| ---------------- | ---------------------------------------------------------------------------------------------------------------------- |
| `make all`       | Runs formatting, linting, ordinary and compile-time tests, the tooling contracts, the workflow contracts and spelling. |
| `make lint`      | Checks YAML, GitHub Actions workflows and shell scripts before documentation, Clippy and Whitaker.                     |
| `make check-fmt` | Verifies the Rust formatting and the Git-selected Markdown, including untracked files, through `mdtablefix`.           |
| `make fmt`       | Rewrites the same Rust and Markdown sources in place.                                                                  |
| `make test`      | Excludes `tests/compile_*.rs` under cargo-nextest; run `make test-ui` for those targets.                               |
| `make coverage`  | Sets LLVM code generation and excludes the compile-time targets; it fails when cargo-nextest is absent.                |

_Table 2: Targets whose behaviour changed in v0.2.0._

`make all` needs both tools installed. The Rust lanes are forgiving:
`make test` and `make test-ui` fall back to `cargo test`, which runs the
compile-time targets in the ordinary lane and offers no per-test timeout.
`make test-tooling` is not: although it is a standard-library Python suite, it
drives `cargo nextest run` and `make coverage` as contracts, so an absent
`cargo-nextest` or `cargo-llvm-cov` fails the suite and therefore `make all`.
`make coverage` also refuses to start on its own without the runner.

## 4. Copy the v0.2.0 build files

The gates read files that did not exist in v0.1.0. Copy them from the rendered
project rather than retyping them, because the checks assert their layout:

- `Makefile`, which adds `check-build-tools`, `check-rust-toolchain`,
  `check-coverage-tools`, `install-build-tools`, `install-cranelift`,
  `test-tooling` and `test-workflow-contracts`, and makes `make all` run the
  compile-time lane, the tooling tests and the workflow contracts.
- `.config/nextest.toml`, which defines the ordinary, UI and timeout profiles.
- `scripts/`, which holds the build-tool installer and checker, the shared pin
  reader and the coverage exclusion.
- `tests/tooling/`, which holds the integration contracts `make test-tooling`
  runs; without it that target has nothing to discover.
- `tools/mold/` and `tools/nextest/`, which hold the pinned versions and the
  mold checksums.
- `.yamllint.yml` and `.yamllint-estate.yml`, which define the YAML lint policy
  that `make lint-yaml` applies. `make lint-yaml` names no configuration file,
  so yamllint discovers `.yamllint.yml` in the working directory; without these
  files the target still passes, but it lints with yamllint's built-in defaults
  instead of the repository policy.

## 5. Keep coverage on nextest

`make coverage` now selects LLVM code generation and excludes the compile-time
targets from the instrumented run. Only nextest can apply that exclusion, so
the target fails when the runner is absent instead of silently instrumenting
the contract targets.

## What does not need to change

The crate layout, the lint and Rustdoc policy in `Cargo.toml` and
`clippy.toml`, the Polonius flags, the pinned toolchain channel, and the
rendered application or library sources are unchanged. Existing tests keep
running through the ordinary lane.

## Migration checklist

- [ ] Install `yamllint`, `actionlint`, ShellCheck, `mdtablefix` 0.6.1, `uv`
      and Python 3.11 or newer.
- [ ] Copy the v0.2.0 `Makefile`, `.config/nextest.toml`, `.yamllint.yml`,
      `.yamllint-estate.yml`, `scripts/`, `tests/tooling/` and `tools/`.
- [ ] Install `cargo-nextest` 0.9.100 or newer and `cargo-llvm-cov`, which the
      tooling contracts and `make coverage` need.
- [ ] Add `make test-ui` to local and hosted validation.
- [ ] Run `make check-build-tools` and resolve what it reports.
- [ ] Run `make all` and fix every diagnostic rather than suppressing it.

## Common errors and fixes

- **Error:**
  `yamllint is required to lint YAML; install it with: uv tool install yamllint`
  - **Fix:** run the printed install command, then rerun `make lint`.
- **Error:**
  `actionlint is required to lint workflows; install it from
  https://github.com/rhysd/actionlint`
  - **Fix:** install actionlint and ShellCheck, which actionlint invokes.
- **Error:** `coverage requires cargo-nextest: only nextest can exclude the`
  - **Fix:** install `cargo-nextest`; the excluded targets belong to
    `make test-ui`.
- **Error:** `cargo-nextest 0.9.99 is older than the pinned 0.9.100`
  - **Fix:** upgrade the runner. The profile sets `global-timeout`, which that
    release added.
- **Error:**
  `make spelling needs a Git repository: the gate enumerates tracked files
  with git ls-files. Run: git init && git add -A`
  - **Fix:** initialize the repository and stage the rendered files.
- **Error:**
  `make spelling found no tracked files: the gate enumerates tracked files
  with git ls-files. Run: git add -A`
  - **Fix:** stage the files, then rerun the gate.
