# Repository layout

This document describes the generated Youxia repository layout. It is the
canonical reference for where source code, tests, configuration, automation,
and long-lived documentation belong.

## Top-level tree

The tree below shows the generated repository structure. It is intentionally
compact and omits build output such as `target/`.

```plaintext
.
├── .cargo/
│   └── config.toml
├── .config/
│   └── nextest.toml
├── .github/
│   ├── cv005.toml
│   ├── dependabot.yml
│   └── workflows/
│       ├── act-validation.yml
│       ├── ci.yml
│       ├── mutation-testing.yml

│       └── release.yml

├── docs/
│   ├── contents.md
│   ├── developers-guide.md

│   ├── polonius.md

│   ├── repository-layout.md
│   ├── users-guide.md
│   └── ...
├── src/

│   ├── lib.rs
│   └── main.rs

├── tests/
│   ├── stub.rs
│   └── tooling/
├── scripts/
├── tools/
│   ├── mold/
│   └── nextest/
├── AGENTS.md
├── Cargo.toml
├── LICENSE
├── Makefile
├── README.md
├── clippy.toml
├── codecov.yml
└── rust-toolchain.toml
```

## Path responsibilities

- `.cargo/config.toml`: Configures Cargo defaults for local development,
  including Linux linker and code-generation settings.

- `.config/nextest.toml`: Bounds test runs and serializes compile-time tests.

- `.github/cv005.toml`: Supplies this repository's parameters to the shared
  coverage workflow contract checker.

- `.yamllint-estate.yml` and `.yamllint.yml`: Define the shared YAML
  policy and its repository overlay.

- `scripts/`: Contains explicit build-tool installers, read-only capability
  checks and the disposable coverage test-selection helper.

- `tools/mold/`: Pins mold's version and archive checksums.

- `tools/nextest/`: Pins the oldest `cargo-nextest` release whose profile
  accepts the keys this repository sets.

- `tests/tooling/`: Exercises public tooling boundaries in temporary Git
  repositories through the standard-library Python test runner.

- `.github/dependabot.yml`: Configures automated dependency update checks.

- `.github/workflows/act-validation.yml`: Installs `act` and runs
  `make test WITH_ACT=1` separately from main CI. No repository target consumes
  `WITH_ACT` yet, so this job currently repeats the main test suite.

- `.github/workflows/ci.yml`: Runs the generated project's continuous
  integration checks.

- `.github/workflows/mutation-testing.yml`: Runs scheduled mutation testing
  through the shared `mutation-cargo` reusable workflow.

- `.github/workflows/release.yml`: Builds and publishes binary release artefacts
  for the application flavour.

- `docs/`: Holds long-lived reference documentation, guides, style rules, and
  design material.

- `docs/contents.md`: Indexes the documentation set and should be updated when
  documentation files are added, renamed, or removed.

- `docs/youxia-design.md`: Explains the proposed Linux component architecture,
  compatibility, systemd resource topology, and runner/protocol recovery.

- `docs/adrs/`: Holds numbered architectural decision records. ADR 0001
  proposes independent runner services and remains subject to qualification.

- `docs/rfcs/`: Holds numbered proposals before architectural acceptance. RFC
  0001 defines the proposed native CLI and daemon; it does not describe
  capabilities implemented by the generated application.

- `docs/roadmap.md`: Holds the current Goals, Ideas, Steps, and Tasks (GIST)
  delivery sequence. Its task list supersedes the initial planning bundle.

- `docs/contracts/`: Holds proposed, separately parseable interface, storage,
  and configuration artefacts linked from the RFC. These are design inputs, not
  installed migrations or executable daemon configuration. The architecture
  also links the semantic runner transport contract and Linux resource profile
  here.

- `docs/execplans/`: Holds self-contained execution plans and their outcomes.

- `docs/lessons-on-daemon-design-and-hot-path-preservation.md`: Records the
  Comenq evidence and the resulting Youxia implementation requirements.

- `docs/users-guide.md`: Explains how to use the generated project and its
  public build and test commands.

- `docs/developers-guide.md`: Explains the contributor workflow and local
  tooling used to work on the generated project.

- `docs/polonius.md`: Records the Polonius toolchain contract, borrow-centric
  design guidance, and audited borrow-checker classifications.

- `docs/repository-layout.md`: Documents the repository tree and path
  responsibilities.

- `src/lib.rs`: Contains library support for application logic and doctested
  examples.

- `src/main.rs`: Contains the application entrypoint and top-level executable
  wiring.

- `tests/`: Holds integration and behavioural tests that exercise public
  behaviour.

- `tests/stub.rs`: Keeps the generated test directory valid until real tests
  replace it.

- `AGENTS.md`: Provides repository-specific working instructions for agents and
  contributors.

- `Cargo.toml`: Defines package metadata, dependencies, lint policy, and Cargo
  configuration.

- `LICENSE`: Records the project licence text.

- `Makefile`: Provides the public build, lint, test, coverage, and documentation
  validation commands.

- `README.md`: Introduces the project and gives the shortest useful
  getting-started path.

- `clippy.toml`: Configures Clippy lint behaviour that is not expressed directly
  in `Cargo.toml`.

- `codecov.yml`: Configures coverage reporting behaviour.

- `rust-toolchain.toml`: Pins the Rust toolchain channel and required
  components.

## Ownership boundaries

- Keep generated source code under `src/`. Add modules below `src/` when a
  feature grows beyond a small entrypoint or crate root.
- Keep black-box integration tests and externally observable workflow tests
  under `tests/`.
- Keep reusable documentation under `docs/`. Update `docs/contents.md` whenever
  a documentation file is added, renamed, or removed.
- Keep build and validation entrypoints in `Makefile`; prefer adding or
  extending a Make target over documenting an ad hoc command.
- Keep continuous integration workflow changes under `.github/workflows/` and
  dependency-update policy under `.github/dependabot.yml`.
- Do not commit generated build output such as `target/`, coverage artefacts, or
  local editor state.

## Updating this document

Update this document when the repository gains a new top-level directory, a new
long-lived documentation category, a new workflow file, or a changed ownership
boundary that would otherwise make the tree misleading.
