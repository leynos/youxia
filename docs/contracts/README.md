# Proposed implementation contracts

These artefacts accompany
[RFC 0001](../rfcs/rfc-0001-native-rust-cli-and-daemon.md). They define
reviewable inputs for the native CLI and daemon implementation. The generated
Youxia application does not load them yet.

| File                                                       | Purpose                                                                                 | Boundary                                                                        |
| ---------------------------------------------------------- | --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| [ishiban-session.schema.json](ishiban-session.schema.json) | Versioned session projection for Ishiban                                                | A proposed local read model, separate from upstream Lody's observation protocol |
| [storage.sql](storage.sql)                                 | SQLite tables, constraints, immutable input/payload guards, and transaction obligations | A logical persistence contract, not an upstream database migration              |
| [config.example.toml](config.example.toml)                 | Initial budgets and observation/hosting authority                                       | Proposed settings requiring implementation, validation, and measurement         |

_Table 1: Proposed contracts and the boundaries they define._

The files originate in the 14 November 2026 Lody Rust design. The import keeps
the observation schema's existing identifier, because it still describes
Lody-compatible session evidence. Example local state paths and the credential
namespace now use Youxia.

## Storage baseline and obligations

SQLite remains the initial engine. Ordinary rowid tables replace the draft's
broad use of `WITHOUT ROWID`, and every non-integer primary-key column declares
`NOT NULL`. This establishes a baseline for measurement and retains the intended
key semantics. RFC 0001 §13.1 records the rationale and the optional Turso
qualification gate.

The storage owner must acknowledge durable acceptance only after the explicit
transaction commits with `synchronous=FULL`. It must configure and verify
connection-local settings, reserve completion and recovery capacity, control
checkpoint work, and bound read transactions. Successful schema creation does
not establish those properties.

The SQL comments specify transaction boundaries that table constraints cannot
enforce: incoming bytes with their cursor, projection with observation events,
snapshot with pending updates, and producer allocation with immutable outbox
bytes. Concrete retry-policy records, admission accounting, and adapter
migrations belong to their implementation tasks in the [roadmap](../roadmap.md).
The initial schema deliberately leaves those adapter-specific records open.

## Validation boundary

Schema parsing, SQL execution, and TOML parsing establish structural validity.
They do not establish native Flock/Loro interoperability, process supervision,
crash recovery, filesystem durability, or the proposed latency targets. The
roadmap assigns those guarantees to explicit implementation and end-to-end
acceptance gates.
