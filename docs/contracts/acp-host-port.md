# Proposed ACP host port contract

## Status and ownership

Proposed, 2026-11-20. This contract defines Youxia's application-facing Agent
Client Protocol (ACP) boundary. It accompanies
[ADR 0002](../adrs/adr-0002-acp-host-port-and-adapters.md) and the
[architecture design](../youxia-design.md) §3.3. Interface names below describe
the intended semantics; they are not implemented Rust signatures.

`youxiad` owns `AcpHostPort` and its domain vocabulary. The port follows
Magitek's planned capabilities and evidence semantics, while allowing each
adapter to implement a declared subset.[^1] The `acpsdk` adapter initially uses
the official Rust `agent-client-protocol` SDK. The later `magitek` adapter uses
Magitek's qualified public API. These are adapter identities, not claims that
either implementation exists in Youxia.

## 1. Dependency and process boundaries

| Component                    | Owns                                                                              | May depend on                                                |
| ---------------------------- | --------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| Session and operation owners | Admission, permissions, durable acceptance, effects, and recovery                 | Youxia domain types and the ACP host port                    |
| `AcpHostPort`                | Application operations, evidence, capabilities, and lifecycle contract            | Domain types; no concrete SDK or Magitek types               |
| `acpsdk` adapter             | Translate the port to the pinned official Rust SDK                                | The port, SDK, and host-supplied services/byte streams       |
| `magitek` adapter            | Translate the same port to the qualified Magitek facade                           | The port, Magitek, and host-supplied services/byte streams   |
| Runner byte adapter          | Unwrap raw output, journal bytes, reconcile writes, and expose lifecycle evidence | The private runner contract and daemon storage services      |
| `arun`                       | Agent pipes, raw retention, write receipts, and execution lifetime                | Its private transport; no ACP engine or domain session types |

_Table 1: Port and adapter ownership._

The daemon composition root selects an engine adapter and supplies the runner
byte adapter plus authorized host services. Both engine adapters consume the
same byte/lifecycle boundary. Neither starts a second process for an execution
already owned by `arun`. The CLI calls daemon operations, never either engine
directly. Keep the initial interfaces and adapters as modules unless an actual
reuse boundary justifies separate crates.

Magitek remains an independent library: it does not import Youxia's port or
`arun` protocol. The consuming adapter translates between the two public
contracts. SDK request objects, Magitek handles, concrete event leases, and
backend error types cannot escape into domain policy or persisted records.
Translate them without losing event ownership, charge lifetime, or evidence.

## 2. Operations and evidence

The port covers connection initialization and negotiated capabilities; session
creation and supported loading/configuration; prompt submission; ordered
updates; permission and installed host-service requests/responses; explicit
cancellation; status, quiesce, and close. Extend optional operations as
Magitek's planned capability set develops, with explicit support evidence.
Process termination remains a separate daemon/systemd operation.

All commands, events, and response authorities bind the run, execution,
protocol generation, and relevant session/operation identity. Peer IDs remain
opaque. A local route must not imply that every asynchronous session update
belongs to the current prompt.

Use domain equivalents of Magitek's submission evidence:[^1]

- `NotSubmitted` means publication definitely did not begin. A local policy
  rejection or unsupported operation can establish this outcome.
- `OutcomeUnknown` means publication may have begun and no evidence excludes
  the effect. Preserve that uncertainty before any retry decision.
- `PeerResult` means a validated correlated response and the required preceding
  event-delivery fence. It does not mean durable host commit or Lody receipt.
- `CancellationRequested` records the cancellation obligation; `PeerCancelled`
  records the separate peer evidence. Neither proves process exit or rollback.

The daemon's accepted receipt, an `arun` pipe-write receipt, a protocol result,
durable transcript commit, and upstream publication remain separate evidence.
Dropping a waiter does not cancel accepted work. Required events cannot
silently disappear: a backend that cannot represent or deliver them must expose
an incomplete/failed operation, never a complete transcript. A terminal
projection cannot overtake its preceding durable output.

The port must preserve charge ownership for retained events, including after
dequeue and close. A concrete implementation can retain an opaque adapter-owned
lease behind a domain-facing owner; releasing that owner releases capacity, not
a durable acknowledgement. An unqualified SDK implementation must declare
unmeasured internal retention rather than infer it from a bounded front queue.

## 3. Capabilities and unavailability

Capture an immutable support snapshot for each protocol generation: adapter
identity/version, port-contract version, selected profile, implemented
operations, negotiated peer features, and qualified guarantees. Keep current
service readiness and authorization separately queryable. Diagnostics expose
these dimensions rather than reducing them to one `supported` flag.

| Dimension              | Meaning                                           | Example                                                             |
| ---------------------- | ------------------------------------------------- | ------------------------------------------------------------------- |
| Adapter implementation | The adapter can express the operation             | The SDK adapter has no checkpoint-restoration API                   |
| Peer negotiation       | This agent advertises the required wire feature   | Session loading requires peer support                               |
| Installed host service | The daemon has an implementation for the callback | Terminal execution requires a run-bound executor                    |
| Policy authority       | The operation is permitted now                    | A permitted filesystem service still restricts paths                |
| Runtime readiness      | Required owners and capacity are available now    | Storage blockage temporarily prevents admission                     |
| Qualification          | Evidence covers the requested guarantee/profile   | A local SDK experiment has not passed retained-credit qualification |

_Table 2: Independent capability and availability dimensions._

Peer operations and advertised client services have different directions.
Compute effective availability from the dimensions applicable to that
operation. Advertise a host service only when its implementation, adapter, and
policy permit it; an SDK method's existence is insufficient. Recheck readiness
and policy during serialized admission and before a host effect. A capability
query cannot reserve authority or close the race with revocation.

Return typed reasons for unsupported adapter/peer features, missing host
services, policy denial, temporary unavailability, an unqualified profile, and
an expired generation. Include the relevant capability and retry eligibility
without leaking backend types. For outbound work rejected before publication,
combine the reason with `NotSubmitted`. After possible publication, preserve
`OutcomeUnknown` or stronger observed evidence; do not recast a timeout as a
safe unsupported-operation retry.

Consumers skip optional work, report its unavailable reason, or select an
explicitly equivalent supported workflow. They reject work whose required
capability is absent. They must not translate missing cancellation into dropped
observation, a missing permission service into approval, or failed session
loading into replay of an uncertain prompt. Local authority may contract during
a generation; existing negotiated wire capabilities do not silently expand.
Newly enabled wire services require renegotiation through a fresh generation.

## 4. Experimental and qualified profiles

The early `acpsdk` experiment selects one disposable local run, explicit
deadlines, finite runner spool and outer-frame limits, and effective systemd
resource limits. It records the exact SDK revision, feature set, peer, missing
services, and unmeasured internal queues. It publishes no Lody presence,
catalogue changes, or remote execution claim. It does not depend on Murder,
Loro replication, or cloud authentication.

Start with initialization, one new session, one prompt, ordered output, status,
and close against a scripted peer; then use an already installed, configured
agent whose required services fit the profile. Permission requests require an
explicit supported decision path or a declared denial. Keep filesystem and
terminal services unadvertised until their implementations meet the applicable
authority, resource, and lifetime contracts.

End-to-end bounded retention remains unqualified until the selected engine
proves all internal ownership paths. A process memory ceiling contains a
failure; it does not prove pre-allocation admission. The experimental profile
does not satisfy roadmap 1.3.1, 3.2.2, or 3.5.3 by itself. Generation fencing,
truthful evidence, event completeness, permission authority, and the
distinction between bytes and effects apply in every profile.

The qualified hosting profile requires the implemented and measured resource
contract plus the selected capability corpus and full one-agent acceptance
gate. Missing optional features can remain unavailable; required guarantees
cannot become optional flags. The read-only observation path remains
independent of either ACP adapter.

## 5. Adapter replacement and recovery

Select one adapter for each protocol generation and persist its identity,
contract/profile version, and any checkpoint format with the run evidence.
Switch the configured adapter for new runs or genuinely fresh protocol
connections after the relevant conformance suite passes. Merely replacing a
socket attachment does not create a fresh ACP conversation on existing pipes.

Never hot-swap a driver during an active or uncertain turn. Existing work keeps
its original owner, drains under that adapter, or enters explicit recovery.
Cross-adapter restoration would require its own versioned migration contract
and witnesses; no such capability is assumed here.

Process survival, raw byte recovery, live-driver socket reattachment, session
loading on a fresh connection, and protocol restoration after daemon death are
separate capabilities. Magitek's current design holds protocol state in memory
and does not promise crash restoration.[^1] The provisional SDK path likewise
claims none. After daemon death, retain raw evidence, fence mutations, and
report `recovery_required`; bounded inspection or explicit termination follows
the existing
[runner recovery contract](arun-transport.md#7-recovery-capability-gate). Do
not initialize a new driver on the old stream or resend an uncertain prompt.

## 6. Shared acceptance witnesses

Run the same observable contract corpus through the fake, SDK, and later
Magitek adapters. Record supported, unsupported, unqualified, failed, and
not-run cases separately; a missing required capability is a failed profile,
not a skipped success. The initial corpus must distinguish:

- An unsupported optional feature from policy denial, transient saturation,
  and generation expiry, including revocation between query and admission.
- A pre-publication rejection from a lost response after possible submission;
  the latter cannot trigger automatic prompt replay.
- Required updates followed by a response from incomplete, reordered, or
  unrepresentable events; terminal projection waits for the durable prefix.
- Permission wait/cancel/close from a blocked ordered dispatcher; stale
  responses cannot authorize a replacement run.
- Partial byte records and lost write receipts from fresh sends; runner tests
  prove exact retained prefixes and no duplicate pipe writes.
- Daemon death with a surviving agent from restored ACP state; the SDK spike
  recovers raw evidence and reports `recovery_required` without reinitializing.
- Selecting another adapter for a new run from replacing an uncertain live
  driver; the same domain workflow runs without backend-specific branches.

Resource probes additionally cover retained events across close, slow
consumers, and internal queues before either adapter claims qualified hosting.
Test the actual daemon composition root and runner transport, not just fake
method calls. The roadmap assigns implementation and promotion to step 1.5 and
tasks 3.2.2, 3.2.6, and 3.5.3.

## References

[^1]: [Magitek design at the reviewed revision](https://github.com/leynos/magitek/blob/2296f8ac5d550a2f5706952fb6a641179605dfa5/docs/magitek-design.md),
    especially §§2.3, 5.4, and 7–10. Its named types and qualification targets
    describe planned capabilities, not a released implementation.
