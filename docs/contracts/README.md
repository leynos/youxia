# Proposed implementation contracts

These artefacts accompany
[RFC 0001](../rfcs/rfc-0001-native-rust-cli-and-daemon.md). They define
reviewable inputs for the native CLI and daemon implementation. The generated
Youxia application does not load them yet.

The [Linux architecture](../youxia-design.md) adds the private runner transport
and an illustrative host resource profile. The runner contract defines
semantics; selecting its exact wire encoding remains an implementation gate.

| File                                                       | Purpose                                                                                 | Boundary                                                                        |
| ---------------------------------------------------------- | --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| [ishiban-session.schema.json](ishiban-session.schema.json) | Versioned session projection for Ishiban                                                | A proposed local read model, separate from upstream Lody's observation protocol |
| [storage.sql](storage.sql)                                 | SQLite tables, constraints, immutable input/payload guards, and transaction obligations | A logical persistence contract, not an upstream database migration              |
| [config.example.toml](config.example.toml)                 | Initial budgets and observation/hosting authority                                       | Proposed settings requiring implementation, validation, and measurement         |
| [arun-transport.md](arun-transport.md)                     | Runner identity, attachment, raw replay, write receipts, and recovery                   | Private daemon/runner semantics; no ACP interpretation in `arun`                |
| [linux-host.example.toml](linux-host.example.toml)         | Illustrative slices, service policy, admission, and raw transport budgets               | Linux extension to the base configuration; not measured production defaults     |

_Table 1: Proposed contracts and the boundaries they define._

The original three files originate in the 14 November 2026 Lody Rust design.
The import keeps the observation schema's existing identifier, because it still
describes Lody-compatible session evidence. Example local state paths and the
credential namespace now use Youxia.

## Storage baseline and obligations

SQLite remains the initial engine. Ordinary rowid tables replace the draft's
broad use of `WITHOUT ROWID`, and every non-integer primary-key column declares
`NOT NULL`. This establishes a baseline for measurement and retains the
intended key semantics. RFC 0001 §13.1 records the rationale and the optional
Turso qualification gate.

The storage owner must acknowledge durable acceptance only after the explicit
transaction commits with `synchronous=FULL`. It must configure and verify
connection-local settings, reserve completion and recovery capacity, control
checkpoint work, and bound read transactions. Successful schema creation does
not establish those properties.

The SQL comments specify transaction boundaries that table constraints cannot
enforce: incoming bytes with their cursor, projection with observation events,
snapshot with pending updates, and producer allocation with immutable outbox
bytes. Concrete retry-policy records, admission accounting, and adapter
migrations belong to their implementation tasks in the
[roadmap](../roadmap.md). The initial schema deliberately leaves those
adapter-specific records open.

## Validation boundary

Schema parsing, SQL execution, and TOML parsing establish structural validity.
They do not establish native Flock/Loro interoperability, process supervision,
crash recovery, filesystem durability, or the proposed latency targets. The
roadmap assigns those guarantees to explicit implementation and end-to-end
acceptance gates.

The Linux profile must validate both hierarchy and reservation arithmetic. Its
per-run memory and spool allocations fit the configured workspace/host
admission counts. CPU quotas represent ceilings, not reservations; parent
limits can bind first. The profile's eight-run limit is a small qualification
example, distinct from the roadmap's later 60-agent fleet workload. Missing I/O
enforcement remains visible when the optional I/O capability is unavailable.
