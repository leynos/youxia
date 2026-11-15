# Lessons on daemon design and hot-path preservation

## 1. Purpose and evidence

Comenq's implementation history exposes failure modes that Youxia's Rust
command-line interface (CLI) and daemon must address explicitly. Moving work to
another thread, restarting a worker, or maintaining an open socket can leave
the promised capability stalled. The useful contract concerns progress through
the whole dependency chain.

This document records evidence inspected on 2026-11-15 against Comenq commit
`19665d11fef9768fa294da6a7dcc5f30b789bc9a`, together with linked review
discussions and the deployment report.[^1] It supplies rationale for the
proposed requirements in RFC 0001 §13 and their delivery gates in the roadmap.
It does not establish that Youxia implements those requirements.

| Evidence                                  | Status at inspection         | Interpretation                                                                                            |
| ----------------------------------------- | ---------------------------- | --------------------------------------------------------------------------------------------------------- |
| Queue rewrite, PR #149                    | Merged                       | Review found contention, recovery, and retry defects during implementation.[^2]                           |
| Streaming `await`, PR #228                | Merged                       | Review and regression fixtures establish the intended lock and lifetime contracts.[^3]                    |
| Version skew, issue #242 and PR #243      | Report closed; repair merged | A deployment exposed misleading diagnostics; the repair classifies errors without adding negotiation.[^4] |
| Environment injection, PR #251            | Merged                       | Review exposed behaviour changes at configuration and operating-system boundaries.[^5]                    |
| Domain extraction, issue #192 and PR #250 | Open; PR unmerged            | The proposed extraction informs a design direction, not a capability established on main.[^6]             |

_Table 1: Evidence classes and their limits._

The source inspection confirms the described code and test assertions. No
Comenq test suite or Youxia runtime benchmark accompanies this document.
Reported validation in an upstream review remains attributed to that review.
Requirements below are proposals for Youxia, not claims about current
behaviour. The full architectural proposal remains authoritative for scope:

- [RFC 0001](rfcs/rfc-0001-native-rust-cli-and-daemon.md).
- [Development roadmap](roadmap.md).

## 2. Isolate contention as well as execution

Comenq initially called synchronous filesystem operations and whole-directory
deserialization from async methods while holding its queue mutex. Review
required moving the blocking work away from Tokio's async executor and using
direct entry lookups for single-identifier operations.[^7]

The later `await` implementation exposed a second boundary. An unknown
identifier could scan the whole history while retaining the mutex needed by
claims, completions, and queue commands. Running the scan on a blocking thread
left this dependency intact. The repair captures pending state and a
generation, releases the lock, scans history, then rechecks state and
generation. Its regression test blocks the history lookup and requires an
enqueue and completion to finish before releasing it.[^8]

Youxia should prohibit bulk history reads, Loro exports, checkpoint
preparation, and diagnostics from retaining a lock, actor turn, storage
transaction, or admission credit needed by a control operation. A dedicated
runtime cannot deliver its latency contract while it waits for one of those
resources.

An expensive read should use bounded immutable inputs, a stable snapshot, or
generation validation. Generation validation also needs a retry budget:
continuous mutation must not restart an expensive calculation indefinitely.
When the budget expires, the read should yield an explicit retryable outcome or
move to an admitted snapshot path.

Admission must precede task creation and blocking-work submission. At the
inspected commit, Comenq spawns a task for each accepted connection; its
storage wrapper submits blocking work that then acquires the shared mutex. The
dedicated `await` limit does not constitute a general bound on queued
connections or storage submissions.[^9] Youxia needs explicit count and byte
limits at those ownership boundaries, including work waiting for execution.

The decisive test should hold bulk work behind a controllable barrier and
require observable control progress before releasing it. For presence, the
observer must see a fresh remote publication. A timer firing inside the
liveness runtime does not prove that publication escaped a shared bottleneck.

## 3. Recover on every owner incarnation

A Comenq worker could durably claim an entry, fail while completing or
releasing it, and restart against the same open store. Claim recovery happened
only when the store opened. The replacement worker therefore found no
selectable work, while `list` continued to display plausible estimated times of
arrival (ETAs). The fix runs recovery at every worker start and reconciles an
interrupted completion before reclaiming abandoned claims.[^10]

Youxia should give every owner an incarnation and a recovery entry point. A
replacement must fence the previous generation, reconcile durable obligations,
reconstruct owned state, and publish capability readiness only when recovery
succeeds. An outstanding operation from the old owner must not change the new
owner's state merely because both refer to the same session.

These recovery paths need separate tests because they preserve different
surrounding state:

| Replacement boundary                | State that recovery must reconcile                                                    |
| ----------------------------------- | ------------------------------------------------------------------------------------- |
| Async task within a live daemon     | Claims, subscriptions, retry state, and callbacks against an already-open store       |
| Native replica process              | Document ownership, checkpoint, retained input, and pending causal operations         |
| Agent Client Protocol (ACP) process | Execution disposition, permissions, outstanding requests, and uncertain dispatch      |
| Entire daemon                       | Durable ownership, accepted commands, incoming journal, outbox, and observation state |
| Restored database                   | Journal identity, producer counters, ownership exclusion, and stale cursors           |

_Table 2: Distinct recovery entry points._

The observation model should distinguish a process restart from restored
capability. A replacement process can exist while recovery remains blocked by
storage or unavailable source data. Report that state and its evidence rather
than publishing healthy execution solely because supervision restarted a task.

### 3.1. Preserve external-effect uncertainty

Comenq's completion record repairs interrupted local cleanup after a successful
post. The worker receives the remote response before recording completion, so a
crash in that interval still leaves a remote effect without durable local
confirmation.[^11] Local claim recovery cannot prove that the remote action
never happened.

For ACP prompts, retain `delivery_uncertain` when the daemon cannot establish
whether dispatch took effect. Recovery may resolve that state through protocol
idempotency or independent evidence; reclaiming ownership alone must not
authorize another prompt submission. Outbox retries must retain the producer
identity and exact bytes required by the publication protocol.

### 3.2. Confirm termination before transferring authority

Comenq's inspected supervisor requests task abortion after its shutdown grace
period and leaves the branch without subsequently awaiting the handle. Its
listener also drops the spawned connection handles.[^9][^12] These are source
observations, not evidence of a reported shutdown incident.

Youxia needs a stronger ownership-transfer contract for ACP children and native
replica processes. Track task and process handles, stop admission, request
shutdown, apply bounded escalation, then join or reap the old owner. If
termination cannot be confirmed, retain an unresolved ownership state unless an
independently enforced fence prevents the old owner's effects. Requesting
cancellation is not confirmation of termination.

## 4. Wakeups must preserve retry policy

Comenq's review sequence exposed three different promises. An initial retry
wait ignored queue changes and delayed their effect. A repair made changes
interrupt the wait, but then unrelated mutations could trigger another post
before the cooldown expired. Retaining an in-memory deadline fixed that
interaction.[^13] A later review found that restart lost the deadline and the
displayed ETA came from different state. The merged repair records the failed
attempt before releasing its claim and derives scheduling from the persisted
activity record.[^14]

Youxia should model four separate facts:

- A wakeup says that relevant state may have changed.
- Eligibility says that policy permits an operation now.
- Attempt identity says whether this is a retry or a different operation.
- Reported state explains why progress is waiting.

A refreshed credential, new subscriber, configuration reload, or unrelated
session command must not erase a retry floor. Persist policy state when its
contract requires the delay to survive replacement or restart, especially a
server-directed delay. Reconstruct monotonic deadlines under an explicit
clock-discontinuity policy; an in-process `Instant` cannot serve as a durable
timestamp.

Comenq also recreated its exponential-backoff iterator after each failure,
which repeatedly selected the first delay. The inspected supervisor retains the
iterator across short failed runs and resets it after a stable run.[^12] Youxia
should define when successful operation resets failure history and test
persistent failure across multiple replacements.

Retry tests should combine failures with mutation, refresh, reload, and
restart. Assert the actual attempts and their eligibility, alongside the
reported waiting reason. A test that only checks a calculated delay can miss a
different path that bypasses it.

## 5. Give cancellation and results enduring owners

Comenq races frame reading against countdown updates. Its current client pins
one frame-reading future and keeps polling that future across timer ticks. The
regression test sends a partial frame, advances through a countdown tick, and
then supplies the remainder. Recreating this reader would lose the prefix held
in the cancelled future's local buffer.[^15]

Youxia should audit each relevant `select!` boundary in ACP framing, Streams
and Server-Sent Events (SSE) decoding, local observation, and worker
inter-process communication (IPC). For every branch, identify which owner
retains partially consumed bytes and protocol state when polling stops. Keep
that state in an enduring decoder or retain a future whose cancellation
behaviour the adapter has established. Test timer, shutdown, reconnect, and
control events around fragmented input.

The same ownership rule applies after a durable operation begins. Comenq
publishes its state-generation change inside the blocking mutation boundary,
even if the caller has dropped its awaiting future.[^9] In Youxia, the accepted
operation owner must complete durable bookkeeping and observation-journal
publication independently of the requesting connection. An observer disconnect
releases a subscription. Cancelling an accepted command requires its own
operation and recorded disposition.

### 5.1. Distinguish identifiers from operation lifetimes

Comenq's `AwaitToken` binds an existing wait to an entry incarnation and
history boundary. A fresh lookup by reusable identifier has a different
contract. A review finding that conflated these cases was withdrawn after
inspection; it should not be cited as an unresolved lifetime defect.[^16]

Youxia should fence permission replies, prompt results, child-exit reports,
refresh results, and projection results with the relevant incarnation or
generation. For shared refresh work, cancelling one waiter must not cancel
other consumers' operation. For a delayed permission reply, the session ID
alone must not authorize a replacement request.

## 6. Reserve capacity for accepted work to finish

Comenq accounts for expected entry growth when it admits work, including later
claim, ordering, and incarnation changes. The retry-floor review rejected
widening a field outside that reserved mutation headroom because it would
violate the byte-budget invariant.[^14][^17]

Youxia's proposed admission accounting should cover the required future
transitions of accepted work: completion, cancellation, acknowledgement,
ownership changes, and recovery. Include observation records, database
write-ahead log (WAL) growth, and temporary checkpoint installation space.
Define bounded reservations per transition or another demonstrated means of
preserving progress; an undocumented spare-capacity margin is insufficient.

At the configured ordinary-admission limit, existing work must still be able to
record its disposition and release resources. Completion must not require a
fresh ordinary admission credit that only completion itself can free. The
capacity test should fill the real admission path, then complete and cancel
already-accepted operations through their production owners.

Configured limits and physical disk exhaustion are separate faults. Another
process can consume reserved filesystem space. An actual `ENOSPC` must produce
an explicit storage-blocked capability without false acknowledgement or
deletion of unreconciled obligations. Admission accounting does not replace
crash-recovery and disk-failure tests.

These requirements apply to both SQLite and Turso. The Comenq evidence concerns
application ownership and recovery, so it does not establish an engine-specific
performance benefit. RFC 0001 §13.1 records the initial storage choice and the
qualification boundary for alternatives.

## 7. Negotiate capabilities before the first observation stream

Comenq issue #242 reports a newer CLI communicating with an older running
daemon installed at another path. Ordinary commands worked, but `await`
returned a connection-loss error for queued, completed, and nonexistent
identifiers. The merged repair separates legacy rejection, absent initial
reply, stream loss, and an explicit daemon error. It does not add a
handshake.[^4]

Youxia should establish protocol compatibility before opening an observation
stream or admitting a command. The handshake should advertise the information
needed to interpret the peer:

| Handshake field                      | Purpose                                              |
| ------------------------------------ | ---------------------------------------------------- |
| Supported protocol range             | Establish compatible decoding and request envelopes  |
| Command and event capabilities       | Reject unsupported operations before side effects    |
| Daemon build identity                | Diagnose the software actually running               |
| Instance and generation              | Detect replacement of the observed daemon            |
| Relevant limits and cursor semantics | Establish framing, delivery, and replay expectations |

_Table 3: Proposed local IPC negotiation information._

Protocol and capability compatibility should govern admission. Build versions
support diagnosis. Minimal status output should identify the running daemon
and, where available, its executable or service identity; printing only the
newly installed CLI version would leave the reported failure unexplained.

An unrecognized or absent handshake must yield a precise compatibility error.
The client must not probe support by submitting an operation with side effects.
Test a new CLI against an intentionally older peer, including a peer that
accepts the connection but cannot decode the new request. This gate belongs in
the first Ishiban slice, before the richer fleet-management CLI.

## 8. Establish domain boundaries before parallel implementation

Comenq issue #192 records the cost of coupling queue rules to persistence,
configuration, transport, and runtime concerns. The still-open PR #250 proposes
a domain service with repository, clock, and sampling ports. Its adapter
constructs the service inside the existing serialized operation, preserving
atomic read-modify-write behaviour.[^6]

Youxia should define directly testable command-admission, delivery-state,
permission, and freshness rules before separate agents implement the adapters.
Check the dependency boundary mechanically: domain policy should not depend on
sockets, a database driver, Loro, or the async runtime. Adapters translate
protocol and storage representations; storage owners execute guarded
transitions atomically.

Classify operations by effects. Claiming work is a command even when its name
resembles a query. A repository interface must not split an atomic transition
into independently locked reads and writes. Introduce only the ports needed for
identified external effects and test seams; a generic application framework
does not follow from this lesson.

## 9. Treat configuration semantics as a public contract

Comenq's `ortho_config` migration retained its existing provider composition
after source inspection exposed two tempting regressions. A convenience error
conversion would describe file or environment failures as CLI merge failures. A
new environment provider would turn an invalid comma-separated token-file value
into a working token pool. The migration retrospective records both choices and
their behavioural evidence.[^18]

The subsequent injection work found that exact-uppercase lookup changed
case-insensitive override behaviour, a Unicode-only abstraction lost a native
socket path, and environment enumeration could panic because of an unrelated
non-Unicode variable. PR #251 added narrow operating-system-aware ports and
production-entry-point tests, including a real CLI connecting to a socket whose
path is not valid UTF-8.[^5]

Youxia should specify the following before implementing configuration:

- Source precedence, including an explicit value equal to the built-in default.
- Missing explicit files versus unsuccessful optional discovery.
- Empty values, list syntax, and environment-name case policy.
- Native path representation and invalid textual-value handling.
- Secret resolution and repository configuration's restricted authority.
- Reloadable settings, restart-only settings, and immutable generations.

Injection must preserve the intended value domain. Text-only providers cannot
represent every operating-system path. Production composition should supply the
chosen native-path and environment ports, while tests inject controlled values.
A provider unit test does not establish that the executable uses that provider:
test the actual CLI and daemon entry points with controlled child environments
and distinguish configuration errors from unrelated startup failures.

## 10. Require tests that fail for the intended reason

Comenq's retrospective records a precedence test whose expected value matched
the default, a startup test that could pass on unrelated failures, and proposed
mutation checks described before execution. The repairs used distinguishing
inputs, asserted identifying diagnostics, and recorded executed checks.[^18]
The inspected startup contract tests now check the specific token-error message
as well as process status and output channels.[^19]

For each Youxia reliability promise, identify a plausible incorrect
implementation and a small test that rejects it. Use controllable barriers,
fake clocks, and fault injection where practical. Assertions should concern the
promised effect at its owner boundary.

| Proposed contract                     | Discriminating witness                                                                 |
| ------------------------------------- | -------------------------------------------------------------------------------------- |
| Bulk work preserves liveness          | Block a history/import operation and require a remote peer to receive fresh presence   |
| Worker replacement restores progress  | Restart only the worker, retaining the daemon and already-open store                   |
| Retry policy survives activity        | Mutate unrelated state and refresh credentials before retry eligibility                |
| Retry policy survives restart         | Replace the responsible owner before its durable retry floor expires                   |
| Framing survives control events       | Split a frame across timer ticks and cancellation-related events                       |
| Accepted work outlives observers      | Disconnect the observer, then verify durable completion and replay                     |
| Old results cannot affect new work    | Deliver an old-generation permission or result after replacement                       |
| Capacity permits required transitions | Fill ordinary admission, then complete or cancel existing work                         |
| Version skew is diagnosable           | Connect a new CLI to an older protocol implementation                                  |
| Configuration reaches production      | Exercise the real executable with controlled sources and native paths                  |
| Shutdown transfers authority safely   | Stall the old owner and verify that replacement cannot claim its authority prematurely |

_Table 4: Small witnesses to complement integrated fault and soak tests._

Presence witnesses use a hosting fixture or controlled protocol harness.
Observe-mode integration must still prove that observation produces no upstream
mutations.

Component tests and combined stress tests answer different questions. Keep the
focused witnesses alongside the planned reconnect, slow-storage, stalled
control-plane request, output-flooding, slow-observer, and replica-import
exercises. Record proposed acceptance targets separately from measured results.
A supervisor spawning a task is not evidence that synchronization resumed.

## 11. Apply the lessons at the first owning slice

RFC 0001 §13 incorporates these lessons into the architectural proposal. The
roadmap should deliver them where responsibility first appears:

- Foundation tasks establish contention boundaries, admission before spawning,
  progress reservations, domain dependencies, and cancellation ownership.
- The Ishiban slice delivers negotiation, running-daemon diagnostics,
  configuration semantics, durable replay, and per-incarnation recovery for the
  observation owners.
- ACP hosting adds process termination and reaping, permission/result fences,
  durable dispatch uncertainty, and accepted-command ownership.
- Fleet qualification combines reload, retry, resource exhaustion, replacement,
  and overload without postponing component guarantees to the soak test.

This sequencing keeps the first observer independent of hosted-agent work. It
also prevents the later fleet phase from becoming the first occasion on which
the daemon demonstrates that a restarted component can make progress.

[^1]: [Comenq source baseline](https://github.com/leynos/comenq/tree/19665d11fef9768fa294da6a7dcc5f30b789bc9a).

[^2]: [Merged queue rewrite, PR #149](https://github.com/leynos/comenq/pull/149).

[^3]: [Merged streaming await, PR #228](https://github.com/leynos/comenq/pull/228).

[^4]: [Deployment report, issue #242](https://github.com/leynos/comenq/issues/242),
    and
    [merged diagnostic repair, PR #243](https://github.com/leynos/comenq/pull/243).

[^5]: [Merged environment injection, PR #251](https://github.com/leynos/comenq/pull/251).

[^6]: [Domain extraction requirement, issue #192](https://github.com/leynos/comenq/issues/192),
    and
    [open domain extraction proposal, PR #250](https://github.com/leynos/comenq/pull/250).
    Inspected proposal head: `f2bd23f43c2d41a429358e22f40216667e1c8d25`.

[^7]: [Blocking scans review](https://github.com/leynos/comenq/pull/149#discussion_r3839421409).

[^8]: [History-lock finding](https://github.com/leynos/comenq/pull/228#discussion_r4300783372),
    [pinned lookup implementation](https://github.com/leynos/comenq/blob/19665d11fef9768fa294da6a7dcc5f30b789bc9a/crates/comenqd/src/queue/await_lookup.rs),
    and
    [pinned regression tests](https://github.com/leynos/comenq/blob/19665d11fef9768fa294da6a7dcc5f30b789bc9a/crates/comenqd/src/queue/await_lookup/tests.rs).

[^9]: [Pinned storage wrapper](https://github.com/leynos/comenq/blob/19665d11fef9768fa294da6a7dcc5f30b789bc9a/crates/comenqd/src/queue/store_access.rs),
    and
    [pinned listener](https://github.com/leynos/comenq/blob/19665d11fef9768fa294da6a7dcc5f30b789bc9a/crates/comenqd/src/listener.rs).

[^10]: [Stale-claim review](https://github.com/leynos/comenq/pull/149#discussion_r4137435219),
    [pinned worker entry point](https://github.com/leynos/comenq/blob/19665d11fef9768fa294da6a7dcc5f30b789bc9a/crates/comenqd/src/worker.rs),
    and
    [pinned recovery ordering](https://github.com/leynos/comenq/blob/19665d11fef9768fa294da6a7dcc5f30b789bc9a/crates/comenqd/src/store/scheduling.rs).

[^11]: [Pinned worker remote/local ordering](https://github.com/leynos/comenq/blob/19665d11fef9768fa294da6a7dcc5f30b789bc9a/crates/comenqd/src/worker.rs),
    and
    [pinned completion journal](https://github.com/leynos/comenq/blob/19665d11fef9768fa294da6a7dcc5f30b789bc9a/crates/comenqd/src/store/completion.rs).

[^12]: [Backoff-reset finding](https://github.com/leynos/comenq/pull/149#discussion_r3839393977),
    and
    [pinned supervision and shutdown](https://github.com/leynos/comenq/blob/19665d11fef9768fa294da6a7dcc5f30b789bc9a/crates/comenqd/src/supervisor.rs).

[^13]: [Unresponsive retry wait](https://github.com/leynos/comenq/pull/149#discussion_r3839393978),
    and
    [early-retry regression](https://github.com/leynos/comenq/pull/149#discussion_r3866912105).

[^14]: [Durable retry-floor and headroom finding](https://github.com/leynos/comenq/pull/149#discussion_r4243007562),
    and
    [pinned attempt persistence and scheduling](https://github.com/leynos/comenq/blob/19665d11fef9768fa294da6a7dcc5f30b789bc9a/crates/comenqd/src/store/scheduling.rs).

[^15]: [Pinned retained frame future](https://github.com/leynos/comenq/blob/19665d11fef9768fa294da6a7dcc5f30b789bc9a/crates/comenq/src/client/await_stream.rs),
    and
    [pinned fragmented-frame regression](https://github.com/leynos/comenq/blob/19665d11fef9768fa294da6a7dcc5f30b789bc9a/crates/comenq/src/client/tests/await_transport.rs).

[^16]: [Withdrawn finding and clarified lifetime contract](https://github.com/leynos/comenq/pull/228#discussion_r4301414273).

[^17]: [Pinned capacity and mutation-headroom accounting](https://github.com/leynos/comenq/blob/19665d11fef9768fa294da6a7dcc5f30b789bc9a/crates/comenqd/src/store/bounds.rs).

[^18]: [Configuration migration outcomes and retrospective](https://github.com/leynos/comenq/blob/19665d11fef9768fa294da6a7dcc5f30b789bc9a/docs/execplans/issue-237-migrate-from-ortho-config-v0-4-0-git-tag-to-v0-10-0.md#outcomes--retrospective).

[^19]: [Pinned executable startup contracts](https://github.com/leynos/comenq/blob/19665d11fef9768fa294da6a7dcc5f30b789bc9a/crates/comenqd/tests/startup_contract.rs).
