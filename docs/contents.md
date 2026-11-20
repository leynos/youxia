# Documentation contents

[Documentation contents](contents.md) is the index for Youxia's documentation
set.

## Architecture and delivery

- [Youxia architecture design](youxia-design.md) defines the proposed Linux
  components, compatibility boundaries, systemd supervision, resource policy,
  and separate process, byte, and ACP recovery guarantees.
- [ADR 0001: Linux supervision and agent transport](adrs/adr-0001-linux-supervision-and-agent-transport.md)
  records the proposed independent runner services and daemon protocol boundary.
- [ADR 0002: ACP host port and adapters](adrs/adr-0002-acp-host-port-and-adapters.md)
  records the application-owned port, provisional SDK path, and later Magitek
  replacement.
- [RFC 0001: Native Rust CLI and daemon](rfcs/rfc-0001-native-rust-cli-and-daemon.md)
  preserves the initial architecture and proposes the Youxia reliability
  amendments, compatibility gates, and rollout boundaries.
- [Youxia roadmap](roadmap.md) sequences the proposed work from native Ishiban
  observation through ACP hosting, fleet operation, and deferred compatibility.
- [Lessons on daemon design and hot-path preservation](lessons-on-daemon-design-and-hot-path-preservation.md)
  connects Comenq's implementation evidence to Youxia's contracts and tests.
- [Proposed implementation contracts](contracts/README.md) explains the
  observation schema, storage model, and configuration example that accompany
  RFC 0001.
- [Runner transport contract](contracts/arun-transport.md) defines private
  daemon and runner semantics for attachment, byte replay, write receipts, and
  recovery.
- [ACP host port contract](contracts/acp-host-port.md) defines adapter
  ownership, capability and evidence semantics, experimental profiles, and
  shared witnesses.
- [Design-documentation execution plan](execplans/add-cli-and-daemon-design-documents.md)
  records the scope, provenance, and verification of this documentation import.
- [Linux architecture execution plan](execplans/add-linux-component-architecture.md)
  records this design's scope, evidence, review, and validation.
- [ACP host port execution plan](execplans/define-acp-host-port-and-runner-spike.md)
  records the paired design amendment and early local runner/SDK spike path.

## Project guides

- [User guide](users-guide.md) explains how to use the generated project and its
  public build and test commands.
- [Developer guide](developers-guide.md) explains the local workflow and
  implementation tooling for contributors.
- [v0.1.0 to v0.2.0 migration guide](v0-2-0-migration-guide.md) carries a
  previously rendered project across the checks-import release boundary.
- [Repository layout](repository-layout.md) explains the generated project's
  top-level files, directories, and ownership boundaries.
- [Documentation style guide](documentation-style-guide.md) defines the
  spelling, structure, Markdown, Architecture Decision Record (ADR), Request
  for Comments (RFC), and roadmap conventions used by this documentation set.
- [Polonius borrow-checker policy](polonius.md) records the nightly compiler
  contract, borrow-centric design rules, and audit tags used by this project.

## Rust reference material

- [OrthoConfig user's guide](ortho-config-users-guide.md) documents layered
  configuration with OrthoConfig v0.10.0.
- [`rstest-bdd` user's guide](rstest-bdd-users-guide.md) documents
  behaviour-driven testing with `rstest-bdd` v0.6.0.
- [Reliable testing in Rust via dependency injection](reliable-testing-in-rust-via-dependency-injection.md)
  explains how to keep tests deterministic by injecting environment, clock,
  filesystem, and other external dependencies.
- [Rust doctest Don't Repeat Yourself guide](rust-doctest-dry-guide.md) explains
  how to write maintainable, executable Rust documentation examples.
- [Rust testing with `rstest` fixtures](rust-testing-with-rstest-fixtures.md)
  explains fixture-based, parameterized, and asynchronous testing with `rstest`.

## Engineering practice

- [Repository checks import plan](execplans/import-rust-template-repo-checks.md)
  describes the proposed import of Rust-template validation tooling.
- [Complexity antipatterns and refactoring strategies](complexity-antipatterns-and-refactoring-strategies.md)
  explains cognitive complexity, the bumpy-road antipattern, and refactoring
  approaches for maintainable code.
- [Scripting standards](scripting-standards.md) explains the preferred Python
  scripting stack, command execution patterns, and test expectations for helper
  scripts.
