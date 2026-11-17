# Youxia roadmap

Goals: give Ishiban trustworthy, resumable session observations; host Agent
Client Protocol (ACP) agents with native Loro synchronization; and preserve
liveness and durable progress under load. This roadmap turns [RFC 0001][design]
into the first observation spike, the second hosting spike, and a controlled
fleet rollout. The [Linux architecture][architecture] and RFC §14 refine the
component and process boundaries: Magitek supplies bounded ACP in `youxiad`,
`arun` retains agent transport, and murder implements Flock metadata. The
implementation uses async Rust, ortho-config, native Loro, oauth2, and restson;
Magitek owns qualification of its ACP implementation dependency. The source
baseline remains Lody commit d3179e1f7538b61d0a6acc6be0a324281be4e3c0; the
actual deployment profile is an early compatibility gate.

The structure follows the [roadmap skill][roadmap-skill] and
[conventions][roadmap-conventions] in leynos/df12-documentation-skills at
commit 4a28c8953d3ccc2b5369b46cf042b53257d418de. GIST means Goals, Ideas,
Steps, and Tasks: each phase carries a falsifiable idea, each step answers a
delivery question, and each numbered checkbox defines a review-sized unit with
dependencies, design references, and acceptance criteria. Future ADRs belong in
docs/adrs/ and future RFCs in docs/rfcs/. The roadmap promises no delivery
dates; test durations and latency budgets describe acceptance only.

All tasks remain unchecked pending their acceptance evidence. Unit,
behavioural, property, and small-model checks belong with the capabilities they
validate; explicit end-to-end tasks cover cross-component and combinatorial
failure behaviour. Native catalogue access, durable cursor coverage, and
bounded execution remain release gates. No production WASM or hidden TypeScript
path can satisfy them. Dependencies control eligibility, including the
conditional promotion rules in phase 5. The RFC preserves the original plan and
records the Youxia amendments in §13. The [Comenq lessons][lessons] supply the
implementation evidence behind those amendments. SQLite remains the initial
storage baseline; optional Turso qualification in step 5.7 does not block
either spike.

Linux service/resource enforcement now enters the first hosting slice.
Transparent turn continuation after daemon death requires the separate
Magitek/host restoration gate; raw process and byte survival cannot satisfy it.
All corresponding implementation tasks remain unchecked.

## 1. Foundational contracts and isolation boundaries

Idea: if the project proves its native codecs, actual SDK queue boundaries, and
deployed protocol profile before building features, the two spikes can reuse
one bounded architecture without hiding a JavaScript runtime or an incompatible
cloud assumption underneath them.

This phase settles the dependencies most likely to invalidate the design. It
produces a buildable skeleton, fixtures, and executable boundary probes. It
does not attempt CLI feature parity.

### 1.1. Prove the compatibility surface before choosing adapters

Can native Rust read the catalogue and histories used by the deployed Lody
profile? The answer controls whether the observation spike can proceed. See RFC
0001 §§2, 5, and 12.

- [ ] 1.1.1. Record the deployed compatibility profile and capture fixtures.

  - [ ] See RFC 0001 §§2, 5, and 12.
  - [ ] Record client/server versions, content mode, history backend, Flock
    format, Streams capabilities, token endpoints, and presence protocol.
  - [ ] Success: sanitized fixtures carry source/version provenance; the matrix
    distinguishes observed support from undocumented assumptions.

- [ ] 1.1.2. Qualify murder against the native Flock format contract.

  - [ ] Requires 1.1.1.
  - [ ] See RFC 0001 §§2.3 and 12.2.
  - [ ] Record murder implementation/format access, licence, supported versions,
    clocks, tombstones, and its native replica-worker boundary.
  - [ ] Success: an evidence-backed decision identifies a usable native route or
    records a blocking gap. A new codec port requires explicit review-sized work
    before this gate can authorize integration; a JavaScript bridge cannot pass
    it.

- [ ] 1.1.3. Integrate the qualified murder catalogue reader.

  - [ ] Requires 1.1.2 and 1.1.1.
  - [ ] See RFC 0001 §§2.3, 5, and 10.1.
  - [ ] Implement the selected format adapter with merge, deletion, and clock
    semantics; keep fixture generation outside the production runtime.
  - [ ] Success: native reads and replay of retained source records match the
    reference state, tombstones, and clocks. Native authoring remains a separate
    hosting gate.

- [ ] 1.1.4. Build the native Loro and protocol differential corpus.

  - [ ] Requires 1.1.1. See RFC 0001 §§2, 5, and 10.
  - [ ] Cover snapshots, updates, pending causal imports, Unicode, legacy
    history, stream envelopes, and unknown optional fields separately.
  - [ ] Success: both implementations agree on semantic state and permitted
    round-trips; unsupported versions fail explicitly without modification.

### 1.2. Establish owners whose work cannot stall liveness

Can a stalled replica operation leave control I/O and liveness responsive? This
step fixes process ownership and admission before feature code grows. See RFC
0001 §§3, 6, and 9.

- [ ] 1.2.1. Create the Rust workspace and pin the reviewed dependency graph.

  - [ ] Requires 1.1.1.
  - [ ] See RFC 0001 §§1–3, 8, 10.3, and 13.6.
  - [ ] Separate pure domain policy from CLI, daemon, protocol, storage,
    replica, and ACP adapters; check allowed dependencies mechanically.
  - [ ] Success: domain transitions run without sockets, Tokio, Loro, or a
    database driver; Linux binaries contain no production Node/WASM execution.
    Prepared dependencies and fixtures support offline CI compilation and
    contract checks; network interoperability runs separately.

- [ ] 1.2.2. Create separate control, I/O, and maintenance execution domains.

  - [ ] Requires 1.2.1.
  - [ ] See RFC 0001 §§3.1–3.3, 9, and 13.2.
  - [ ] Give control its own runtime and network resources; document lock,
    actor-turn, transaction, and credit ownership across expensive operations.
  - [ ] Success: a deliberately blocked maintenance job leaves local control and
    cached health responsive without retaining resources control needs.
    Immutable inputs or generation-checked reads use bounded revalidation;
    moving a retained lock into a blocking task cannot satisfy the gate.

- [ ] 1.2.3. Implement bounded supervisor-to-replica process messaging.

  - [ ] Requires 1.2.2.
  - [ ] See RFC 0001 §§3.1–3.3, 5, 9, 13.3, and 13.4.
  - [ ] Start a fixed small pool, initially two workers, with one owner per
    document, retained task/process handles, and generation-fenced messages.
  - [ ] Success: stuck-worker termination leaves control responsive; join/reap
    confirms old-owner exit before transfer. Fragmented inter-process
    communication (IPC) frames survive timer/control events. Late, duplicate,
    and reordered replies cannot mutate a replacement; credits remain charged
    until downstream release.

- [ ] 1.2.4. Define and instrument every queue and resource budget.

  - [ ] Requires 1.2.3. See RFC 0001 §§3, 9, 10, and 13.2.
  - [ ] Specify count, bytes, age, owner, cancellation, and saturation policy;
    admit before spawning/submitting work and charge downstream retention.
  - [ ] Reserve capacity for accepted work's completion, cancellation,
    acknowledgements, recovery records, write-ahead log (WAL) growth, and
    checkpoint staging.
  - [ ] Success: overload probes bound queued and in-flight work; filling
    ordinary admission leaves progress transitions possible without acquiring an
    ordinary credit that only those transitions can release. Physical disk
    exhaustion remains a separately reported fault.

### 1.3. Verify the library boundaries that wrappers cannot repair

Do the chosen ACP and REST libraries expose the controls the daemon needs? This
step chooses a minimal patch or adapter before dependent features rely on a
boundary that does not actually exist. See RFC 0001 §§7, 8, and 12.

- [ ] 1.3.1. Qualify the Magitek framing and downstream credit contract.

  - [ ] Requires 1.2.1 and 1.2.4.
  - [ ] See RFC 0001 §§7.2, 10, and 12.2.
  - [ ] Trace frame allocation, decode, request, notification, response,
    callback, and task ownership through Magitek's selected implementation;
    instrument a slow-consumer probe and retained leases across closure.
  - [ ] See the [Linux architecture][architecture] §§3.3, 9, and 11. Conditional
    Wireframe reuse requires the public-API ACP toy and the full budget contract.
  - [ ] Success: the report identifies every retained buffer and permit
    lifetime, records any unbounded path, and specifies the minimal patch
    contract. Hosting still requires the implemented and measured boundary in
    3.2.2.

- [ ] 1.3.2. Enforce REST body admission and finite request lifetimes.

  - [ ] Requires 1.2.1 and 1.2.4.
  - [ ] See RFC 0001 §§8.2, 9, and 10.
  - [ ] Add body limits before collection, request/body deadlines, cancellation,
    and bounded decoding on the REST maintenance domain.
  - [ ] Success: oversized and slowly streamed responses respect byte and
    lifetime limits; synchronous decoding cannot occupy control or transport
    callbacks.

- [ ] 1.3.3. Preserve REST retry evidence and redact diagnostics.

  - [ ] Requires 1.3.2.
  - [ ] See RFC 0001 §§8.1–8.2, 9.3, and 12.2.
  - [ ] Retain status and retry headers, apply endpoint redirect policy, and
    remove credential/request/response payloads from tracing.
  - [ ] Success: retryable, rejected, and redirected responses produce distinct
    typed outcomes; error reporting preserves retry guidance without exposing
    secrets.

- [ ] 1.3.4. Record spike scope and migration authority as explicit ADRs.

  - [ ] Requires 1.1.1–1.1.4 and 1.3.3.
  - [ ] See RFC 0001 §§1, 2, 8, 11, 12, and 13.6.
  - [ ] Inventory the selected production scripts/UI workflows, including
    resume, steering, MCP, and automation only where used; map each to a
    prerequisite or exclusion. Define atomic guarded transitions and narrow
    external-effect ports without splitting read-modify-write ownership.
  - [ ] Success: ADRs identify retired Task semantics, supported history/content
    modes, compatibility evidence, state paths, and one execution owner. Each
    gate has an owner and pass/fail evidence; queries cannot hide dispatch.

Task 1.3.1 can proceed alongside observation work. Task 3.2.2 must implement
and measure the resulting queue and credit contract before hosting; neither
task blocks phase 2's read-only data path.

### 1.4. Establish a bounded, versioned local control connection

Can a CLI establish which daemon owns the connection before requesting work?
This step prevents unsupported commands from appearing as lost execution and
provides minimal diagnostics before the first observation feed. See RFC 0001
§§4.4, 8, and 13.5, and the [Comenq lessons][lessons].

- [ ] 1.4.1. Implement local IPC protocol and capability negotiation.
  - [ ] Requires 1.2.2 and 1.2.4. See RFC 0001 §13.5.
  - [ ] Authenticate the local peer, negotiate protocol range, commands, event
    features, limits, and cursor semantics under bounded frame/deadline rules.
  - [ ] Success: newer/older compatible peers negotiate a common contract; the
    CLI reports an explicit unsupported-peer result for incompatible or
    pre-handshake peers before a stream opens or command is admitted. Pre-stream
    rejection, malformed initial reply, and post-establishment loss remain
    distinct.
- [ ] 1.4.2. Expose minimal running-daemon identity and status diagnostics.
  - [ ] Requires 1.4.1. See RFC 0001 §§6.3, 9.3, and 13.5.
  - [ ] Return build identity, daemon instance/generation, supported operations,
    and executable/service identity where available from the connected daemon.
  - [ ] Success: a newly installed CLI connected to an older running daemon
    identifies the actual peer and unsupported capability. Build versions aid
    diagnosis; negotiated compatibility determines whether work can proceed.

## 2. First spike: trustworthy Ishiban observation

Idea: if one native replica can provide a resumable, evidence-based session
projection without opening every transcript or performing execution writes,
Ishiban gains a reliable fleet data source before agent hosting exists.

The slice delivers a small CLI and daemon observation API, plus a thin adapter
to Ishiban's existing Falcon/SSE boundary. It preserves the distinction between
workflow, execution, archive state, and freshness. Phase 2 cannot pass while
native catalogue access remains unproven.

### 2.1. Authenticate one workspace with controlled network ownership

Can the observer discover and reauthorize its workspace without placing
configuration or token work on callbacks? The result establishes the auth owner
that later hosting reuses. See RFC 0001 §§3, 4, and 8.

- [ ] 2.1.1. Implement startup configuration and private credential loading.

  - [ ] Requires 1.2.1, 1.3.3, and 1.3.4. See RFC 0001 §§8, 9, and 13.6.
  - [ ] Specify precedence, explicit-default, missing-file, discovery, empty,
    list, and environment-name case semantics; use injected OS-aware sources.
    Preserve OS-native paths and forbid project-level authority expansion.
  - [ ] Success: controlled real-binary tests distinguish source precedence and
    specific startup errors, preserve supported non-Unicode paths, and tolerate
    unrelated non-Unicode variables. Validated immutable configuration and
    private credentials load before hot paths start; no callback rereads files.

- [ ] 2.1.2. Implement the deployed OAuth device authorization flow.

  - [ ] Requires 2.1.1.
  - [ ] See RFC 0001 §§2.2, 8.1, and 12.2.
  - [ ] Use oauth2 with the captured client ID, endpoints, polling, expiry, and
    slow-down semantics; disable redirects in the OAuth client.
  - [ ] Success: pending, rejected, expired, cancelled, and successful grants
    follow reference behaviour, and no refresh-token or PKCE flow is invented.

- [ ] 2.1.3. Exchange and store the CLI API key under one credential owner.

  - [ ] Requires 2.1.2.
  - [ ] See RFC 0001 §§8.1–8.2 and 9.3.
  - [ ] Use the hardened restson adapter for the custom key exchange and
    validation; replace private credential state atomically.
  - [ ] Success: interrupted writes retain a valid credential generation,
    rejected credentials do not become timeout retries, and no daemon credential
    enters an agent environment by default.

- [ ] 2.1.4. Implement authorized workspace discovery and access tracking.

  - [ ] Requires 2.1.3.
  - [ ] See RFC 0001 §§2.2, 8.1, and 12.2.
  - [ ] Qualify the native Convex subscription path; label any bounded-query
    polling experiment with its freshness and revocation limits.
  - [ ] Success: workspace access changes and revocation match the selected
    contract; a polling experiment cannot claim subscription equivalence.

- [ ] 2.1.5. Coordinate workspace Streams tokens by credential generation.

  - [ ] Requires 2.1.4.
  - [ ] See RFC 0001 §§5.1, 6.2, 8.1, and 13.4.
  - [ ] Share one refresh operation per scope, publish immutable token
    generations, and give each waiter an independently cancellable lease.
  - [ ] Success: cancelled waiters leave other consumers' refresh intact; stale
    refreshes and old-token failures cannot replace/revoke newer credentials.
    Completion and notifications remain owner responsibilities when a caller
    disconnects. Task 2.2.6 integrates durable retry eligibility before release.

### 2.2. Keep an observer replica recoverable across interruptions

Can the observer distinguish bytes received, state durably stored, and state
applied? This determines whether reconnect can avoid silent loss. See RFC 0001
§§5, 6, and 9.

- [ ] 2.2.1. Implement the storage owner and atomic incoming batch journal.

  - [ ] Requires 1.1.4, 1.2.3, and 1.2.4.
  - [ ] See RFC 0001 §§5.2, 9.4, 10.2, and 13.1; contracts/storage.sql.
  - [ ] Expose domain operations over versioned SQLite with a dedicated bounded
    writer, bounded readers, WAL/FULL durability, explicit checkpoint policy,
    ordinary rowid tables, and explicit required key nullability.
  - [ ] Success: explicit transaction completion precedes acknowledgement;
    complete incoming bytes and their cursor commit atomically. Crash, failed
    commit, null-key, and reordered-input cases preserve recoverability without
    blocking control behind a database transaction.

- [ ] 2.2.2. Stage large snapshots through quota-reserved bounded spooling.

  - [ ] Requires 2.2.1 and 1.2.4.
  - [ ] See RFC 0001 §§5.1, 5.3, and 9.1.
  - [ ] Reserve disk space, stream bounded chunks, queue descriptors, and apply
    distinct compressed, decompressed, and native-import budgets.
  - [ ] Success: an admitted 80 MiB snapshot larger than the ordinary memory
    queue makes progress without an impossible byte permit; crash cleanup
    preserves referenced payloads, and no cursor covers uncommitted staged
    bytes.

- [ ] 2.2.3. Reconstruct observer replicas from retained durable input.

  - [ ] Requires 2.2.1 and 2.2.2.
  - [ ] See RFC 0001 §§5.2–5.3, 9.1, 10.2, and 13.3.
  - [ ] On every owner incarnation, fence old work, reconcile durable recovery
    records, and replay the base plus required input before publishing
    readiness. Retain causal gaps and block poisoned rooms; defer unsafe
    compaction.
  - [ ] Success: worker-only restart with the daemon/store still open and whole
    restart both restore progress. B-before-A survives two restarts and later
    convergence; projection watermarks suppress duplicate events, never imports
    needed to rebuild the document.

- [ ] 2.2.4. Implement the selected native durable-Streams read adapter.

  - [ ] Requires 2.2.3 and 2.1.5. See RFC 0001 §§2, 5, 12, and 13.4.
  - [ ] Protected workspaces also require 5.1.2; Roost-backed observations also
    require 5.2.1. Promote those gates when the first scope needs them.
  - [ ] Qualify the Rust Streams candidate against deployed envelopes; audit
    each read boundary for cancellation ownership; retain decoder state or one
    frame future across timer/control events. Implement only missing extensions
    behind the adapter.
  - [ ] Success: fragmented/incomplete bodies, duplicates, expired cursors, and
    malformed records converge or block explicitly. Timer/control wakeups retain
    consumed frame prefixes; interrupted batches replay from the committed
    cursor, and no poison record advances it by being skipped.

- [ ] 2.2.5. Add an independent presence receiver and freshness projection.

  - [ ] Requires 2.1.5 and 2.2.4. See RFC 0001 §§4–6.
  - [ ] Decode the actual ephemeral protocol and retain evidence age separately
    from durable document connectivity.
  - [ ] Success: fresh evidence remains online until expiry, absence means
    offline only with a confirmed synchronized view, and uncertain transport
    becomes unknown without inventing a completed turn.

- [ ] 2.2.6. Persist retry eligibility for reconnect and token-refresh owners.

  - [ ] Requires 2.2.4 and 2.1.5. See RFC 0001 §§5.5, 8.1, and 13.3.
  - [ ] Keep wakeups, attempt identity, eligibility, and reported waiting reason
    separate. Persist policy-required retry floors and reconstruct monotonic
    deadlines under the clock-discontinuity policy.
  - [ ] Success: unrelated mutations, subscriber arrivals, refresh completion,
    injected configuration-generation changes, and owner restart cannot bypass
    an active retry floor; diagnostics derive from the same state as scheduling.
    Backoff resets only after the documented stable-run or successful-attempt
    condition. Task 4.2.4 later exercises the real reload entry point.

### 2.3. Project useful session facts at bounded cost

Can Ishiban obtain trustworthy state without reading all message bodies? This
step defines which facts belong in the board and which remain unknown. See RFC
0001 §§2, 4, and 9.

- [ ] 2.3.1. Implement watch-before-list catalogue acquisition.
  - [ ] Requires 2.2.4 and 1.1.3. See RFC 0001 §§4, 5, and 10.
  - [ ] Reconcile changes during enumeration and preserve archive, deletion,
    project, branch, and PR facts as separate fields.
  - [ ] Success: creation, update, archive, and deletion races during initial
    listing match a reference replay before `ready` is emitted.
- [ ] 2.3.2. Implement lazy history-directory hydration and eviction.
  - [ ] Requires 2.3.1 and 1.2.4. See RFC 0001 §§3–5 and 9.
  - [ ] Start with four concurrent acquisitions; separately bound active
    document count/bytes and expose deferred or unavailable rows.
  - [ ] Success: large idle catalogues keep bodies unopened; busy sessions
    retain terminal-proof tracking, and eviction never discards unapplied or
    unsent state or falsely changes a turn outcome.
- [ ] 2.3.3. Implement the versioned Ishiban session projection.
  - [ ] Requires 2.2.5 and 2.3.2. See RFC 0001 §§2 and 4 and
    `contracts/ishiban-session.schema.json`.
  - [ ] Use stable Session IDs and explicit external work-item mappings; retain
    independent execution, workflow, archive, and freshness fields.
  - [ ] Success: fixtures prove that idle, archived, offline, merged PR, and
    completed turn never substitute for one another; missing task correlation or
    workflow evidence remains explicitly unknown.

### 2.4. Expose a resumable feed to the existing Ishiban service

Can a disconnected consumer recover one consistent board state without
depending on a process-local JSONL sequence? The result defines the durable
consumer contract. See RFC 0001 §§4, 5, and 9.

- [ ] 2.4.1. Commit projections and replay events atomically.

  - [ ] Requires 2.3.3 and 2.2.3.
  - [ ] See RFC 0001 §§4.3, 5.2, and 10.2.
  - [ ] Persist applied progress, bounded projection changes, journal identity,
    and monotonically sequenced events in the same commit.
  - [ ] Success: crash and replay cases cannot expose a projection without its
    event or publish the same committed change twice; restoration cannot reuse
    an old journal identity.

- [ ] 2.4.2. Serve bounded snapshot generations with replay watermarks.

  - [ ] Requires 2.4.1.
  - [ ] See RFC 0001 §§4.3 and 9.1.
  - [ ] Materialize quota-bounded immutable snapshot pages and expiring tokens;
    define replay retention and explicit reset responses.
  - [ ] Success: concurrent updates cannot fall between snapshot and follow,
    slow readers hold no indefinite SQLite transaction, and expired or foreign
    cursors cannot silently jump to the present.

- [ ] 2.4.3. Expose authenticated snapshot, watch, and JSONL interfaces.

  - [ ] Requires 2.4.2, 1.2.4, and 1.4.2.
  - [ ] See RFC 0001 §§4.3–4.4, 8, 9, 13.4, and 13.5.
  - [ ] Require negotiated capabilities; bound consumer queues, frame readers,
    versioned errors, optional detail pages, and oversized required-row errors.
  - [ ] Success: slow clients cannot stall replication or other consumers;
    fragmented reads survive control events, and oversized rows cannot loop
    through resnapshots. Disconnect releases only the subscription and retains
    the explicit replay/reset route.

- [ ] 2.4.4. Provide the upstream observe-v1 compatibility view.

  - [ ] Requires 2.4.3 and 1.1.1.
  - [ ] See RFC 0001 §§4.3–4.4, 8, and 11.2.
  - [ ] Format pinned upstream observation fields and process-local sequence
    semantics separately from the new durable Ishiban API.
  - [ ] Success: reference CLI envelopes remain compatible; callers cannot
    mistake the new durable cursor or enriched projection for unchanged upstream
    v1 semantics.

- [ ] 2.4.5. Connect Falcon's SSE adapter to the native observation API.

  - [ ] Requires 2.4.3. See RFC 0001 §§1, 4, and 11.
  - [ ] Translate the native epoch/sequence to SSE event IDs and implement
    reconnect/resnapshot handling without adding another replica owner.
  - [ ] Success: Ishiban reconnects across adapter and daemon restarts and
    renders the same projection as a fresh snapshot; no UI rewrite or
    source-side execution write is required.

### 2.5. Exit the observation spike with parity and failure evidence

Does the complete read path remain useful during load and recovery? Acceptance
here unlocks hosting and identifies any remaining codec or projection
limitation. See RFC 0001 §§10–12.

- [ ] 2.5.1. Compare an independent shadow observer with the reference source.
  - [ ] Requires steps 2.1–2.4. See RFC 0001 §§4, 10, and 11.
  - [ ] Success: fixture and authorized live shadow comparisons match projected
    facts using separate local state; tests show no source document edits,
    unread acknowledgements, permission answers, agent launches, or machine-host
    advertisement.
- [ ] 2.5.2. Run the observation overload and restart acceptance suite.
  - [ ] Requires 2.5.1. See RFC 0001 §§3–6, 9, 10, and 13.7.
  - [ ] Exercise 200 repository groups and 10,000 idle sessions; block a history
    scan/import while requiring unrelated reads and ingestion to progress.
    Separately restart only a worker, retain the open store, and inject version
    skew, fragmented frames, retry wakeups/restarts, and full ordinary
    admission.
  - [ ] Success: each fault asserts its promised observable outcome and rejects
    a plausible incorrect implementation; combined slow-disk/REST/import load
    remains bounded. Recovery invents no terminal events. Publish measured
    results and failed targets before opening phase 3.

## 3. Second spike: one ACP agent with native Loro sync

Idea: if a single supervised ACP agent can run, persist incremental output, and
converge with an existing Lody peer while all expensive work remains outside
liveness and transport execution, the architecture supports hosting without
recreating the TypeScript daemon's failure mechanisms.

This slice runs in a disposable, explicitly supported workspace and uses a
custom or already installed ACP executable. It does not depend on rebuilding
every provider downloader, MCP integration, or orchestration feature.

### 3.1. Make local writes durable before publishing them

Can the host distinguish durable acceptance from delivery and remote receipt?
The answer defines crash recovery and prevents an in-memory queue from becoming
the only copy of agent output. See RFC 0001 §§5 and 7.

- [ ] 3.1.1. Implement atomic local changes and the durable outbound queue.

  - [ ] Requires 2.5.2. See RFC 0001 §§5, 7, 9, 13.1, and 13.2, and
    `contracts/storage.sql`.
  - [ ] Persist domain changes, exact encoded updates, and stable send
    identities before transmission; reserve completion/recovery growth before
    accepting work. The storage owner commits even if the caller disconnects.
  - [ ] Success: explicit commit precedes acceptance; crash points preserve each
    accepted obligation. Filling ordinary admission still permits existing work
    to complete or cancel; real disk exhaustion returns storage-blocked without
    false acknowledgement or pruning unreconciled records.

- [ ] 3.1.2. Implement outbound Streams identity and acknowledgement rules.

  - [ ] Requires 3.1.1 and 2.2.4. See RFC 0001 §§5 and 12.
  - [ ] Preserve required producer epoch/sequence across restart and distinguish
    request completion, server acceptance, and peer evidence.
  - [ ] Success: lost acknowledgements and duplicate sends behave within
    verified protocol guarantees; the adapter never invents exactly-once
    execution or server persistence guarantees.

- [ ] 3.1.3. Implement reconnect reconciliation and retained local backlog.

  - [ ] Requires 3.1.2 and 2.2.6. See RFC 0001 §§5, 9, 10, and 13.3.
  - [ ] Reconcile on each connection and bounded jittered progress check;
    preserve attempt identity and required retry floors through wakeups,
    injected configuration-generation changes, and restart. Bootstrap retains
    unsent work and immutable producer tuples. Real reload integration belongs
    to 4.2.4 and 4.4.2.
  - [ ] Success: remote/local-only edits, lost responses, cursor expiry, and
    delayed dependencies converge; retry timing and reported eligibility agree.
    Poisoned records stay visible, and recovery cannot replay uncertain prompts.

- [ ] 3.1.4. Qualify murder authoring for the selected Flock catalogue format.

  - [ ] Requires 1.1.3 and 3.1.2.
  - [ ] See RFC 0001 §§2.3, 5.4, and 7.6.
  - [ ] Integrate the qualified native writer with durable producer/peer
    identity and supported mutation and deletion operations.
  - [ ] Success: the reference reader accepts authored updates, clocks, and
    tombstones across retry and restart; an unavailable native writer keeps
    hosting gated.

- [ ] 3.1.5. Publish machine registration and enforce its execution ownership.

  - [ ] Requires 3.1.4 and 3.1.2.
  - [ ] See RFC 0001 §§6, 7.6, and 9.4.
  - [ ] Use verified service contracts for registration and capabilities, with
    local ownership locks and generation fencing; keep periodic presence outside
    catalogue writes.
  - [ ] Success: an existing peer sees the correct owner and capabilities, while
    duplicate local owners and copied live writer state cannot claim supported
    simultaneous execution.

- [ ] 3.1.6. Publish discoverable session lifecycle metadata.

  - [ ] Requires 3.1.5.
  - [ ] See RFC 0001 §§4.1, 5.4, and 7.6.
  - [ ] Write SessionMeta, agent configuration references, activation pointers,
    and the supported history backend through the durable catalogue owner.
  - [ ] Success: an existing client discovers the hosted session and correct
    history/owner; retries preserve identities, and incomplete publication
    remains an explicit recoverable state.

### 3.2. Own the agent process and its protocol capacity

Can a noisy, hung, or exited agent leave the host responsive and its outcome
unambiguous? This step applies the SDK gate to a real child process. See RFC
0001 §§3, 7, and 9.

- [ ] 3.2.1. Implement systemd-supervised arun and agent execution.

  - [ ] Requires 1.3.1, 2.5.2, and 2.2.6.
  - [ ] See RFC 0001 §§7, 9, 11, 13.3, and 14, and the
    [Linux architecture][architecture] §§4–7.
  - [ ] Qualify the user manager, cgroup v2 controllers, inherited limits, and
    lingering policy. Use independent arun services with no daemon stop
    dependency and no automatic runner restart.
  - [ ] Freeze executable/arguments/cwd/environment, reserve host/workspace/run
    resources, persist launch intent, and reconcile ambiguous manager replies
    by the same run ID. Drain stdout and stderr independently.
  - [ ] Success: every incarnation reconciles durable ownership before
    readiness; failed/short-lived runs retain backoff. Hung initialization,
    stderr flood, and retained descendants end explicitly; abort requests
    require join/reap confirmation, and unresolved exit cannot authorize
    ownership transfer.

- [ ] 3.2.2. Integrate Magitek frame limits and downstream admission credits.

  - [ ] Requires 3.2.1, 3.2.4, and 1.3.1. See RFC 0001 §§7, 9, 10, 13.4, and 14.
  - [ ] Use Magitek's qualified implementation; enforce limits before allocation
    and through retained leases and downstream queues. Keep callbacks bounded,
    retain decoder state across cancellable reads, and poison abandoned logical
    frames even when abandonment falls between complete arun chunks.
  - [ ] Success: fragmented frames across timer/control events retain every
    byte; valid/oversized floods stay bounded and retain cancellation capacity.
    Slow storage backpressures or explicitly fails the affected producer without
    waiting for a response on the same ordered dispatcher.

- [ ] 3.2.3. Persist launch intent and the prompt submission boundary.

  - [ ] Requires 3.1.1 and 3.2.2. See RFC 0001 §§5, 7, 10, and 13.3–13.4.
  - [ ] Freeze prompt/config/operation identities and journal dispatch before
    transport; fence late callbacks by session, operation lifetime, and owner
    generation. Exercise the small state machine with generated transitions.
  - [ ] Success: crashes expose unsent versus potentially submitted state;
    recovery reconciles completion evidence before reclaiming claims. A reused
    visible session ID cannot absorb an old result, and a reclaimed claim never
    authorizes prompt replay without idempotency or resolving evidence.

- [ ] 3.2.4. Implement bounded arun replay and fenced reattachment.

  - [ ] Requires 3.2.1 and 3.1.1. See the
    [runner transport contract](contracts/arun-transport.md).
  - [ ] Implement contiguous stdout replay, durable inbox acknowledgements,
    stdin sequence/digest receipts, attachment fencing, finite detached/stall
    policy, and offline import of completed-run spools and write receipts.
  - [ ] Success: daemon/socket loss across partial frames loses no committed
    prefix; stdout saturation never silently truncates protocol bytes. Retained
    spools keep disk reservations after execution ends; lost write receipts
    cannot cause duplicate pipe writes or imply semantic acceptance.

- [ ] 3.2.5. Qualify ACP continuation after daemon replacement.

  - [ ] Requires 3.2.2–3.2.4. See the [Linux architecture][architecture] §7
    and the Magitek restoration extension required there.
  - [ ] Define versioned negotiation/session/pending-request descriptors,
    request-ID allocation, host-effect/permission receipts, raw and applied
    cursors, and replay that performs no repeated external effects.
  - [ ] Success: crash-window witnesses either restore the original ACP
    conversation safely or fence mutations with `recovery_required` and an
    explicit uncertain outcome. Capability advertisement permits transparent
    continuation only after the restoration path passes; a tested fallback
    alone cannot advertise it.

### 3.3. Run a complete turn and publish incremental history

Can the hosted agent and existing Lody peers agree on a turn's durable state?
This step proves the smallest end-to-end hosting capability. See RFC 0001 §§5
and 7.

- [ ] 3.3.1. Wire ACP initialization and one-session prompt control.

  - [ ] Requires 3.2.3, 3.1.6, and 1.4.2.
  - [ ] See RFC 0001 §§7.1, 7.4, 8, and 13.5.
  - [ ] Negotiate ACP and local IPC capabilities separately; create/load only
    supported sessions and route CLI admission to the durable command owner.
  - [ ] Success: a test agent follows initialization/session/prompt transitions;
    unsupported operations fail before admission, and advertised capabilities
    match installed handlers. Host terminal capability stays unadvertised
    until a run-bound executor proves aggregate resource, lifetime, and recovery
    semantics; it cannot spawn into the daemon control cgroup. Local version
    skew cannot masquerade as a lost accepted prompt.

- [ ] 3.3.2. Route permission decisions through generation-fenced response
  owners.

  - [ ] Requires 3.3.1.
  - [ ] See RFC 0001 §§7.2–7.4 and 10.2.
  - [ ] Persist the exact action, request identity, deadline, and execution
    generation; return bounded routing work from ordered SDK callbacks.
  - [ ] Success: denied and expired requests remain denied; delayed answers
    cannot authorize a replacement execution, and a waiting decision cannot
    deadlock protocol progress.

- [ ] 3.3.3. Implement the selected ACP filesystem callbacks on admitted
  workers.

  - [ ] Requires 3.3.1 and 3.3.2.
  - [ ] See RFC 0001 §§3, 7.1–7.3, and 9.
  - [ ] Enforce the selected path and operation authority, bounded
    request/result size, and independent asynchronous response ownership.
  - [ ] Success: permitted operations work through the supervised session,
    prohibited paths remain inaccessible, and slow filesystem work cannot occupy
    ordered dispatch or liveness.

- [ ] 3.3.4. Materialize ACP updates through incremental history changes.

  - [ ] Requires 3.3.3 and 3.1.1. See RFC 0001 §§3, 5, 7, and 10.
  - [ ] Route bounded updates to the native owner; index affected turns and tool
    calls without serializing the whole conversation per chunk.
  - [ ] Success: increasing unrelated transcript size does not increase normal
    chunk-update work beyond the agreed target; output and terminal markers
    survive restart in the reference reader.

- [ ] 3.3.5. Verify bidirectional state compatibility with a Lody peer.

  - [ ] Requires 3.3.4, 3.1.3, and 3.1.6.
  - [ ] See RFC 0001 §§2, 5, 7, and 10.
  - [ ] Exercise concurrent supported edits and remote history reads through the
    deployed protocol profile in the disposable workspace.
  - [ ] Success: both peers converge on supported facts and identify unsupported
    fields explicitly; remote edits do not bypass host authorization or become
    duplicate execution requests.

### 3.4. Keep heartbeat publication independent and truthful

Can the host publish fresh presence while replication or REST stalls, and can
it report degraded capabilities without claiming all work is healthy? See RFC
0001 §§3, 6, and 9.

- [ ] 3.4.1. Implement the dedicated liveness runtime and publication path.

  - [ ] Requires 3.2.2, 2.2.5, and 3.1.5. See RFC 0001 §§3 and 6.
  - [ ] Reserve networking/admission capacity, coalesce latest unsent values
    before protocol sequencing, retain required removals, and stamp fresh
    timestamps at publication without illegal frame reordering.
  - [ ] Success: high-rate session activity cannot delay machine heartbeat
    admission beyond the declared budget; no token-chunk callback emits
    presence, and missed ticks do not create a catch-up storm.

- [ ] 3.4.2. Implement capability readiness and worker-progress health.

  - [ ] Requires 3.4.1, 1.2.3, and 2.2.3.
  - [ ] See RFC 0001 §§6, 9, and 13.3.
  - [ ] Separate process liveness, publication, replica progress, storage, and
    agent admission; expose recovery/ownership gates on every incarnation.
  - [ ] Success: a replacement worker stays unready until reconciliation
    restores progress; a responsive ticker or successful spawn cannot imply
    readiness. Waiting reasons derive from the same retry/claim state as
    scheduling, and local heartbeat dispatch cannot imply remote receipt.

- [ ] 3.4.3. Isolate token refresh and network failure domains under load.

  - [ ] Requires 3.4.1 and 2.1.5. See RFC 0001 §§6, 8, and 9.
  - [ ] Keep shared refresh generation-safe while reserving transport resources
    for liveness; bound refresh and body-completion lifetimes.
  - [ ] Success: stalled REST, token expiry, cancelled waiters, and an old token
    rejection cannot starve a healthy presence path or invalidate a newer
    credential generation.

### 3.5. Exit hosting with explicit crash and cancellation outcomes

Does one hosted turn remain understandable through cancellation, process death,
and replica recovery? The result defines the fleet admission gate. See RFC 0001
§§7, 10, and 11.

- [ ] 3.5.1. Implement cancellation and terminal-outcome reconciliation.

  - [ ] Requires 3.3.5 and 3.4.2. See RFC 0001 §§7, 10, and 13.4.
  - [ ] Distinguish request cancellation, ACP cancellation, child termination,
    durable settlement, and unknown submission; the operation owner retains
    completion/event obligations after the requesting connection disappears.
  - [ ] Success: disconnecting CLI/observers leaves accepted work recoverable;
    only explicit cancellation changes agent intent. EOF, late/old-generation
    results, denied permission, and crashes produce defensible outcomes without
    blind resend or equating idle/disconnected with completed.

- [ ] 3.5.2. Recover native workers from durable state and checkpoints.

  - [ ] Requires 3.1.3, 3.3.4, and 3.4.2.
  - [ ] See RFC 0001 §§5, 9, 10, and 13.3.
  - [ ] Extend first-spike replay with atomic snapshot/pending-sidecar
    checkpoints and protected outbox identity; reconcile interrupted completion
    before releasing abandoned claims on every incarnation. Keep checkpoint work
    off control I/O.
  - [ ] Success: worker-only and whole-daemon restarts restore progress after
    import/snapshot/apply failure. Empty pending exports clear old sidecars,
    export errors retain the prior generation, and poisoned input blocks without
    a restart loop. No recovery claim resolves external delivery uncertainty.

- [ ] 3.5.3. Pass the combined one-agent fault and interoperability gate.

  - [ ] Requires 3.5.1, 3.5.2, 3.4.3, and 3.2.5. See RFC 0001 §§10–14.
  - [ ] Require a remote peer to receive fresh renewals while history/import is
    blocked; restart only a worker, disconnect an accepted command's caller, and
    complete/cancel work at full ordinary admission as separate witnesses.
  - [ ] Combine stdout flood, slow storage, stalled REST, pathological import,
    disconnect, and peer observation in one reproducible workload.
  - [ ] Restart only the daemon while the runner survives; finish an agent
    during absence; distinguish restoration from the tested recovery-required
    fallback. Explicit authorization revocation must stop affected runs rather
    than merely stopping the daemon.
  - [ ] Success: witnesses reject the corresponding false healthy outcome;
    combined latency/memory budgets hold, durable output survives, and uncertain
    prompts remain explicit. Local timer ticks alone cannot pass liveness.

## 4. Fleet hosting, practical CLI parity, and controlled migration

Idea: if bounded admission and document ownership preserve the one-agent
invariants across a representative fleet, the Rust daemon can replace a small
production subset and then expand without relying on frequent restarts to
regain memory or repair synchronization.

This phase supplies the commands needed for ordinary operation and verifies the
actual fleet workload. Capacity targets are test conditions, not a promise that
a particular host can execute that many model workloads.

### 4.1. Preserve fairness as sessions and documents multiply

Can one busy session or giant document consume another session's progress
budget? The result sets safe admission defaults and pool sizing. See RFC 0001
§§3, 5, and 9.

- [ ] 4.1.1. Add machine, workspace, and session admission accounting.

  - [ ] Requires 3.5.3. See RFC 0001 §§3, 7, 9, and 13.2.
  - [ ] Bound agents, documents, bytes, pending writes, and queued work before
    scheduling; reserve later completion/cancellation/recovery growth per scope.
  - [ ] Success: ordinary saturation delays/rejects new work with a stable
    reason; existing obligations can release resources and record disposition
    while cancellation/liveness remain admissible. Another process consuming
    physical disk produces an explicit storage-blocked capability.

- [ ] 4.1.2. Implement fair replica scheduling and bounded residency.

  - [ ] Requires 4.1.1 and 3.5.2. See RFC 0001 §§3, 5, and 9.
  - [ ] Schedule bounded units across documents in the fixed worker pool;
    checkpoint/evict only after protecting outstanding state.
  - [ ] Success: a pathological document affects only its declared worker cohort
    and shows degradation; healthy cohorts progress without adding an unbounded
    number of worker processes or threads.

- [ ] 4.1.3. Add incremental maintenance and explicit maintenance admission.

  - [ ] Requires 4.1.2. See RFC 0001 §§3, 5, and 9.
  - [ ] Bound compaction, snapshot export, SQLite checkpointing, cleanup, git
    inspection, and filesystem work separately from interactive work.
  - [ ] Success: maintenance cannot occupy liveness execution or exhaust all
    interactive credits; interruption retains a valid recoverable checkpoint and
    never advances durability evidence prematurely.

### 4.2. Deliver the CLI operations required for daily use

Can operators inspect and control supported sessions without falling back to
hidden TypeScript execution? This step establishes the core command contract
while keeping broader product parity explicit. See RFC 0001 §8.

- [ ] 4.2.1. Implement workspace, machine, project, and session reads.

  - [ ] Requires 2.4.4 and 4.1.1. See RFC 0001 §§4 and 8.
  - [ ] Provide list/show/status/history/observe with documented JSON, JSONL,
    paging, provenance, freshness, and unsupported-mode errors.
  - [ ] Success: CLI contract fixtures agree with daemon projections; paginated
    history does not materialize the complete transcript.

- [ ] 4.2.2. Implement supported session create/send/cancel commands.

  - [ ] Requires 4.2.1 and 3.5.1. See RFC 0001 §§5, 7, and 8.
  - [ ] Reuse durable intent, capability checks, frozen configuration, and
    request identity; document unsupported steering/delegation cases.
  - [ ] Success: exact retries preserve identity, changed requests cannot reuse
    an accepted identity, and disconnected outcomes remain unknown until
    evidence resolves them.

- [ ] 4.2.3. Expose status, diagnostics, auth, and effective configuration
  commands.

  - [ ] Requires 4.2.1, 3.4.2, and 1.4.2.
  - [ ] See RFC 0001 §§8, 9.3, 11, and 13.5–13.6.
  - [ ] Extend minimal peer diagnostics with readiness, queue pressure,
    recovery, retry eligibility, credential class, and configuration provenance.
  - [ ] Success: humans/JSON clients can identify the running daemon, stale
    synchronization, blocked recovery, or unsupported capabilities during an
    outage; reporting never substitutes the installed CLI's identity or exposes
    secrets.

- [ ] 4.2.4. Implement validated immutable configuration reload.

  - [ ] Requires 4.2.3, 2.1.1, and 2.2.6.
  - [ ] See RFC 0001 §§3.1, 8.3, 13.3, and 13.6.
  - [ ] Parse/validate on maintenance workers; publish one generation and
    classify restart-only/migration-only changes under the startup semantics.
  - [ ] Success: real-entry-point tests preserve the active generation on
    invalid reload, frozen turn configuration, retry floors, and admitted
    obligations. Observe mode cannot acquire new authority, and lowering limits
    cannot consume the capacity reserved for accepted work to finish.

- [ ] 4.2.5. Add controlled daemon start and stop commands.

  - [ ] Requires 4.2.3 and 3.5.1.
  - [ ] See RFC 0001 §§7.5, 9.4, and 11.
  - [ ] Route lifecycle commands through one supervisor with explicit ownership,
    bounded waits, and stable exit/error results.
  - [ ] Success: duplicate starts cannot create a second owner; failed or
    unconfirmed termination remains visible and cannot authorize replacement.

- [ ] 4.2.6. Qualify the portable CLI on Windows and the Linux host through WSL.

  - [ ] Requires 4.2.3 and 4.2.5.
  - [ ] See RFC 0001 §§1, 8, and 11.
  - [ ] Build the CLI and exercise supported invocation, output, path, and
    signal behaviour without claiming native Windows daemon parity.
  - [ ] Success: documented supported operations work in the qualified
    arrangement; native Windows hosting returns an explicit unsupported result
    until its separate gate passes.

- [ ] 4.2.7. Implement basic local project registration and worktree use.

  - [ ] Requires 4.2.2 and 4.1.3. See RFC 0001 §§7–9 and 11.
  - [ ] Preserve project identity/path authorization and route bounded
    git/worktree creation through maintenance workers before agent launch.
  - [ ] Success: reference fixtures cover register/list/use, existing and new
    worktrees, interrupted preparation, and uncommitted work; retries do not
    create duplicate contexts or delete retained project data.

- [ ] 4.2.8. Implement archive and restore with upstream retention rules.

  - [ ] Requires 4.2.2 and 4.2.7. See RFC 0001 §§4, 7–9, and 11.
  - [ ] Preserve the pinned archive/restore contract for history, identity,
    pending work, and worktree cleanup; keep archive separate from outcome.
  - [ ] Success: differential tests cover eligible/ineligible transitions,
    concurrent activity, retained history, and restore; no extra cleanup or
    fabricated terminal outcome occurs beyond the documented policy.

- [ ] 4.2.9. Implement bounded native machine RPC request and reply transport.

  - [ ] Requires 3.1.6, 3.5.1, and 4.2.2.
  - [ ] See RFC 0001 §§5, 7.6, and 8.
  - [ ] Preserve the observed stream names, ingress/reply envelopes,
    correlation, deadlines, and retained-result identity under independent
    request/reply budgets.
  - [ ] Success: reference requesters exchange compatible frames; duplicate,
    expired, and lost replies preserve correlation and bounded storage without
    authorizing a new execution.

- [ ] 4.2.10. Route authorized machine RPC methods through existing command
  owners.

  - [ ] Requires 4.2.9.
  - [ ] See RFC 0001 §§5.4, 7.4, 7.6, and 10.2.
  - [ ] Implement supported create/send, permission, and cancellation routes
    with requester identity, role propagation, capability checks, and durable
    receipts.
  - [ ] Success: existing UI/CLI peers control the supported surface, retries
    return the same accepted disposition, and arbitrary catalogue edits or late
    replies cannot bypass execution authority.

### 4.3. Operate the daemon with bounded resource and shutdown costs

Can the host maintain responsiveness while compilation or external tools
consume the machine? This step connects internal budgets to service-level
operation. See RFC 0001 §§3, 6, and 9.

- [ ] 4.3.1. Package Linux service resource and ownership controls.
  - [ ] Requires 4.1.3, 4.2.5, and 3.2.1. See RFC 0001 §§9, 11, and 14.
  - [ ] Extend the first hosting slice's systemd adapter and service policy to
    measured installation/workspace/fleet limits. Qualify CPU, memory, swap,
    I/O, task, state-directory, and child-lifecycle boundaries on the target
    host; the illustrative Linux profile is not a production measurement.
  - [ ] Success: a synthetic competing compiler load leaves reserved daemon
    capacity measurable; service restarts cannot create two owners.
- [ ] 4.3.2. Expose operational metrics and bounded diagnostic traces.
  - [ ] Requires 4.3.1. See RFC 0001 §§6, 9, and 10.
  - [ ] Report scheduler lag, queue age/bytes, replica apply/cursor progress,
    outbox age, worker restarts, and observed heartbeat stages.
  - [ ] Success: dashboards distinguish read, write, auth, storage, and host
    failures without session IDs in unbounded metric labels or
    transcript/credential payloads in logs.
- [ ] 4.3.3. Implement bounded drain and recoverable shutdown.
  - [ ] Requires 4.3.1 and 4.2.2. See RFC 0001 §§5, 7, 9, 11, and 13.3.
  - [ ] Distinguish daemon maintenance from run termination. Stop admission,
    checkpoint/settle backlog, fence controller attachments, and detach runners
    for supported maintenance. Explicit stop-all ends run service cgroups.
  - [ ] Track daemon workers through join/reap, confirm run termination where
    required, and retain independent disk reservations until actual reclaim.
  - [ ] Success: bounded shutdown records unresolved cleanup/delivery;
    requesting abortion never counts as termination. Lingering work blocks
    ownership transfer, deadlines cannot erase accepted obligations, and no
    uncertain execution becomes successful to simplify shutdown.

### 4.4. Demonstrate fleet reliability under representative load

Does the implementation satisfy its declared budgets under combined stress for
longer than the reported failure interval? The result controls rollout size
rather than serving as a promotional benchmark. See RFC 0001 §10.

- [ ] 4.4.1. Build the representative fleet and catalogue workload.

  - [ ] Requires 4.1.3 and 4.3.2. See RFC 0001 §§9 and 10.
  - [ ] Model 60 active ACP agents, 10,000 idle sessions, 200 repositories, long
    histories, tool bursts, and several concurrent consumers.
  - [ ] Success: reproducible captures report per-component CPU, RSS, disk
    growth, queue age, convergence, and latency against declared budgets;
    simulator costs are distinct from real agent costs.

- [ ] 4.4.2. Run fleet-wide fault injection and recovery assertions.

  - [ ] Requires 4.4.1, 4.3.3, and 4.2.4. See RFC 0001 §§5–10 and 13.7.
  - [ ] Combine slow/full disk, auth/network failure, cursor expiry, worker
    crash, bad import, stdout flood, and slow consumers with
    invalid/restart-only reload and reload during admitted work.
  - [ ] Cross retry eligibility with unrelated mutation, refresh, reload, and
    worker-only restart; cross ordinary saturation with completion/cancellation;
    deliver old-generation results after replacement and inject version skew.
  - [ ] Success: specific witness assertions and combined stress distinguish
    live-but-stalled owners, lost decoder state, premature retries, and false
    readiness. Healthy work progresses; accepted durable data survives and
    uncertain prompts never replay automatically.

- [ ] 4.4.3. Complete the sustained-load acceptance run.

  - [ ] Requires 4.4.2. See RFC 0001 §§9–11.
  - [ ] Run a 72-hour soak with repeated disconnect/reconnect and load cycles,
    recording heap/RSS, spool growth, and peer-observed state.
  - [ ] Success: the report demonstrates bounded post-warm-up resource trends
    and the agreed liveness/convergence targets; any unmet target prevents
    expanding the canary until its cause is understood.

### 4.5. Transfer execution ownership without losing backlog

Can production adopt and roll back the implementation without duplicate
execution or corrupting another daemon's state? This step makes replacement a
controlled operation. See RFC 0001 §11.

- [ ] 4.5.1. Repeat shadow comparison for the production cutover candidate.
  - [ ] Requires 4.4.3 and 2.5.1. See RFC 0001 §§4, 10, and 11.
  - [ ] Use independent state and read-only credentials/capabilities; compare
    session facts and explicit Ishiban correlations.
  - [ ] Success: a divergence ledger distinguishes stale evidence, unsupported
    modes, mapping gaps, and actual compatibility defects.
- [ ] 4.5.2. Execute a small canary ownership transfer.
  - [ ] Requires 4.5.1, 4.3.3, 4.2.7–4.2.10, and the 1.3.4 scope inventory.
  - [ ] See RFC 0001 §§9 and 11.
  - [ ] Drain the selected old owner, verify termination, preserve
    identities/backlog by the supported migration route, then enable Rust.
  - [ ] Gate every selected workflow on its inventory prerequisites; exclude
    explicitly deferred workflows from this canary. Resume or other advanced
    parity is required only when that scope depends on it.
  - [ ] Success: exactly one execution owner operates the selected scope; no
    live SQLite files are shared, and checkpoints prove every retained accepted
    operation's disposition before broader expansion.
- [ ] 4.5.3. Rehearse rollback and publish the core support contract.
  - [ ] Requires 4.5.2. See RFC 0001 §§1, 11, and 12.
  - [ ] Retain forward-created backlog safely, respect schema/version
    boundaries, and document restore rules for replica peer identities.
  - [ ] Success: rollback neither replays uncertain work nor discards unsent
    changes; the release lists supported commands/profiles and advertises
    only the independently proven process, byte, and ACP recovery capabilities.

## 5. Deferred compatibility after the core host is trustworthy

Idea: if the core host already meets its durability and liveness contract,
additional Lody surfaces can justify their own protocol and operational costs
without destabilizing the two initial use cases.

These tasks do not block the supported ordinary-workspace core release. They
qualify one selected adapter/profile at a time. If qualification identifies a
substantial new port, refine that work into review-sized tasks here before
promotion; a decision or test report alone cannot satisfy an implementation
gate. They become necessary before enabling the corresponding capability. An
existing deployment that needs one of them must retain the old owner for that
scope until its gate passes.

Phase 5 expresses the default priority, not a requirement to finish phase 4
before supporting the first selected workspace. If that workspace uses
protected content, promote step 5.1 before task 2.2.4. If it uses Roost,
promote task 5.2.1 before task 2.2.4 and task 5.2.2 before enabling Roost
writes. These gates depend on foundations and reference fixtures so their
promotion does not create a dependency cycle. Execution integration still
requires the normal phase 3 acceptance tests.

Likewise, promote a deferred workflow capability before task 4.5.2 when the
selected production inventory requires it. Such tasks depend on the core
acceptance gate, not completion of the canary they would otherwise block.
Explicitly excluded workflows remain with their existing owner.

### 5.1. Evaluate encrypted workspace support without weakening it

Can a native host reproduce the encrypted authorization and custody model? This
determines whether encrypted workspaces can enter the support matrix. See RFC
0001 §§2, 8, and 12.

- [ ] 5.1.1. Specify and implement the required native E2EE protocols.
  - [ ] Requires 1.1.1, 1.2.1, and 1.3.3.
  - [ ] See RFC 0001 §§2, 5, 8, and 12.
  - [ ] Success: reviewed key, pairing, envelope, identity, and execution
    authorization contracts match reference vectors; there is no plaintext
    fallback or downgrade on missing native support.
- [ ] 5.1.2. Prove encrypted revocation, recovery, and execution boundaries.
  - [ ] Requires 5.1.1. See RFC 0001 §§7, 10, and 11.
  - [ ] Success: revoked, stale, mismatched, and restored credentials cannot
    authorize new execution; loss/recovery tests preserve the existing
    distinction between local editing and remote authority.

### 5.2. Evaluate Roost history independently of Loro history

Can the alternate immutable history model fit the same observation and hosting
contracts? This determines whether its adapter merits support. See RFC 0001
§§2, 5, and 12.

- [ ] 5.2.1. Implement a versioned Roost read adapter and parity corpus.
  - [ ] Requires 1.1.1, 1.2.3, and 1.3.3.
  - [ ] See RFC 0001 §§2, 4, 5, and 12.
  - [ ] Success: native reads preserve immutable record semantics and match
    reference scalar/history fixtures; unsupported records remain visible
    instead of being interpreted as Loro documents.
- [ ] 5.2.2. Decide and prove the Roost hosting/migration contract.
  - [ ] Requires 5.2.1. See RFC 0001 §§5, 7, 10, and 11.
  - [ ] Success: an ADR defines supported writes and ownership transfer;
    differential and crash tests pass before any existing history backend
    changes or writable capability is advertised.

### 5.3. Expand desktop and native-platform interoperability

Can additional clients and hosts reuse the same owners without creating a
second data plane accidentally? This step gates desktop and native Windows
daemon support. See RFC 0001 §§1, 2, and 11.

- [ ] 5.3.1. Implement the existing local Loro data-plane protocol.
  - [ ] Requires 4.4.3. See RFC 0001 §§2, 5, 6, and 12.
  - [ ] Success: protocol-v7 authentication, peer frontiers, chunking,
    origin-separated presence, and backpressure pass reference fixtures; cloud
    unavailability does not falsify local-room health.
- [ ] 5.3.2. Package native Windows hosting and further supported targets.
  - [ ] Requires 5.3.1, 4.3.3, and 4.2.6. See RFC 0001 §§1, 3, 9, and 11.
  - [ ] Success: named-pipe security, child job ownership, paths, filesystem
    replacement, and restart tests meet the same core contract; unsupported
    platform behaviour never falls through to unsafe defaults.

### 5.4. Add managed providers and MCP behind explicit capabilities

Can provider setup and agent tools preserve the same ownership and admission
rules as custom ACP executables? These capabilities must pass independently
before entering the supported command surface. See RFC 0001 §§7, 8, and 12.

- [ ] 5.4.1. Add verified provider runtime acquisition and configuration.
  - [ ] Requires 4.4.3 and any applicable 5.1 or 5.2 tasks.
  - [ ] See RFC 0001 §§1, 7, 8, and 12.
  - [ ] Success: one provider adapter at a time verifies artefacts and
    configuration provenance, keeps download/unpack work outside I/O execution,
    and cannot replace an in-use runtime without coordination.
- [ ] 5.4.2. Add daemon-hosted MCP access for supported workspace commands.
  - [ ] Requires 4.2.10 and 4.4.3. See RFC 0001 §§7, 8, and 12.
  - [ ] Success: MCP borrows existing daemon owners, derives the correct
    requester identity, applies bounded request admission, and opens no
    independent catalogue/presence replica per tool invocation.

### 5.5. Extend durable scheduling and delegation deliberately

Can background triggers and agent-to-agent work preserve accepted identities
through ambiguous delivery? This step adds behaviour beyond a directly
requested single turn. See RFC 0001 §§5, 7, and 12.

- [ ] 5.5.1. Add durable schedule dispatch and recovery.
  - [ ] Requires 4.4.3 and 5.4.2. See RFC 0001 §§5, 7, and 12.
  - [ ] Success: each admitted occurrence has a stable identity and
    authorization evidence; crash/retry cannot duplicate an uncertain execution
    or silently reinterpret a changed schedule definition.
- [ ] 5.5.2. Add operation/inbox delegation and continuation parity.
  - [ ] Requires 5.4.2 and applicable 5.1 tasks.
  - [ ] See RFC 0001 §§5, 7, 10, and 12.
  - [ ] Success: reference state-machine cases preserve frozen inputs, causal
    depth, stop barriers, reply provenance, and permanent unknown submission;
    cancellation and late receipts do not create extra turns.

### 5.6. Add managed upgrades after ownership transfer is proven

Can a release switch retain the established one-owner and backlog contract?
This step generalizes the manual rollout while retaining negotiated runner
versions and explicit protocol-restoration gates. See RFC 0001 §§9, 11, 12, and
14, and the [Linux architecture][architecture] §7.

- [ ] 5.6.1. Add managed upgrade and further lifecycle compatibility.
  - [ ] Requires 4.5.3. Native Windows updates also require 5.3.2.
  - [ ] See RFC 0001 §§9, 11, and 12.
  - [ ] Success: verified releases, durable update identity, drain, confirmed
    old-owner exit, and bounded rollback pass fault tests; accepted updates
    survive acknowledgement loss without duplicate switch.

### 5.7. Qualify an alternative store against the same durability contract

Does another local engine improve measured tail latency or resource use while
preserving accepted-work recovery? SQLite remains the first-spike baseline.
This optional work may run after hosting proves the shared workload; neither
initial spike nor core rollout depends on it. See RFC 0001 §§5, 9, and 13.1.

- [ ] 5.7.1. Implement a bounded Turso adapter for the domain storage
  operations.
  - [ ] Requires 3.5.3. See RFC 0001 §13.1 and `contracts/storage.sql`.
  - [ ] Qualify a pinned engine release against key/constraint, transaction,
    statement-lifetime, and durability semantics; preserve explicit commit
    acknowledgement and the domain's atomic transition boundaries.
  - [ ] Success: the adapter passes the same inbox, command, outbox, projection,
    and checkpoint recovery contract under FULL durability. Unsupported schema
    features fail visibly; native async I/O does not remove execution admission
    or progress-capacity limits.
- [ ] 5.7.2. Compare storage engines and record the selection decision.
  - [ ] Requires 5.7.1 and 4.4.1. See RFC 0001 §§9–10 and 13.1.
  - [ ] Compare both engines with the same bounded single-writer workload, then
    bounded independent Turso transactions where per-room ordering and atomicity
    permit them. Exercise disk-full, cancellation, crash, replay, and
    checkpoints.
  - [ ] Success: published commit/tail latency, throughput, CPU, memory, and
    disk results separate engine substitution from scheduler changes. An ADR
    selects a change only if recovery passes and the daemon workload materially
    benefits; qualification creates no automatic migration or performance claim.

[architecture]: youxia-design.md
[design]: rfcs/rfc-0001-native-rust-cli-and-daemon.md
[lessons]: lessons-on-daemon-design-and-hot-path-preservation.md
[roadmap-conventions]: https://github.com/leynos/df12-documentation-skills/blob/4a28c8953d3ccc2b5369b46cf042b53257d418de/skills/roadmap-doc/references/conventions.md
[roadmap-skill]: https://github.com/leynos/df12-documentation-skills/blob/4a28c8953d3ccc2b5369b46cf042b53257d418de/skills/roadmap-doc/SKILL.md
