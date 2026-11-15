# RFC 0001: Native Rust CLI and daemon

## Preamble

- **RFC number:** 0001
- **Status:** Proposed
- **Created:** 2026-11-15
- **Source design:** 2026-11-14
- **Audience:** implementing agents, reviewers, and daemon operators.
- **Compatibility baseline:** Lody commit
  `d3179e1f7538b61d0a6acc6be0a324281be4e3c0`, CLI 0.104.0.[^1]

## Summary

Youxia proposes a native Rust command-line interface (CLI) and daemon that
preserve accepted work while bulk synchronization, agent output, or slow
storage compete for resources. Its first vertical slice supplies trustworthy
read-only observations to Ishiban. Its second hosts one Agent Client Protocol
(ACP) agent and synchronizes its history through native Loro, a conflict-free
replicated data type (CRDT) engine. Fleet operation follows those two
qualification gates.

Sections 1–12 retain the architecture and correctness analysis from the initial
Lody reimplementation plan. The original combined document also included a
67-task breakdown and inline contracts. The [roadmap](../roadmap.md) replaces
that task list; this RFC keeps the architecture in one place. The proposed
[observation schema](../contracts/ishiban-session.schema.json), [storage contract](../contracts/storage.sql),
and [configuration example](../contracts/config.example.toml) remain separate,
reviewable artefacts.

Section 13 records the later storage assessment and the requirements derived
from [Comenq's implementation lessons][lessons]. Those amendments take
precedence where they refine an earlier statement. The SQLite schema now uses
ordinary rowid tables with explicit primary-key nullability. The product and
provisional binary names use Youxia; existing Lody service, authentication,
protocol, and compatibility identifiers retain their upstream names.

Upstream and library findings describe the revisions inspected on 2026-11-14.
They do not establish the currently deployed CLI/server profile or the latest
available dependency versions. Implementation must requalify that profile. This
RFC proposes contracts and acceptance targets; it reports no implemented Youxia
daemon, completed interoperability gate, or measured benchmark result.

## Contents

- [1. Decision and scope][section-1]
- [2. Verified baseline and compatibility boundaries][section-2]
- [3. Components and runtime isolation][section-3]
- [4. Ishiban observation and replay][section-4]
- [5. Native replication and durability][section-5]
- [6. Heartbeats, liveness, and readiness][section-6]
- [7. ACP hosting with durable Loro sync][section-7]
- [8. CLI, authentication, and configuration][section-8]
- [9. Resource budgets, operations, and observability][section-9]
- [10. Verification strategy][section-10]
- [11. Rollout and practical CLI parity][section-11]
- [12. Decisions, gates, and implementation hand-off][section-12]
- [13. Amendments for Youxia implementation][section-13]

## 1. Decision and scope

Build a native Rust CLI and daemon in two initial vertical slices:

1. A durable, read-only workspace observer that supplies Ishiban with session
   metadata, trustworthy execution evidence, freshness, and resumable changes.
2. A host for one external ACP agent, with durable input admission, incremental
   output persistence, and bidirectional native Loro synchronization.

Extend that proven path to the working fleet and practical CLI parity. Use
Tokio for asynchronous I/O, the official Rust ACP software development kit
(SDK) for agent connections, OrthoConfig for configuration, native Rust Loro
for Loro documents, oauth2 for the supported device authorization flow, and
restson for bounded JSON request/response APIs.

The main architectural requirement is **bounded work at every scheduling
boundary**. An async function may still consume seconds of CPU, allocate an
entire history, wait behind a saturated writer, or synchronously invoke a
callback. Hot paths may perform bounded framing, validation, routing, and
accounting. Their cost must not grow with total conversation history.

The target remains compatible with the existing Lody service and supported
clients. A new self-hosted cloud backend, desktop replacement, UI rewrite,
general-purpose orchestration platform, and active-active daemon ownership are
outside the initial scope. Linux on Rohga is the first daemon target. Keep the
CLI and core portable; qualify Windows process and named-pipe behaviour
separately.

Use provisional installation names `youxia` and `youxiad` until the
compatibility and cutover gates pass. A temporary bridge to the TypeScript
daemon can accelerate projection development, but it does not satisfy the
independent native-daemon milestone.

### 1.1. Definition of the first two deliverables

| Deliverable       | Observable outcome                                                                                                                                                                | Completion boundary                                                                                                                                                            |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Ishiban spike     | One authorized workspace appears through a native observer, with catalogue discovery, selective history evidence, explicit stale/unknown states, and durable replay after restart | No workspace/session/presence mutations; essential metadata and supported Loro histories work without a TypeScript daemon in the production path                               |
| ACP hosting spike | One configured real ACP agent accepts a prompt, streams output, handles a permission interaction and cancellation, and synchronizes its conversation with an existing Lody client | Accepted input and durable output survive restart/reconnect; uncertain submission remains explicit; native replica operations never run in ACP dispatch or heartbeat callbacks |

_Table 1: Observable completion boundaries for the first two slices._

Read-only observation may authenticate, subscribe, and persist its own local
cache. It must not create missing streams, mark messages read, publish
presence, update model summaries, archive sessions, or answer permissions.

### 1.2. Native dependency qualification

“Native” means native machine code operating on replicated state. It does not
mean an Effect-native TypeScript API, a WebAssembly (WASM) module inside
another process, or a WKWebView-based decoder. Native compilation removes
Loro's particular WASM address-space limit; it does not remove document
residency or CPU costs.

The requested dependency list needs two additional compatibility boundaries:
**Flock** for workspace metadata and **Streams** for transport. Native Loro
does not provide either boundary by itself. Section 2 makes this an explicit
early gate.

## 2. Verified baseline and compatibility boundaries

### 2.1. Findings that determine the architecture

The inspected upstream revision separates fleet ownership, workspace runtimes,
and supervisor/execution-worker lifetimes. Retain the relevant ownership rules
while moving expensive work into separately scheduled domains.[^2][^3]

| Evidence in inspected source                                                                                                                                                                       | Consequence for the rewrite                                                                                                                           |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| The workspace presence channel serializes machine heartbeats with other presence publications. An entry can wait beyond the 90-second time to live (TTL) while the room still reports joined. [^4] | Isolate scheduling and reserve publication capacity; observe queue age and delivery separately from connection status                                 |
| The November heap incident records 40–50 long sessions exhausting a 4 GiB WASM heap. The fixes broaden collection and enter ordinary shutdown on a trap. [^5]                                      | Use native Loro; retain explicit document leases, residency budgets, process containment, and orderly shutdown                                        |
| An October incident traced sync stalls to whole-history and whole-turn serialization on the main thread. Windowed writes reduced the measured fixture cost substantially. [^6]                     | Port incremental write semantics; moving the same full-history work into Rust would preserve the scaling problem                                      |
| Received Loro operations awaiting predecessors can disappear if persistence retains only ordinary snapshots. That revision preserves pending operations. [^7]                                      | Journal received bytes and preserve pending state through every checkpoint/compaction boundary                                                        |
| Different in-memory replicas sharing a database must not share a cursor ahead of their own recoverable state. [^8]                                                                                 | Give the daemon ownership of replicas and cursor checkpoints; the CLI uses interprocess communication (IPC); independent observers use isolated state |
| Existing observation uses durable evidence and selective history opening, but its sequence orders one command process only. [^9]                                                                   | Preserve the semantics and add a separate durable observation journal for Ishiban                                                                     |
| Legacy product Task documents remain only for cleanup; SessionMeta has no replacement task ID or workflow stage. [^10][^11]                                                                        | Preserve session identity and establish explicit Ishiban work-item correlations                                                                       |

_Table 2: Inspected upstream mechanisms and their architectural consequences._

These are source-backed mechanisms and implemented upstream changes. They do
not identify the cause of every failure on the user's installed daemon. The
rewrite must preserve the upstream corrections, then demonstrate the additional
scheduling and durability guarantees under the target workload.

### 2.2. Keep the protocols distinct

| Boundary                                 | Existing responsibility                                                                                             | Rust implementation decision                                                                        |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| Cloud authorization and catalogue access | Better Auth device authorization, CLI API keys, Convex queries/subscriptions, workspace access                      | Auth owner plus typed HTTP adapter and a separately qualified subscription adapter                  |
| Durable Streams                          | HTTP bootstrap/catch-up, server-sent events (SSE) or long-poll, opaque offsets, snapshots, append/producer identity | Audit the published Rust Streams client before implementing replacement transport                   |
| Loro documents                           | Default session histories and their schema                                                                          | Native loro crate, owned by replica workers                                                         |
| Flock rooms                              | Workspace meta/session catalogue and other named workspace catalogues                                               | Native Flock implementation or complete, tested native codec; mandatory for independent observation |
| Presence                                 | Ephemeral liveness/activity with its own ownership and transport                                                    | Dedicated scheduler and publisher with bounded latest-state admission                               |
| Machine remote procedure calls (RPC)     | Request/response commands and responses over the existing RPC transport                                             | Explicit request identities, deadlines, deduplication, and reply recovery                           |
| Local data plane                         | Authenticated local socket/pipe protocol 7, Loro/Flock vectors and framed updates                                   | Separate compatibility adapter; not the cloud Streams protocol or Ishiban API                       |
| ACP                                      | Bidirectional JSON-RPC with agent subprocesses                                                                      | Rust SDK client role with bounded transport and supervised process ownership                        |

_Table 3: Independent protocols and compatibility responsibilities._

The durable Streams composition maps workspace meta to `<workspaceId>:meta`,
ordinary sessions to `<workspaceId>:s:<sessionId>`, and named Flock rooms to
their existing IDs. Preserve encoding, workspace scope, gateway/shard
configuration, token scope, and snapshot codec behaviour. The inspected code
accepts raw historical snapshots and zstd-compressed snapshots. Do not guess
production endpoints from placeholder defaults.[^12][^13]

The local protocol has its own authentication, room joins, version vectors, 32
MiB frame ceiling, chunk reassembly, and ping watchdog. Its existing writer
already delays export until the socket can make progress. A local join is a
reconciliation point even if an in-memory dirty flag is clear. Preserve those
properties if implementing that adapter.[^14]

### 2.3. Native Flock is a blocking compatibility gate

The visible workspace code uses Flock. Public npm documentation identifies a
Rust core, but this research did not establish access to a native source/crate
release matching Lody's pinned Flock dependency. A public description of JSON
interchange does not specify the complete binary snapshot format.[^15]

Resolve the gate in this order:

1. Obtain and audit the matching native Flock source/API, licensing, version
   semantics, tombstones, snapshot formats, and read/recovery fixtures.
2. If no usable implementation exists, determine whether a complete published
   format permits a bounded native reader and later a writer. Budget this as
   actual compatibility work.
3. Use protocol 7's Flock JSON interchange only as an explicitly labelled
   development bridge or transitional observer. Verify clocks, deletions,
   version summaries, and reconnect semantics against the upstream oracle.
4. Do not pass the independent observer gate until the TypeScript dependency has
   left its essential metadata path.

The mobile implementation is not an established native escape route: its Swift
Flock decoder invokes a JavaScript decoder in WKWebView.[^16] Never substitute
a Loro map merely because the application exposes both data types through
similarly shaped metadata methods.

Split the qualification: the observer needs native decoding, merge/deletion
semantics, and recoverable replay. It can retain raw upstream records instead
of producing a new Flock snapshot. Native authoring and upstream-readable
machine/session metadata are a separate gate before hosting. ACP SDK hardening
and native Flock authoring may progress in parallel; they must not delay the
first read-only slice once its own dependencies pass.

### 2.4. Loro, Roost, and protected workspaces

Lody still defaults ordinary new sessions to Loro, including metadata without a
backend discriminator. Roost is opt-in and persists an immutable
`historyBackend`. A remote-owned Roost history may require owner RPC.[^17]

The first supported profile is an authorized, unencrypted workspace with Loro
history. Catalogue rows for other backends remain visible with an explicit
unsupported/unavailable verdict. They must not become empty histories or
completed sessions.

Before applying that profile to the real workspace, inspect its protection and
backend distribution. If it uses encryption or requires Roost to satisfy
Ishiban's essential coverage, promote that capability to a prerequisite. Do not
disable encryption or reinterpret persisted history to make a spike pass.
Protected payloads, key epochs, room binding, encrypted-only reads, and
iroh/machine-sharing behaviour require a separate compatibility slice.

### 2.5. Candidate dependency baseline

| Dependency            | Inspected candidate                                     | Qualification                                                                    |
| --------------------- | ------------------------------------------------------- | -------------------------------------------------------------------------------- |
| agent-client-protocol | 5.2.0; source 91d368ad8b6761f314da9095c4a030d365c079a9  | Stable ACP v1; queue/framing audit and real-agent tests [^18][^19]               |
| ortho_config          | 0.10.0; source 38812c563e3953a490e3efc202609f37e21a0517 | Released composition APIs; Rust 1.89 minimum from this dependency [^20]          |
| loro                  | 1.17.1 native candidate                                 | Cross-read/write fixtures against Lody's JS 1.17.0 [^21][^22]                    |
| loro-streams-client   | 0.1.0 candidate                                         | Audit against pinned TS streams-client 0.12.2 and streams-crdt 0.20.0 [^23][^24] |
| oauth2                | 5.0.0                                                   | Actual Better Auth endpoint/response compatibility [^25]                         |
| restson               | 1.5.0                                                   | Bounded-body, timeout, retry-header, and logging hardening [^26]                 |
| Native Flock          | Unresolved                                              | Do not invent a crate/version or claim availability                              |
| SQLite adapter        | Select during foundation                                | Dedicated writer, WAL/FULL durability, bounded readers                           |

_Table 4: Inspected dependency candidates and required qualification._

The inspected ACP SDK exposes `Client.v1()`; do not copy obsolete Rust
`ClientSideConnection` and mandatory `LocalSet` assumptions into the plan. Its
handler futures are `Send`. The SDK crate version and ACP wire version are
different numbers.[^18][^27]

Pin the tested graph and exact patches in a lockfile. Rust 1.89 is a known
lower bound, not a promise that every eventual transitive dependency supports
it. Audit target-active features; a cross-platform lockfile mentioning WASM
does not prove the native executable uses it. The production state path must
contain neither a WASM engine nor bundled Loro/Flock WASM execution.

## 3. Components and runtime isolation

### 3.1. Ownership topology

Use a small number of permanent execution domains. Start with two replica
worker processes and tune only after measurement; avoid a thread or runtime per
document.

| Domain                              | Owns                                                                                           | Must not execute inline                                                                        |
| ----------------------------------- | ---------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| CLI                                 | Argument parsing, config selection, human/JSON formatting, IPC request lifetime                | Independent live replicas or concurrent writes to daemon SQLite                                |
| Daemon control thread               | Liveness scheduling, cheap health snapshots, shutdown coordination, publication deadlines      | History traversal, Loro calls, disk calls, config discovery, REST parsing                      |
| Daemon I/O runtime                  | Bounded frame readers/writers, Streams reads, local IPC, finite RPC routing                    | Decompression, whole-document JSON, git, large serialization                                   |
| Replica worker processes            | Native Loro/Flock documents, ordered mutation/import, scalar projection, bounded snapshot jobs | Network-facing callback chains or unbounded work queues                                        |
| Storage owner                       | SQLite transactions, durable inbox/outbox, checkpoints, projection and event commit            | Agent execution, indefinite reads, foreground VACUUM                                           |
| ACP adapters and session supervisor | Connection lifetime, admitted requests, permissions, process groups and execution generations  | Replica operations, synchronous filesystem work, remote approval waits inside ordered dispatch |
| Maintenance/REST workers            | Bounded restson calls, config reload, git/diff/index work, compression where not replica-owned | Heartbeat scheduling or per-token hooks                                                        |

_Table 5: Execution domains and inline-work exclusions._

The dedicated control runtime lives on its own OS thread and constructs its own
network resources. A cloned HTTP client whose connection driver runs on an
overloaded runtime would undermine the separation. Token refresh runs in a
separate owner and publishes immutable token snapshots; liveness never waits
while holding a refresh lock.

Fixed replica **processes** provide a killable boundary for pathological
imports, native panics, or memory growth. Each document has one logical owner
and one ordered mailbox. On worker death, increment the generation, reload from
the durable checkpoint/journal, and reject late replies. Worker placement and
rebalancing occur only at checkpointed boundaries.

A fixed pool still needs limits on individual operations. An arbitrary binary
snapshot cannot become incremental simply by slicing its bytes. Measure native
import/export cost and admit only supported bounded inputs. Quarantine an
offending room, preserve its journal, and keep unrelated local reads and
control work available.

### 3.2. Boundary contracts

Every message crossing a domain carries its scope and generation:
deployment/profile, workspace, room/session, owner generation, operation ID,
and byte cost. Credits cover queued payloads, in-flight payloads, IPC buffers,
and downstream ownership. Release a credit when the bounded domain actually
releases the resource, not when a forwarding task puts it into another queue.

Use immutable byte buffers and compact projections. Do not pass a globally
shared `Arc<Mutex<LoroDoc>>` into async code. Loro's Send/Sync traits permit
threading; its import, export, snapshots, and callbacks remain synchronous.
Document ownership is a scheduling decision, not a workaround for a missing
trait.[^21]

Callbacks may mark a bounded set of dirty fields/IDs and enqueue a reference.
They may not serialize histories, export snapshots, perform SQLite writes, or
re-enter a replica through an observer callback. A saturated callback path must
have a defined overload result; it cannot silently allocate another queue.

### 3.3. Queue policy

| Work class                | Capacity rule                                                            | Saturation response                                                                      |
| ------------------------- | ------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------- |
| Durable remote input      | Bytes, records, and disk-spool budget                                    | Pause or close the affected feed; resume from its committed cursor                       |
| Accepted local operations | Durable journal/outbox before acceptance                                 | Reject new admission if reservation fails; preserve existing work                        |
| Presence                  | Fixed key/value limits, bounded distinct keys, latest unsent value       | Coalesce ephemeral updates; reserve machine liveness service                             |
| ACP protocol traffic      | Frame bytes, in-flight requests, handler/task counts, downstream credits | Backpressure where safe; explicit connection overload/controlled failure where it is not |
| Observation consumers     | Per-consumer byte/lag limit                                              | Disconnect with resnapshot/replay requirement                                            |
| Diagnostics               | Bounded non-blocking sink                                                | Drop/sample diagnostics with a counter; never block core progress                        |
| Maintenance               | Fixed concurrency and bytes                                              | Delay or reject optional work                                                            |

_Table 6: Queue budgets and overload responses._

Neither a bounded queue nor `spawn_blocking` alone establishes a bound on CPU,
memory, or completion time. Tokio queues blocking work beyond its thread limit,
and started blocking tasks cannot be aborted. Use admission before scheduling;
use a process boundary when termination must work.[^28]

### 3.4. Workspace shape

Start with cohesive modules/crates rather than one crate per abstraction:

- **youxia-core:** IDs, command state machines, observations, health, and pure
  projection rules.
- **youxia-protocol:** pinned Lody DTOs, compatibility decoding, explicit
  unknown fields, and transport-independent domain conversions.
- **youxia-store:** the durable storage API and SQLite adapter.
- **youxia-sync:** native replica ownership, Loro/Flock adapters, Streams,
  presence, and recovery.
- **youxia-acp:** SDK integration, admission, callbacks, and process
  supervision.
- **youxia-cli / youxiad:** composition, configuration, authentication, local
  API, service lifecycle, and internal replica-worker entry point.

Ports should describe operations such as reading a catalogue, durably accepting
a command, importing a replica batch, or publishing liveness. Callers should
not depend on raw Loro containers or a particular HTTP client.

Section 13.2 adds the shared-resource contention and progress-capacity rules.
Section 13.6 requires domain dependency checks and atomic storage transitions.

## 4. Ishiban observation and replay

### 4.1. Preserve the existing observation semantics

Install the catalogue watch before enumeration, reconcile identities changed
during enumeration, and publish catalogue readiness only after that boundary.
This prevents the list/subscribe race. Catalogue readiness does not imply that
every history is ready.[^9]

Discover all sessions from metadata. Open supported history directories for
active, pending, newly created, changed-turn, and explicitly inspected
sessions. Read turn identity/scalars without materializing transcripts. Retire
an observation lease only after fresh durable terminal evidence and activation
pointers agree.

The upstream concurrency of four bounds acquisition, not total active
documents. Add explicit residency and byte budgets. When a budget prevents live
enrichment, expose that fact and retain the previous observation with its
timestamp. Do not claim all 60 active sessions are current while silently
evicting their live evidence.

Preserve these distinctions:

| Dimension    | Examples                                                   | Evidence rule                                                                                                      |
| ------------ | ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Execution    | idle, pending, running, waiting, unknown                   | Derive from persisted turn/control facts; metadata-only catalogue means unknown                                    |
| Turn outcome | completed, failed, `canceled`, unknown                     | Completion requires handled user plus linked finished/ended assistant; failure/cancel have their own durable facts |
| Freshness    | current, catching up, stale, unsupported, corrupt, unknown | Describe the evidence channel and last confirmed point                                                             |
| Connectivity | online, offline, unknown                                   | Use fresh presence and confirmed presence synchronization                                                          |
| Workflow     | planning, planned, pending review, refining, merged        | Require explicit work-item and workflow evidence                                                                   |

_Table 7: Independent session dimensions and their evidence requirements._

A cancel receipt, idle metadata, vanished heartbeat, or closed socket never
proves a completed turn. An archive changes visibility; it is not deletion.
Partial catalogue absence is not proof of removal. A fast completed turn may be
observed without a start event. Reopened turns may produce another transition
with the same turn IDs.[^9]

### 4.2. Work-item identity and board stages

Use `(profile_id, workspace_id, session_id)` as the observation identity. This
matches the projection schema, whose primary key includes `profile_id`, so two
deployment profiles that share workspace and session identifiers cannot
collapse into one observed row. Keep parent, root/origin, repository, branch,
agent-role, schedule, and PR associations with their provenance. Preserve the
distinction between Lody's retired product Task and an ACP subagent task
embedded in history.[^10][^11]

Ishiban owns an explicit mapping from work items to one or more sessions.
Recover existing mappings only from trusted surviving evidence or deliberate
configuration. Do not manufacture one work item for every session.

Keep the established board stages: planning, planned, pending review, refining,
and merged. Publish no stage when evidence is insufficient. Store the mapping
revision and evidence URI so later corrections can update the projection. PR
merge evidence may advance a known work item; it cannot silently establish that
every linked session represents that work item.

Session catalogue metadata can supply repository and PR hints. GitHub, Linear,
execplan, CI, and issue reconciliation remain separate consumers or existing
Ishiban services. Their work must not enter the daemon's hot path.

### 4.3. New durable observation contract

Preserve upstream `session observe` v1 as a compatibility view. Introduce a
separate namespaced Ishiban API; do not relabel a new enriched schema as the
unchanged upstream v1 format.

The new event envelope carries:

| Field                              | Meaning                                                                    |
| ---------------------------------- | -------------------------------------------------------------------------- |
| api/version                        | A new observation API namespace and schema version                         |
| cursor                             | Opaque encoding of journal identity and local monotonic sequence           |
| type                               | Session upsert/removal, turn observation, source health, or explicit reset |
| profile/workspace/session identity | Deployment/account scope, with session optional for source-wide health     |
| observed_at                        | Local observation time, distinct from execution/source time                |
| source evidence                    | Backend, room/frontier or applied receipt, and evidence class              |
| payload                            | A bounded projection or change record                                      |

_Table 8: Fields in the durable observation envelope._

The journal identity changes on database restoration or reconstruction that
could reuse sequence numbers. Consumers must not parse the cursor or compare
upstream offsets. A new journal cannot pretend to continue an older one.

Commit replica application progress, projection changes, and observation events
consistently. The [storage contract](../contracts/storage.sql) defines the
required transaction boundaries; SQL column definitions alone do not enforce
them. A restart replays unapplied durable input and avoids duplicating already
committed projection events.

Read the initial snapshot and its replay watermark from the same database
snapshot. For large paginated results, materialize a bounded immutable snapshot
generation with a short-lived token; do not hold a SQLite read transaction open
for an arbitrarily slow browser. Subsequent replay begins strictly after the
returned watermark.

An expired cursor or missing retention interval returns an explicit reset/
resnapshot response. It never jumps to “now” without telling the consumer. When
a consumer falls behind, disconnect it while retaining the source journal. A
slow browser must not delay source ingestion or agent execution.

The [projection schema](../contracts/ishiban-session.schema.json) separates
history availability from the freshness of selected evidence: a current
catalogue can truthfully describe an unsupported history. The new feed bounds a
serialized event to 256 KiB within a 1 MiB consumer buffer. Page optional
associations/detail separately; never put a full transcript into an event. If a
required scalar cannot fit, emit a bounded explicit row-error record and
preserve its prior observation. Repeated resnapshot is not a remedy for an
individually oversized row.

### 4.4. Initial integration surface

Provide authenticated local IPC plus JSONL for scripts. The existing Falcon/SSE
component can expose the Rust journal to Ishiban and forward Last-Event-ID
semantics. The Rust daemon owns the durable cursor; Falcon does not invent a
second competing sequence.

Candidate commands are:

- `youxia auth login/status/logout`
- `youxia workspace list --json`
- `youxia session list --workspace ... --json`
- `youxia session status/history ... --json`
- `youxia session observe --workspace ... --all --jsonl --follow`
- `youxia observation snapshot/follow` for the new durable contract
- `youxia daemon status/diagnose`

Keep stdout machine-readable and diagnostics on stderr. Define stable error
codes, unsupported-feature errors, cursor reset behaviour, and signal cleanup.
Closing an observer does not cancel an agent.

The local IPC handshake and running-peer diagnostics in §13.5 gate this first
observation surface. Section 13.4 defines cancellation-safe framing ownership.

## 5. Native replication and durability

### 5.1. Reuse the native Streams client conditionally

The published Rust Streams client already supports bootstrap, append, read/live
SSE and long-poll, snapshots, token callbacks, and retry behaviour. Its SSE
contract associates buffered data with the following control offset and
discards incomplete batches on disconnect for replay.[^23]

Audit its actual source and tests against the pinned Lody protocol profile.
Qualify byte limits, multipart truncation, protected-payload extensions,
producer deduplication, cancellation, retry headers, idle watchdogs, and the
point where internal reconnect cursors advance. A delivered event is not
automatically durably stored.

Use restson only for bounded JSON request/response operations. Do not force
SSE, raw Loro bytes, multipart snapshots, or presence through that interface.
Use the native Streams client's transport where it meets the contract and a
narrow adapter or patch where it does not.

### 5.2. Three progress positions, plus peer evidence

Track separately:

1. **Received:** bytes reached the process; no durability promise.
2. **Durably ingested:** a complete contiguous feed prefix and its opaque cursor
   are recoverable from storage.
3. **Applied/projected:** the replica consumed the relevant durable records and
   the projection/event transaction committed.
4. **Remote/peer evidence:** transport acceptance, server reconciliation, or a
   specific peer observation, each explicitly named.

A cursor belongs to a deployment/profile, workspace, room, stream incarnation,
and durable replica. Network connection generation is not stream incarnation.
If the service exposes no incarnation identifier, record that limitation and
rebootstrap whenever continuity cannot be proved. Never synthesize server
evidence from a reconnect counter.

The transport reader validates framing and reserves byte capacity. The storage
owner commits an entire cursor-bearing batch and the new durable cursor in one
transaction. Only then may the ingestion owner acknowledge that durable
boundary internally. Preserve out-of-order causal operations inside that batch
even if Loro cannot apply them yet.

The replica worker imports durable data and produces an incrementally computed
projection. The storage transaction commits the applied watermark, projection
changes, and observation events together. Failed imports do not advance the
applied position. A poison record blocks/quarantines its room and produces an
operator-visible error; it does not authorize a silent skip.

After a worker restart, reconstruct its document from the checkpoint and every
later relevant inbox record, even if the persisted projection watermark is
ahead. The watermark suppresses duplicate event publication; it must not
suppress imports needed to rebuild the in-memory document. Deduplicate
transport records across reconnect generations using the selected protocol's
stable identity, and suppress unchanged semantic projection updates.

### 5.3. Checkpoints and missing dependencies

A recoverable Loro checkpoint contains the ordinary snapshot, pending updates
or retained raw journal, represented input watermark, native format version,
and integrity metadata. Construct a consistent generation and install it
atomically. Do not delete old recoverable state until the new generation
commits.

Prevent mutations/imports between snapshot export and pending-sidecar export.
An empty pending result clears the old sidecar in the new generation; an export
error leaves the previous checkpoint intact. Restore the snapshot before
importing its sidecar. Neither export call is an atomic pair by itself.

Loro exposes `export_pending_updates` because ordinary snapshots do not include
all operations awaiting causal predecessors. Retaining the complete received
journal is an alternative, provided compaction proves coverage. Neither applied
version vectors nor a successful local flush prove that no dependencies remain
missing.[^7][^21]

Carry forward the upstream regression:

1. Persist a base document.
2. Receive operation B before its predecessor A.
3. Flush, stop, and reopen.
4. Receive A.
5. Require the same document as uninterrupted delivery, including after another
   reopen.

Add partial checkpoint writes, disk-full, crash-before-cursor-commit, and
corrupted-generation recovery. Bootstrap cannot overwrite locally accepted,
unsent operations; retain and reconcile the outbox and original identities.

### 5.4. Local authoring and the outbox

A local command admission reserves storage and writes its frozen input,
semantic operation identity, session/turn IDs, and required outgoing records
before returning an accepted receipt. The per-session owner serializes
authoring so native CRDT counters and producer sequences remain consistent.

Persist the exact outgoing bytes and producer tuple before publication. Retry
that immutable tuple; do not regenerate “equivalent” operations after an
uncertain send. A repeated idempotency key with different frozen input is an
error. Transport deduplication and semantic command deduplication solve
different problems.

Keep producer state, next sequence, owner generation, and peer identity
recoverable. Database restore can resurrect an old CRDT counter. Before
authoring, either recover the complete previously published horizon or rotate
to a fresh supported replica/peer identity. Changing the observation journal ID
alone does not solve CRDT identity reuse.

An HTTP append success is **transport acceptance** unless the exact service
contract establishes more. Do not promise peer receipt, disk flush, quorum
durability, or exactly-once execution from it. Retention/compaction policy must
rely on verified recovery guarantees and the retained local checkpoint, not an
invented server acknowledgement.

### 5.5. Recovery state machine

| State       | Entry condition                                                | Exit requirement                                                     |
| ----------- | -------------------------------------------------------------- | -------------------------------------------------------------------- |
| Recovering  | Startup, worker loss, damaged cache, or continuity reset       | Valid local checkpoint/journal or an explicit clean bootstrap        |
| Catching up | Authorized stream open from recoverable position               | Applied durable input plus the selected protocol's catch-up evidence |
| Current     | Confirmed catch-up for the observed capability                 | Continued progress checks; absence of activity alone is not failure  |
| Stale       | Lost connection/progress or admission backlog beyond budget    | Reconnect/reconcile from committed position                          |
| Blocked     | Invalid auth, unsupported backend/protection, or poison record | Explicit dependency restoration or supported recovery decision       |
| Draining    | Shutdown/cutover                                               | Stop admission, retain durable work, release ownership               |

_Table 9: Replica recovery states and exit requirements._

Every reconnect establishes a new generation and reconciles from durable state.
Late tasks from the old generation cannot write, advance a cursor, publish
stale presence, or dispose the new owner's document.

Use protocol-supported head/version/producer operations for anti-entropy.
Schedule bounded jittered checks and trigger them after a suspicious lack of
progress. Do not invent a version-vector handshake unsupported by the existing
server. A trimmed cursor/410 requires snapshot/bootstrap recovery; a 401
requires auth handling; a 429 follows retry guidance. Retry each room with
backoff and a workspace concurrency budget so reconnecting 60 sessions does not
create a recovery storm.

Sections 13.1 and 13.3 refine storage qualification, owner-incarnation
recovery, and retry-floor persistence. Recovery never authorizes replay of an
uncertain external effect solely because its old claim has been reclaimed.

## 6. Heartbeats, liveness, and readiness

### 6.1. Separate the failure dimensions

A daemon can have a functioning timer while its outbound presence is stuck. It
can synchronize histories while its presence channel fails. It can keep
publishing presence while a replica worker is deadlocked. Expose those
conditions separately.[^4]

Use monotonic time for schedules/deadlines and wall time only where the
existing wire protocol requires timestamps. Detect clock discontinuities; never
infer elapsed time from a wall-clock subtraction alone.

Retain the existing 30-second heartbeat and 90-second freshness defaults for
the compatibility profile. Use a missed-tick policy that emits one fresh
renewal after delay rather than a burst of obsolete heartbeats. The policy does
not recover a missed lease; it makes recovery explicit.[^29]

### 6.2. Publication design

The control domain owns one bounded latest-state slot for machine liveness,
bounded per-session presence, lifecycle removals, and a publication schedule.
High-frequency text, tool progress, and token callbacks may update cheap local
state; they cannot enqueue one presence publication per update.

Reserve scheduling, connection-pool, and append budget for liveness on the
**existing ephemeral protocol**. Presence is not a made-up second server
stream. Coalesce unsent replaceable updates before encoding; preserve in-flight
ordering and any clock/producer rules of the selected adapter.

Materialize the heartbeat timestamp when starting actual publication, not when
creating work that may queue indefinitely. Do not mutate serialized in-flight
operations to freshen them. After an ambiguous failure, reconcile or retry
under the protocol's identity rules, then issue a new renewal.

Bound append size and duration. A priority queue cannot interrupt a blocked
append already in progress. The acceptance test must establish the maximum
publication delay under the measured workload and supported server behaviour.
Network outages and host starvation remain visible failures.

Measure these timestamps independently: intended schedule, local dispatch,
publication start, transport completion, and observed remote freshness. A local
barrier or drained queue does not prove a particular peer received that
heartbeat.

### 6.3. Capability readiness and supervision

Publish/readiness-report separate capabilities:

- Local cached reads.
- Cloud ingestion.
- Replica convergence.
- Agent admission.
- Individual active-agent health.
- Presence publication.

When durable storage is full or execution ownership is uncertain, agent
admission becomes unavailable even if the process heartbeat still works. A
single blocked history should not disable unrelated cached reads.

The service watchdog checks bounded progress indicators from storage, replicas,
and supervision. It must not declare the entire daemon healthy because a
dedicated ticker can still run. Respect the existing presence schema; richer
diagnostics belong in the local API when older clients cannot interpret them.

Reserve service CPU opportunity separately from compile/agent workloads using
ordinary Linux service/resource controls. A dedicated thread cannot promise
latency if rustc and all child processes exhaust the host's CPU or memory. Keep
that operational condition in the benchmark profile.

## 7. ACP hosting with durable Loro sync

### 7.1. Implement the client role

The daemon is the ACP **client** when it launches an external agent. It
advertises only implemented filesystem/terminal capabilities, routes permission
requests, and consumes agent session updates. Stable protocol v1 is the first
target. Provider-specific Lody extensions remain explicit adapters with
captured compatibility fixtures.[^18][^30]

The first end-to-end path is:

1. Resolve agent configuration and a controlled working directory.
2. Admit and persist a command with stable session/turn identity.
3. Start or select one owned ACP process and initialize capabilities.
4. Create/load the ACP session according to negotiated support.
5. Record dispatch intent before writing the prompt.
6. Persist admitted output incrementally and publish corresponding Loro
   operations through the outbox.
7. Prove completion/failure/cancellation from the appropriate lifecycle
   evidence, then publish a final projection.
8. Observe the conversation from an existing Lody client.

### 7.2. Protect the SDK boundary

The inspected SDK processes ordered callbacks within a connection dispatcher.
Awaiting a response that requires the same dispatcher from inside a handler can
deadlock. `cx.spawn` moves work outside that ordered callback but does not
itself provide CPU isolation from the connection driver.[^27]

The inspected SDK also deliberately uses unbounded channels, and its ordinary
line transport does not impose the daemon's required frame ceiling. A bounded
application queue in front of those channels is insufficient if a forwarding
task immediately empties it into the SDK.[^31]

The hosting spike requires:

- A length-limited stdout framing adapter that rejects overlarge or unterminated
  frames before accumulating arbitrary memory.
- Real downstream byte/message credits at every SDK admission boundary.
- Caps on pending requests, permission handles, callback registrations, SDK
  tasks, and response buffers.
- A narrow maintained SDK patch where public hooks cannot establish those
  bounds; preserve regression tests so it can move upstream later.
- Reserved control admission without reordering protocol events that require
  ordered interpretation.
- Prompt handler return after bounded validation/routing; async response bridges
  own their permits and catch expected application errors.

Do not advertise hard daemon memory bounds until the actual SDK queues and
transport buffers participate in the accounting. On overload, fail the affected
connection/session explicitly and preserve a reconstructible journal.
Indefinite output production, finite storage, and loss-free unbounded retention
cannot all hold simultaneously.

### 7.3. Incremental output and the durability boundary

Retain separate operations for text append, tool-call insertion/update,
permission state, plan/config changes, and terminal state. Apply only the
touched fields/items and maintain version-checked indexes. Do not repeatedly
convert a whole conversation or a growing turn to JSON.[^6]

Coalesce adjacent text only when concatenation preserves the original order and
meaning. Flush at bounded byte/time limits and at structural boundaries. Keep
stable operation IDs across retries. A terminal status cannot overtake earlier
durable output.

ACP notifications generally do not carry a durable acknowledgement contract.
Therefore distinguish received output, journaled output, and remotely accepted
output. A process crash may lose a notification that reached only RAM. Minimize
that window through a bounded append journal, report it truthfully, and use an
agent's verified replay/load capability when available. Do not promise recovery
of arbitrary unacknowledged agent output.

Permission and filesystem callbacks use separately admitted workers.
Permissions carry process/session generation, request identity, a deadline, and
the exact requested action. A stale answer cannot authorize a replacement
session. No default automatic approval is implied by a sample SDK client.

### 7.4. Dispatch and cancellation semantics

| State                          | Meaning                                                                              |
| ------------------------------ | ------------------------------------------------------------------------------------ |
| accepted                       | Frozen command and required durable records committed                                |
| dispatching                    | Owner recorded intent to send; the external side effect may or may not have occurred |
| running                        | Verified running evidence from the owned ACP execution                               |
| waiting_permission             | Running execution waits on a particular permission generation                        |
| completed / failed / cancelled | Terminal evidence committed with preceding output                                    |
| delivery_uncertain             | A crash/transport break prevents establishing whether submission executed            |

_Table 10: Durable command states and external-effect uncertainty._

The pre-dispatch journal intentionally leaves an uncertainty interval. If the
daemon crashes just before or after writing to agent stdin, it cannot claim
exactly-once execution without agent-supported idempotency or reconciliation.
Reconnect does not authorize a blind prompt resend.

Distinguish JSON-RPC request cancellation, ACP session cancellation, process
termination, and daemon shutdown. A cancellation request/acknowledgement does
not prove the agent stopped or the turn finalized. Persist the request, await
bounded terminal evidence, then escalate according to the process policy and
record the result.

### 7.5. Child process ownership

Use one supervisor for spawn, environment, cwd, stdin/stdout/stderr,
termination, and reaping. The SDK's built-in process adapter has useful Unix
process-group cleanup but inherits the parent environment and has its own
drop/termination semantics. A daemon-owned Tokio process adapter is the
preferred integration where controlled environment, cwd, cgroups, and custom
shutdown are required. Do not give both layers competing ownership.[^32]

Drain stderr independently with a bounded diagnostic tail. Keep protocol stdout
exclusively JSON-RPC. Test wrappers and descendants, EOF, malformed frames,
hung stdin, ignored cancellation, and processes surviving a parent exit.
Windows Job Object semantics need a separate qualification before claiming
parity with Unix process-group cleanup.

A daemon restart cannot generically reattach to arbitrary inherited stdio. The
initial contract drains or terminates owned processes and reconciles sessions
on restart. Seamless handover is deferred until a supervisor and agent protocol
can actually support it.

### 7.6. Publish host metadata and implement machine RPC

Creating a native Loro document is insufficient to expose a usable Lody
session. The hosting spike also needs compatible Flock SessionMeta creation,
machine registration/ownership, agent configuration references, activation
pointers, history-backend selection, and catalogue publication. Verify those
writes with the pinned TypeScript reader and a real existing client.

Before core rollout, implement the supported machine RPC methods with the
actual request/response envelopes and stream names. Ordinary requests use
`<workspaceId>:rpc:req:<machineId>`; response naming has current and legacy
forms. Preserve request deadlines, target identity, authorization, correlation,
retained results, and duplicate-delivery semantics.[^33]

Remote create/send, permission answers, and cancellation enter the same durable
command owners as local CLI operations. A CRDT metadata edit is not
automatically an authorized command; decode dispatch according to the selected
upstream contract. Persist enough request/result evidence to return the same
receipt after a lost reply. Timeout does not authorize new execution.

Request handling stays separate from bulk history synchronization. Bound
pending RPC requests/replies and their disk retention, keep per-method
capabilities explicit, and test control from an existing Lody client. The first
hosting smoke may initiate locally, but a remotely unusable daemon cannot pass
the practical replacement milestone.

## 8. CLI, authentication, and configuration

### 8.1. Authentication follows the deployed flow

The inspected CLI uses Better Auth device authorization with client ID
`lody-cli`. It exchanges the resulting session token for a CLI API key via
`/api/cli/api-key/create`, validates that key through a named Convex query, and
separately obtains workspace-scoped Streams credentials.[^34][^35]

Use oauth2's async device-flow machinery for the compatible grant. Capture
actual endpoint paths, response shapes, polling intervals, pending/slow-down
errors, and expiry behaviour before coding the adapter. Use restson for the
custom JSON exchange and supported queries. Do not invent Proof Key for Code
Exchange (PKCE) or a refresh token if this deployment does not offer that flow.

One auth owner coordinates refresh per credential/workspace generation. A
cancelled waiter releases its own lease without cancelling other consumers'
refresh. Publish tokens atomically and reject late refreshes from revoked
generations. Distinguish invalid credentials from network failures. Expired
credentials block cloud capabilities, not healthy local cached reads.[^36]

Store secrets in an OS credential facility or private credential storage with
atomic replacement; ordinary configuration contains references. Do not forward
daemon cloud credentials into agent environments by default. The OAuth HTTP
adapter must disable redirects and redact token responses. OAuth2's
reqwest/http types and restson's older Hyper/http types are not interchangeable
without an explicit adapter.[^25]

Convex subscription is a separate obligation. Qualify a native subscription
adapter; if a first experiment uses bounded polling of a documented query,
publish its freshness/revocation latency and keep it out of the final
equivalence claim.

### 8.2. Restson stays off dispatch and liveness paths

Restson 1.5.0 is async, but it aggregates whole response bodies and performs
JSON serialization/deserialization synchronously. Its normal timeout does not
pre-empt the later parser, and its error path does not preserve all retry
headers. Trace logging can include sensitive requests/bodies.[^26]

Use it for small typed, paginated control-plane JSON operations on the
maintenance/REST runtime. Before live use, provide a reviewed narrow patch or
upstream extension that:

- Caps streamed response accumulation before exceeding the byte budget.
- Configures finite request/body deadlines and cancellation.
- Retains retry headers needed for backoff.
- Removes or redacts sensitive trace data.
- Separates heavy decode work from the liveness runtime.

An outer Tokio timeout cannot pre-empt synchronous JSON decoding. Bound input
size and isolate the work. Disable unused blocking/native-TLS features where
the chosen dependency graph permits rustls.

### 8.3. OrthoConfig composition and reload

Use released OrthoConfig APIs for typed CLI, environment, file, and default
composition. Load and validate configuration before starting the execution
domains. Use injected environment sources for hermetic precedence tests. Do not
treat illustrative proposed policy APIs as released functionality.[^37]

The single authoritative mode is observe or host. Observer composition does not
expose writer, presence-publisher, or agent-dispatch capabilities, even if the
config contains dormant hosting limits. A mode change requires an explicit
controlled restart; another boolean must not enable hosting behind an
observe-mode label.

Separate operator authority from repository preferences. A checked-out project
config must not raise resource ceilings, change credentials, broaden filesystem
permissions, or select an arbitrary agent executable. Disable project discovery
for those daemon settings.

For reload, parse/validate on a maintenance worker and publish one immutable
configuration generation. Existing turns retain their frozen execution config.
Invalid reload leaves the previous generation active.

Classify settings:

| Reloadable after validation                                                                    | Requires controlled restart or migration                                                                   |
| ---------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Log level, observation retention policy, safe admission reductions, optional refresh intervals | State directory, replica identity, deployment/profile, native backend, transport protocol, database schema |
| Some limits for future work                                                                    | In-flight limits whose reduction would invalidate admitted obligations                                     |

_Table 11: Configuration reload and restart boundaries._

The [configuration example](../contracts/config.example.toml) defines proposed
starting budgets. It is a design contract, not a claim that OrthoConfig
supplies those daemon policies.

Section 13.6 adds the source-semantics matrix, OS-native path policy, and real
binary tests that establish production configuration wiring.

## 9. Resource budgets, operations, and observability

### 9.1. Bound RAM, disk, and individual work

Budget queue bytes and count, not count alone. Include retained input,
decompressed snapshots, native replica allocation, serialization scratch, OS
pipe/socket buffers, SDK queues, database pages, and allocator margin. The
native Loro cache-limit API does not cap all native allocations.[^21]

Start with small fixed worker counts. The supplied configuration proposes two
I/O threads, two replica workers, one maintenance job, four concurrent room
opens, and one agent for the hosting spike. These are starting parameters for
measurement, not measured optima.

Compressed and decompressed snapshot limits differ. Apply compressed-byte
admission before buffering and a decompressed output ceiling during decoding.
Measure native import amplification separately; an encoded-size cap alone does
not establish a resident set size (RSS) bound. Use process memory limits for
containment.

The example permits 128 MiB compressed snapshots while its ordinary durable
memory queue is 64 MiB. Stream large snapshots into quota-reserved spool files
in bounded chunks and queue small descriptors. Do not wait for a byte permit
larger than the queue's entire capacity. Persist or incrementally copy staged
data before committing its checkpoint/cursor; fsync/rename and database
ordering must preserve the same recoverability contract. Native import still
needs a separate admitted memory budget if its API requires contiguous bytes.
Temporary files count against disk quotas and are reclaimed after crash by
reference-aware cleanup, never by deleting a live checkpoint's payload.

A 64-document soft limit is not permission to keep 64 arbitrarily large
documents. Admit against both count and measured/estimated residency. Account
for staging copies and checkpoint work. Eviction releases readers,
subscriptions, and container handles together; it cannot discard unpublished
operations or falsely retain current freshness.

Bound disk spool and journal retention. Reserve capacity for recording
failure/shutdown state. At exhaustion, reject new durable admission, pause
affected feeds, preserve accepted work, and report degraded capabilities. Never
“solve” disk pressure by pruning unreconciled outbox or causal input.

### 9.2. Suggested acceptance targets

These are proposed engineering gates to validate and revise from recorded
workloads, not claims about an implementation that already exists.

| Property              | Initial target and conditions                                                                                                                           |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Liveness scheduler    | p99.9 dispatch lag below 250 ms; no sample over 2 s during the specified stress profile on a host with reserved service CPU                             |
| Presence publication  | Below 5 s p99 from scheduled renewal to transport completion while network/auth/server remain healthy; no local-backlog lease expiry                    |
| Cached local reads    | p95 below 100 ms for bounded catalogue/status pages during replay                                                                                       |
| Observation freshness | p95 below 1 s from durable application of a relevant change to local delivery; network catch-up reported separately                                     |
| Recovery              | Every committed accepted command recoverable; no persisted cursor beyond its recoverable bytes                                                          |
| Memory                | Enforced configured per-domain limits, stable resident set at fixed workload after warm-up; no growth proportional to historical sessions left unopened |
| Fleet qualification   | 60 concurrently active synthetic agents, 10,000 idle catalogue entries, and 200 repository metadata groups                                              |
| Soak                  | At least 72 hours after the deterministic gates pass, spanning multiple auth refreshes, disconnects, and checkpoints                                    |

_Table 12: Proposed acceptance targets and workload conditions._

Record hardware, agent/output rate, payload distribution, largest snapshot,
aggregate resident corpus, CPU allocation, disk latency, and network profile
with every result. Include tens-of-megabytes histories and an 80 MiB snapshot
case because the source reports that scale. Do not require a fixed RSS figure
for an unspecified workload or assume the executor can pause a large import.

### 9.3. Metrics and diagnostics

Record scheduler delay, publication delay, queue bytes/age, durable/apply
watermarks, replay debt, pending causal operations, snapshot size and import
time, worker RSS, storage commit latency, room admission, ACP frame/rate/
request counts, and process cleanup results.

Keep identifiers out of unbounded metric labels. Put scoped operation, session,
room, and generation IDs in sampled traces/diagnostic records. Do not log
prompts, token bodies, file contents, or authorization headers by default.
Formatting and exporters run outside critical callbacks.

Provide `daemon diagnose --json` with capability readiness, oldest queue age,
last successful durable/apply points, token validity class, affected room
counts, and actionable reason codes. “Connected” is not a sufficient health
report.

### 9.4. Shutdown and ownership

Exactly one owner controls each machine identity, replica writer identity,
outbox, and agent process. Enforce local locks and generation fencing. Copied
state on a second host remains a separate risk: where the service offers no
fencing primitive, active-active use of the same identity is unsupported.

Shutdown stops admission, retires publication generations, requests session
drain/cancel according to policy, commits recoverable state, and reaps child
processes. Use bounded deadlines and report any unresolved delivery rather than
inventing successful completion.

Database write-ahead logging (WAL) plus `synchronous=FULL` defines the intended
committed-data promise on a functioning local filesystem. Fault tests
distinguish process kill, OS/power loss, filesystem corruption, and disk-full.
No software plan can promise preservation after arbitrary storage destruction.

Section 13.3 requires the supervisor to confirm termination by joining or
reaping the previous owner before transfer. An abort request alone is not that
confirmation. Section 13.1 defines storage commit and checkpoint qualification.

## 10. Verification strategy

### 10.1. Use upstream as a compatibility oracle

Create licensed, minimized fixtures from the pinned TypeScript implementation
for Loro histories, Flock metadata, raw/zstd snapshots, pending causal
operations, legacy forms, deletion/tombstones, and current command outputs. The
TypeScript/WASM oracle belongs in tests; it is not a hidden production
dependency.

Verify native reads of upstream data, upstream reads of native writes,
merge/replay order, producer identities, and semantically equivalent results.
Do not compare unstable binary bytes where the protocol permits different
encodings; compare documented identities, versions, and projected meaning.

### 10.2. Contract and failure tests

| Relationship or failure               | Required assertion                                                                |
| ------------------------------------- | --------------------------------------------------------------------------------- |
| Crash between receive and cursor save | No cursor covers unavailable bytes                                                |
| Crash after projection commit         | Recovery does not create a second replay event for the same committed application |
| B arrives before A, then restart      | Pending B survives and applies when A arrives                                     |
| Duplicate/reordered input             | Replica converges; semantic commands do not execute twice                         |
| Trimmed cursor                        | Explicit bootstrap retains accepted local work                                    |
| Corrupt snapshot/poison delta         | Room becomes blocked/corrupt; no false current/empty/completed result             |
| Same command key, changed input       | Reject conflict                                                                   |
| Restored database                     | No reused authoring identity/counter; observation cursor reset explicit           |
| Slow Ishiban consumer                 | Source ingestion and heartbeat continue; consumer resumes or resnapshots          |
| Metadata idle before next history     | Execution remains unknown/pending until evidence settles                          |
| Partial catalogue listing             | No fabricated deletion                                                            |
| Flock/transport lease loss            | Connectivity becomes unknown/offline under the actual evidence rules              |
| SDK stdout without newline / flooding | Byte caps and actual SDK credits hold                                             |
| Slow permission callback              | Connection traffic and unrelated sessions continue                                |
| Late permission/result after restart  | Generation mismatch prevents applying it                                          |
| ACP EOF after possible prompt send    | Delivery uncertainty survives restart; no blind resend                            |
| Worker panic or pathological import   | Worker/room isolation preserves other capabilities                                |
| Disk-full                             | Reject new acceptance and retain prior obligations                                |
| Observer attach/close                 | No CRDT, metadata, read-status, or presence mutation                              |

_Table 13: Contract failures and required observable outcomes._

Test relationships rather than snapshots of entire documents or arbitrary
constant values. Examples include projection/event atomicity, contiguous cursor
coverage, one execution owner, bounded ownership of bytes, and terminal-state
dependence on durable evidence.

Use deterministic clocks and fault injection at transaction/publication
boundaries. Property tests should explore duplicate/reordered operations and
state transitions. Model only the small ownership/dispatch/recovery protocols
whose state space adds value; a small FizzBee model is an optional tool, not a
requirement to model the entire application.

### 10.3. Combined adversarial run

Run bulk reconnect replay while one replica imports a pathological snapshot,
SQLite slows, a restson response stalls, an agent floods stdout, and an Ishiban
client stops reading.

Success means bounded memory/spool, no admitted-data loss, explicit capability
degradation, continuing local liveness scheduling, measured publication delay,
and no falsely completed command. Then run the fleet soak with generated agents
before consuming expensive provider inference. A real-agent smoke remains
necessary for the supported ACP/provider profile.

Maintain an offline fixture cache for compilation and contract tests. Run
compilation checks with `--offline` once dependencies/fixtures are prepared.
Separate controlled network interoperability tests from routine CI.

Section 13.7 adds discriminating failure witnesses alongside these combined
runs. Unit, behavioural, property, and small-model checks belong with their
implementation tasks; multi-owner end-to-end suites have dedicated roadmap
acceptance gates.

## 11. Rollout and practical CLI parity

### 11.1. Deployment sequence

1. **Independent observer:** separate data directory, replica identity, and
   credentials/reference. Compare native output with pinned CLI observations.
2. **Disposable hosting workspace:** one agent and Loro-backed session. Exercise
   auth, permissions, cancellation, crash, replay, and peer viewing.
3. **Small production canary:** a separate machine identity or non-overlapping
   dispatch scope; prove process ownership and resource budgets.
4. **Fleet cutover:** drain/stop the TypeScript execution owner, verify child
   release and outbox status, then activate the Rust owner.
5. **Expansion:** add remaining required commands and backend/protection
   profiles after their gates pass.

Do not let both daemons write the same machine/replica identity or share live
SQLite state. Do not copy credentials plus counters to create a second live
writer.

Rollback preserves the Rust data directory and accepted outbox. Stop Rust
admission, establish what actually dispatched, and reconcile before returning
ownership. A schema-compatible export/import requires its own tests. Deleting
the Rust database and restarting TypeScript is not a safe rollback for accepted
but unpublished commands.

### 11.2. Command families

| Family            | First useful delivery                                     | Later parity                                                                           |
| ----------------- | --------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| Auth/workspaces   | Login, status, authorized workspace selection             | Pairing/revocation and additional access profiles                                      |
| Read APIs         | List, status, bounded history, observation, diagnosis     | Advanced filters and backend-specific history                                          |
| Agent execution   | One agent configuration, create/chat, permissions, cancel | Resume/fork/steer/queue, additional agent adapters                                     |
| Daemon lifecycle  | Foreground service, start/stop/status, graceful drain     | Managed install/update and qualified rollback                                          |
| Projects/repos    | Controlled existing working directory                     | Registration, worktrees, branch operations, PR evidence                                |
| Session lifecycle | Accurate active/terminal state                            | Archive/restore/delete with original retention contracts                               |
| Orchestration     | Explicit operation IDs and ownership                      | Child sessions, MCP orchestration, schedules/automation                                |
| Other surfaces    | None required for first spikes                            | Desktop data plane, terminals/previews/files, Roost, end-to-end encryption (E2EE)/iroh |

_Table 14: CLI command families and staged compatibility._

Capture exact flags, JSON envelopes, exit codes, signal behaviour, and errors
before claiming drop-in CLI replacement. Reject unimplemented commands with
specific errors. Keep legacy compatibility formatting separate from the new
domain model.

Inventory the selected production workflow before choosing the canary. Project
registration, worktree/branch handling, archive/restore, resume, steering,
delegation, and provider setup each need an implemented task or an explicit
support exclusion. Promote every capability used by the selected canary to its
cutover prerequisites. A fleet that depends on resumed agents or MCP
orchestration cannot move merely because fresh local prompts work.

Zero-downtime daemon upgrades remain a later capability. Preserve the upstream
supervisor's one-owner and termination-before-replacement rules, but do not
promise arbitrary ACP stdio reattachment.[^3]

## 12. Decisions, gates, and implementation hand-off

### 12.1. Decision register

| Decision               | Resolution                                                                                                          |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------- |
| Core runtime           | Tokio I/O with separate liveness domain and bounded native worker processes                                         |
| Replicated history     | Native Loro; candidate 1.17.1, qualified against existing JS 1.17.0                                                 |
| Workspace metadata     | Native Flock gate; no representation substitution                                                                   |
| Streams                | Audit/reuse first-party Rust client; patch missing obligations narrowly                                             |
| HTTP client allocation | restson for bounded JSON control calls; native streaming transport and OAuth adapter for their respective protocols |
| ACP role/version       | Client host, stable v1, inspected SDK generation                                                                    |
| SDK memory bounds      | Required real credit/framing integration, with narrow patch if necessary                                            |
| Durable state          | Daemon-owned SQLite inbox/outbox/checkpoints/projections; thin CLI                                                  |
| Ishiban event cursor   | New durable journal cursor; explicit reset on restoration                                                           |
| Task/workflow mapping  | External explicit work-item correlation; no inference from execution                                                |
| Initial platform       | Linux daemon; portable core/CLI; Windows lifecycle separately qualified                                             |
| Production fallback    | No silent WASM or TypeScript fallback; bridge status remains visible                                                |

_Table 15: Proposed architecture decisions._

### 12.2. Blocking questions to resolve through implementation work

| Gate                     | Evidence required to proceed                                                                  | If unavailable                                                                            |
| ------------------------ | --------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| Actual deployed profile  | CLI version, supported cloud endpoints, workspace protection/backend mix                      | Narrow the stated support profile; do not assume source HEAD equals deployment            |
| Native Flock reads       | Exact implementation/format access plus native decode, merge, deletion, and recovery fixtures | Keep projection work on a labelled bridge; independent native observation remains blocked |
| Native Flock authoring   | Upstream-readable machine/session metadata and correct clocks/producer ownership              | Hosting remains gated; read-only observation can proceed                                  |
| Rust Streams parity      | Captured bootstrap/live/retry/producer tests against selected service profile                 | Extend or replace only the missing transport adapter                                      |
| Auth/Convex              | Working device exchange, CLI-key validation, workspace access and revocation behaviour        | Observer cannot claim live authorized catalogue parity                                    |
| ACP queue accounting     | Instrumented proof of finite buffers/handles through the SDK boundary                         | Patch the SDK before the hosting spike                                                    |
| Restson safety           | Body caps before allocation, finite deadlines, safe diagnostics, retry metadata               | Harden the adapter before real workspace traffic                                          |
| Ishiban identity         | Explicit work-item/session mapping and stage evidence                                         | Show session observations with unclassified workflow                                      |
| Protected/Roost coverage | Native compatible backend or verified owner-RPC route                                         | Explicit unsupported verdict; promote to prerequisite if essential                        |
| Server durability        | Documented or tested acknowledgement semantics                                                | Name transport acceptance honestly and retain recoverable local state                     |

_Table 16: Blocking compatibility gates and required evidence._

The [implementation roadmap](../roadmap.md) turns these decisions into numbered
tasks and gates. The companion contracts are starting interfaces for
implementation review. They do not constitute a built daemon, a passing
interoperability test, or a migration of existing data.

### 12.3. Requirements coverage

| User requirement                          | Design coverage            |
| ----------------------------------------- | -------------------------- |
| Reimplement CLI and daemon in async Rust  | §§1, 3, 8, 11              |
| Rust ACP SDK                              | §7                         |
| OrthoConfig                               | §8.3                       |
| Rust Loro SDK without WASM where possible | §§2.3–2.5, 5               |
| oauth2 and restson                        | §§8.1–8.2                  |
| Ishiban capabilities first                | §4 and roadmap phase 2     |
| ACP hosting and Loro sync second          | §§5, 7 and roadmap phase 3 |
| Keep busy work off hot paths/event loops  | §§3, 6, 7.2, 9             |
| Mitigate sync loss                        | §§5, 10                    |
| Mitigate skipped heartbeats               | §§6, 9–10                  |

_Table 17: Coverage of the original requirements._

## 13. Amendments for Youxia implementation

These proposed requirements incorporate the storage comparison and the
[Comenq lessons][lessons]. The lessons document distinguishes verified review
findings and merged fixes from a deployment report, an open extraction
proposal, and inferences for Youxia. This section defines the resulting Youxia
contracts; it does not claim that Comenq implements all of them.

### 13.1. Storage engine and schema baseline

Retain SQLite for the first observation and hosting slices. Express persistence
through domain operations such as durable batch ingestion, command acceptance,
checkpoint installation, and projection/event commit. The storage owner owns
their atomicity; adapters elsewhere must not assemble those transactions from
uncoordinated raw SQL calls. Native asynchronous I/O alone would not establish
bounded query CPU, result allocation, or hot-path independence.

Use ordinary rowid tables as the initial schema, including payload-bearing
records. State `NOT NULL` explicitly on required keys. SQLite's guidance treats
`WITHOUT ROWID` as a workload-dependent optimization and describes ordinary
rowid tables as generally preferable for large rows. Changing table form must
preserve required key constraints.[^38] The adjacent storage contract adopts
that baseline; later optimizations require representative measurements.

A successful write statement does not constitute command acceptance. The
storage owner returns acceptance only after the complete required transaction
commits under the qualified durability policy. Verify `synchronous=FULL` and
foreign-key enforcement for each relevant connection. Keep writes outside
liveness and network execution, limit read-transaction lifetime, and schedule
checkpoint work through a bounded owner. SQLite's WAL documentation explains
both full synchronization and the commit latency that automatic checkpointing
can introduce.[^39] Disable automatic checkpointing only after controlled
checkpoint ownership and WAL-growth limits exist.

Turso Database remains an optional engine qualification behind the same domain
operations. The inspected v0.8.3 compatibility document describes experimental
insert-only `WITHOUT ROWID` support and statement-lifetime qualifications for
transaction completion.[^40] Those are versioned findings to recheck for the
candidate under test. They neither establish that Turso cannot meet the
contract nor justify assuming that replacing SQLite preserves it unchanged.

Qualify incoming batch/cursor commits, outbox producer allocation, projection
and observation atomicity, checkpoint installation, output bursts, reconnect
replay, cancellation, process death, and disk exhaustion against both engines.
Measure tail latency, CPU, memory, queue age, and disk growth under the same
workload and durability settings. Compare bounded single-writer scheduling
first, then bounded concurrent Turso transactions where independent rooms allow
them. Preserve per-room order and required atomic commits. A single logical
storage owner need not force every adapter into a single physical writer.

Turso selection requires the shared crash-recovery contract to pass and a
material workload benefit. Record the selected release, driver, transaction
mode, and constraints as a separate decision. Optional qualification does not
block the first two slices and must not lower durability to improve a benchmark.

### 13.2. Contention and progress capacity

Isolation covers resources as well as executor threads. A bulk operation must
not retain a mutex, actor turn, database transaction, publication slot, or
credit that heartbeat renewal, durable ingestion, cancellation, or completion
needs. Moving the operation into `spawn_blocking` does not remove those
dependencies. [Comenq's lock-retaining history scan][lessons] supplies the
concrete failure case.

Capture bounded immutable input and its generation under the shortest practical
ownership boundary. Perform expensive work after releasing contested resources.
Revalidate the generation before committing a derived result. Bound retries
under continuous mutation; once that budget expires, return a specific
retryable/stale result or schedule an explicitly admitted replacement job.

Acquire count and byte admission before creating a connection task, submitting
blocking work, or entering an SDK queue. Credits remain attached through every
handoff until the actual owner releases the resource. Queue depth alone must
not hide tasks waiting for admission or bytes retained in downstream buffers.

Reserve enough capacity at admission for the required completion, cancellation,
failure, and recovery transitions of accepted work. Account for durable
acknowledgements, generation changes, observation entries, WAL growth, and
checkpoint staging. Completion cannot require an ordinary credit that only its
own completion could free. Optional detail and new intake yield to previously
accepted obligations within the declared scheduling policy.

At the configured admission limit, existing work must still record its
disposition and release resources. Physical filesystem exhaustion remains a
separate injected fault: accounting reservations cannot stop another process
consuming the disk. Actual `ENOSPC` blocks the affected capability without
false acceptance or deletion of unreconciled input.

### 13.3. Incarnation recovery and retry policy

Every replacement owner runs recovery before publishing readiness. The recovery
contract applies separately to an in-process task, native replica process, ACP
process, whole daemon, and restored database. A successful spawn proves only
that a replacement exists.

For each boundary, the supervisor must:

1. Fence the previous generation against further state changes.
2. Establish whether the old owner and its outstanding effects have stopped.
3. Reconcile durable claims, interrupted completions, dispatch uncertainty, and
   retained retry state in the domain-defined order.
4. Reconstruct owned state and attach subscriptions with new generation fences.
5. Publish only capabilities whose progress preconditions now hold.

A shutdown timeout or task-abort request does not confirm termination. Retain
handles, await/join tasks, and terminate/reap child processes according to the
qualified platform contract. If exit cannot be established, keep ownership
unresolved and deny conflicting replacement execution. Whole-daemon recovery
tests cannot substitute for restarting only a worker while its parent and open
storage remain alive.

Claim reclamation does not resolve an external side effect. Preserve
`delivery_uncertain` for an ACP prompt that may have reached the agent, and
require supported idempotency or independent reconciliation before
resubmission. Durable local completion records cannot retroactively close the
interval between a remote effect and its local acknowledgement.

Treat wakeup, eligibility, attempt identity, and reported state separately. A
queue mutation, credential refresh, configuration reload, or new subscriber may
trigger re-evaluation; it must not erase a retry floor. Persist server-directed
or application-required retry constraints that must survive restart before
releasing the failed attempt's ownership. Derive diagnostics and scheduling
from the same policy state.

Persist the policy evidence needed to reconstruct a deadline, not a monotonic
clock's process-local `Instant`. Define restart and wall-clock discontinuity
behaviour explicitly, including uncertainty. Keep supervisor backoff state
across short failed runs and reset it only after the declared stable-run
condition. Tests must combine retries with unrelated mutation, reload, refresh,
and replacement so each can wake the owner without bypassing pacing.

### 13.4. Cancellation and operation identity

Audit each `select!`, timeout, and cancellation boundary in ACP framing,
Streams and SSE decoding, local JSON Lines (JSONL), and worker IPC. Record
which owner retains partially consumed bytes and protocol state if a branch
loses the race. Keep framing state in a persistent decoder or retain one read
future across control/timer events when its established cancellation contract
requires that. Do not recreate a stateful read future after discarding an
already consumed prefix.

Once durable acceptance transfers responsibility to an operation owner, that
owner commits completion and observation publication independently of the
requesting future. A CLI disconnect releases response resources; it does not
silently cancel an accepted command. An observer disconnect releases its
subscription. Agent cancellation remains an explicit command with its own
acceptance, escalation, and terminal disposition.

Bind pending permissions, prompt responses, refresh results, process exits, and
projection results to an operation lifetime and owner generation. A reused
session identifier alone cannot authorize a delayed result. Reject
old-generation results after replacement without consuming a new operation's
permissions, credits, or response slot.

### 13.5. IPC negotiation and running-peer diagnostics

Before opening the initial observation stream or admitting a command, the local
client and daemon establish a bounded authenticated handshake. Negotiate a
protocol version or compatible range, supported commands, event/schema
capabilities, relevant limits, and cursor semantics. Include daemon build
identity and instance/generation for diagnosis and replacement detection.
Protocol and capability compatibility determine whether an operation may
proceed; a package version string alone does not.

Provide minimal `daemon status`/`diagnose` output in the first spike. Identify
the running daemon's build, instance, executable/service identity where
available, selected protocol, and relevant capabilities. The installed CLI's
own version cannot stand in for the running process. Keep richer fleet
diagnostics in the later CLI workstream.

Classify unsupported or legacy rejection before a valid stream, absence of a
valid initial reply, loss after stream establishment, and a valid domain error
separately. Test intentionally skewed peers. Comenq's deployment incident and
merged diagnostic repair motivate this gate; capability negotiation is the
additional Youxia requirement, not a capability that repair demonstrated.

This handshake belongs to Youxia's local control and observation surface. It
must not silently alter upstream protocol 7, machine RPC, or cloud Streams wire
formats. Those remain separately qualified compatibility boundaries.

### 13.6. Domain and configuration boundaries

Keep command admission, delivery-state, permission, and evidence-freshness
rules directly testable without sockets, Tokio, Loro, or a database driver.
Check the permitted dependency graph mechanically. Adapters translate wire and
storage representations; operation owners retain atomic guarded transitions.
Extracting a domain rule must not split one serialized read-modify-write
operation into independently locked calls.

Use narrow ports for real external effects and existing interfaces where they
fit. A claim or reservation has command semantics even if it returns a value.
Avoid a generic framework built around speculative reuse. Comenq's open domain
extraction proposal provides a reviewable design example; its unmerged state
provides no evidence of a deployed result.

Specify configuration behaviour before implementing the adapter: source
precedence, explicit values equal to defaults, missing explicit files versus
optional discovery failure, empty values, list syntax, environment-name case,
OS-native paths, secrets, repository authority, and reloadability. Preserve
meaningful I/O and parsing failures instead of converting them into missing
values. Each chosen policy needs distinguishing inputs in its acceptance test.

Inject environment and path access through a narrow OS-aware production seam.
Do not silently lose non-Unicode paths or panic because of an unrelated
non-Unicode environment variable. Where an external protocol requires Unicode,
reject an unsupported value at that named boundary with a specific diagnostic.
A convenience provider or error-conversion helper must not change the chosen
source semantics accidentally.

Exercise the actual CLI and daemon composition roots with controlled subprocess
environments and native paths. Tests of a mocked provider alone do not prove
that production wiring uses it. Invalid reload must preserve the active
configuration generation and existing admitted obligations; valid reload must
retain any established retry floor and frozen execution configuration.

### 13.7. Discriminating failure evidence

Each reliability contract needs a small witness that rejects its plausible
incorrect implementation. Combine those witnesses with the end-to-end and soak
gates in §10; neither test scale replaces the other. Coordinate fault injection
deterministically where possible, and assert the external consequence rather
than a timer firing, a task spawning, or a mock being called.

Presence witnesses run in a hosting fixture or controlled protocol harness.
Observe-mode integration still proves that observation publishes no presence or
other upstream mutations.

| Contract                               | Discriminating witness                                                                                                                                         |
| -------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Bulk work preserves control progress   | Hold a bulk history/import operation at a deterministic barrier while a remote peer receives fresh heartbeat publication and unrelated accepted work completes |
| Every incarnation recovers             | Fail/restart only one worker while the daemon and open store remain alive; prove the replacement makes progress after reconciling old claims                   |
| Retry policy survives activity         | Inject unrelated mutations, token refresh, and configuration reload before the retry floor; prove no early attempt occurs                                      |
| Retry policy survives restart          | Restart the relevant owner before eligibility, then prove persisted policy controls both scheduling and reported state                                         |
| Frame reads preserve consumed input    | Split a frame across timer/control events and complete it without losing or repeating the prefix                                                               |
| Acceptance outlives the caller         | Disconnect the CLI or observer after acceptance and verify durable completion and event publication continue                                                   |
| Generation fences protect replacements | Deliver an old permission/result after replacing the execution; prove it cannot authorize or update the new operation                                          |
| Admission leaves progress capacity     | Fill ordinary admission, then complete/cancel existing work and verify its disposition commits                                                                 |
| Peer skew remains diagnosable          | Connect a new CLI to an intentionally old/rejecting daemon and distinguish rejection, no initial frame, stream loss, and valid domain errors                   |
| Configuration reaches production       | Invoke the real binaries with values that distinguish precedence, error categories, and native-path handling                                                   |
| Shutdown establishes ownership release | Block or ignore termination, prove no conflicting owner starts, then observe join/reap before transfer                                                         |

_Table 18: Small failure witnesses for the amended contracts._

Keep fixture inputs, fault boundaries, expected evidence, and remaining
limitations beside the relevant implementation task. A test that fails for an
unrelated startup error or passes because the expected value equals a default
does not establish its intended contract. Record unexecuted proposals as
planned checks, never completed evidence.

## Sources

The Lody links identify the inspected compatibility revision. Library links
identify versions where available; Tokio's API documentation remains a moving
reference to requalify during implementation. The Comenq companion records its
own source statuses. Proposed architecture and acceptance targets are design
requirements, not source measurements.

[^1]: [Lody compatibility baseline commit](https://github.com/LodyAI/Lody/commit/d3179e1f7538b61d0a6acc6be0a324281be4e3c0).

[^2]: [Lody fleet ownership](https://github.com/LodyAI/Lody/blob/d3179e1f7538b61d0a6acc6be0a324281be4e3c0/apps/cli/src/lib/lody-fleet.ts).

[^3]: [Lody daemon supervision and replacement](https://github.com/LodyAI/Lody/blob/d3179e1f7538b61d0a6acc6be0a324281be4e3c0/apps/cli/src/commands/daemon-runner.ts).

[^4]: [Lody presence scheduling and freshness](https://github.com/LodyAI/Lody/blob/d3179e1f7538b61d0a6acc6be0a324281be4e3c0/.agents/docs/cli-lib-loro-presence.md).

[^5]: [Lody WASM heap exhaustion investigation](https://github.com/LodyAI/Lody/blob/d3179e1f7538b61d0a6acc6be0a324281be4e3c0/.agents/notes/implemented/bug-fix/2026-11-09-loro-wasm-heap-exhaustion.md).

[^6]: [Lody history-write scaling investigation](https://github.com/LodyAI/Lody/blob/d3179e1f7538b61d0a6acc6be0a324281be4e3c0/.agents/notes/implemented/bug-fix/2026-10-14-daemon-history-writes-scale-with-turn-size.md).

[^7]: [Lody pending-operation persistence investigation](https://github.com/LodyAI/Lody/blob/d3179e1f7538b61d0a6acc6be0a324281be4e3c0/.agents/notes/implemented/bug-fix/2026-10-22-loro-pending-persistence.md).

[^8]: [Lody SQLite replica store and cursor ownership](https://github.com/LodyAI/Lody/blob/d3179e1f7538b61d0a6acc6be0a324281be4e3c0/apps/cli/src/lib/loro/sqlite-repo-store.ts).

[^9]: [Lody session observation specification](https://github.com/LodyAI/Lody/blob/d3179e1f7538b61d0a6acc6be0a324281be4e3c0/specs/cli-session-observe.md).

[^10]: [Lody shared session metadata schema](https://github.com/LodyAI/Lody/blob/d3179e1f7538b61d0a6acc6be0a324281be4e3c0/packages/shared/src/schema.ts).

[^11]: [Lody legacy task types](https://github.com/LodyAI/Lody/blob/d3179e1f7538b61d0a6acc6be0a324281be4e3c0/packages/shared/src/task-types.ts).

[^12]: [Lody Streams transport](https://github.com/LodyAI/Lody/blob/d3179e1f7538b61d0a6acc6be0a324281be4e3c0/apps/cli/src/lib/loro/streams-transport.ts).

[^13]: [Lody snapshot codec](https://github.com/LodyAI/Lody/blob/d3179e1f7538b61d0a6acc6be0a324281be4e3c0/packages/shared/src/streams-snapshot-codec.ts).

[^14]: [Lody local data-plane protocol](https://github.com/LodyAI/Lody/blob/d3179e1f7538b61d0a6acc6be0a324281be4e3c0/.agents/docs/cli-lib-local-loro-data-plane.md).

[^15]: [Lody Flock workspace integration](https://github.com/LodyAI/Lody/blob/d3179e1f7538b61d0a6acc6be0a324281be4e3c0/packages/shared/src/workspace-flock.ts).

[^16]: [Lody mobile Flock decoder](https://github.com/LodyAI/Lody/blob/d3179e1f7538b61d0a6acc6be0a324281be4e3c0/apps/mobile/ios/packages/LodyKit/Sources/LodyKit/Cloud/FlockDecoder.swift).

[^17]: [Lody Roost history feature gate](https://github.com/LodyAI/Lody/blob/d3179e1f7538b61d0a6acc6be0a324281be4e3c0/.agents/notes/implemented/feature/2026-10-08-roost-history-feature-gate.md).

[^18]: [ACP Rust SDK 5.2.0](https://docs.rs/agent-client-protocol/5.2.0/agent_client_protocol/).

[^19]: [ACP SDK manifest at the inspected revision](https://github.com/agentclientprotocol/rust-sdk/blob/91d368ad8b6761f314da9095c4a030d365c079a9/Cargo.toml).

[^20]: [OrthoConfig manifest at the inspected revision](https://github.com/leynos/ortho-config/blob/38812c563e3953a490e3efc202609f37e21a0517/Cargo.toml).

[^21]: [Loro 1.17.1 native document API](https://docs.rs/loro/1.17.1/loro/struct.LoroDoc.html).

[^22]: [Lody CLI dependency manifest](https://github.com/LodyAI/Lody/blob/d3179e1f7538b61d0a6acc6be0a324281be4e3c0/apps/cli/package.json).

[^23]: [Native Streams client 0.1.0](https://docs.rs/crate/loro-streams-client/0.1.0).

[^24]: [Lody workspace dependency versions](https://github.com/LodyAI/Lody/blob/d3179e1f7538b61d0a6acc6be0a324281be4e3c0/pnpm-workspace.yaml).

[^25]: [OAuth2 5.0.0](https://docs.rs/oauth2/5.0.0/oauth2/).

[^26]: [Pinned Restson implementation](https://github.com/spietika/restson-rust/blob/f9ae5a4d697b8cc83f568bb87a3a6730f668523b/src/lib.rs).

[^27]: [ACP Rust SDK 5.2.0 ordered dispatch](https://docs.rs/agent-client-protocol/5.2.0/agent_client_protocol/concepts/ordering/index.html).

[^28]: [Tokio blocking-task contract](https://docs.rs/tokio/latest/tokio/task/fn.spawn_blocking.html).

[^29]: [Tokio missed-tick behaviour](https://docs.rs/tokio/latest/tokio/time/enum.MissedTickBehavior.html).

[^30]: [Lody ACP runner](https://github.com/LodyAI/Lody/blob/d3179e1f7538b61d0a6acc6be0a324281be4e3c0/apps/cli/src/agent/acp-runner.ts).

[^31]: [Pinned ACP SDK JSON-RPC queues and framing](https://github.com/agentclientprotocol/rust-sdk/blob/91d368ad8b6761f314da9095c4a030d365c079a9/src/agent-client-protocol/src/jsonrpc.rs).

[^32]: [Pinned ACP SDK agent-process adapter](https://github.com/agentclientprotocol/rust-sdk/blob/91d368ad8b6761f314da9095c4a030d365c079a9/src/agent-client-protocol/src/acp_agent.rs).

[^33]: [Lody machine RPC protocol](https://github.com/LodyAI/Lody/blob/d3179e1f7538b61d0a6acc6be0a324281be4e3c0/packages/loro-streams-rpc/README.md).

[^34]: [Lody device authorization and CLI credentials](https://github.com/LodyAI/Lody/blob/d3179e1f7538b61d0a6acc6be0a324281be4e3c0/apps/cli/src/lib/auth.ts).

[^35]: [Lody cloud CLI port](https://github.com/LodyAI/Lody/blob/d3179e1f7538b61d0a6acc6be0a324281be4e3c0/apps/cli/src/lib/cloud-cli-port.ts).

[^36]: [Lody Streams token management](https://github.com/LodyAI/Lody/blob/d3179e1f7538b61d0a6acc6be0a324281be4e3c0/packages/shared/src/loro-streams-token/README.md).

[^37]: [OrthoConfig 0.10.0 user guide at the inspected revision](https://github.com/leynos/ortho-config/blob/38812c563e3953a490e3efc202609f37e21a0517/docs/users-guide.md).

[^38]: [SQLite guidance for rowid and WITHOUT ROWID tables](https://www.sqlite.org/withoutrowid.html).

[^39]: [SQLite WAL synchronization and checkpointing](https://www.sqlite.org/wal.html).

[^40]: [Turso v0.8.3 compatibility and transaction behaviour](https://github.com/tursodatabase/turso/blob/v0.8.3/COMPAT.md).

[lessons]: ../lessons-on-daemon-design-and-hot-path-preservation.md
[section-1]: #1-decision-and-scope
[section-10]: #10-verification-strategy
[section-11]: #11-rollout-and-practical-cli-parity
[section-12]: #12-decisions-gates-and-implementation-hand-off
[section-13]: #13-amendments-for-youxia-implementation
[section-2]: #2-verified-baseline-and-compatibility-boundaries
[section-3]: #3-components-and-runtime-isolation
[section-4]: #4-ishiban-observation-and-replay
[section-5]: #5-native-replication-and-durability
[section-6]: #6-heartbeats-liveness-and-readiness
[section-7]: #7-acp-hosting-with-durable-loro-sync
[section-8]: #8-cli-authentication-and-configuration
[section-9]: #9-resource-budgets-operations-and-observability
