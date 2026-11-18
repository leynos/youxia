# Proposed arun transport contract

## Status and ownership

Proposed, 2026-11-17. This contract accompanies the
[Youxia architecture](../youxia-design.md). It defines semantic requirements
for the private daemon-to-runner protocol; it is not a released wire format.
The implementation gate must select and publish its exact encoding and
independent test vectors before peers depend on it.

`arun` owns one agent process, its pipes, a bounded raw stdout spool, and a
bounded diagnostic stderr tail. `youxiad` owns Agent Client Protocol (ACP)
interpretation through Magitek, authorization, sessions, turns, and durable
domain state. Systemd owns service termination and descendant containment.

No operation below requires `arun` to parse JSON, recognize an ACP method,
identify a session, decide a permission, or declare a turn complete. Byte
segmentation is independent of JSON Lines (JSONL) record boundaries.

## 1. Identity and attachment

A run has an immutable, randomly generated 128-bit `run_id`, rendered as 32
lowercase hexadecimal digits for paths and unit names. Its manifest binds that
identity to the host boot ID, workspace, machine identity, execution
generation, frozen executable/arguments/environment/cwd, and resource profile.
Use native byte-preserving representations for Linux process arguments and
paths; select an explicit binary representation at serialization boundaries.
Never construct a shell command from manifest strings.

The daemon commits launch intent and atomically installs the private manifest
before asking systemd to start the run. `arun` validates the manifest's
version, ownership, identity, and permitted paths before launching. A
service-start timeout triggers reconciliation by the original run ID, never an
immediate second launch with a fresh ID.

The Unix-domain socket lives in a private per-run runtime directory. Socket
mode and peer credentials admit only the configured user. Both peers verify the
run ID, host boot ID, supported protocol version, and effective bounds. This
provides accidental-cross-attachment protection within the cooperative
same-user trust model; it does not defend against a hostile process of that
user.

Exactly one attachment owns stdin writes and acknowledgements. `arun` allocates
a monotonically increasing `attachment_epoch` and validates it on each
mutation. An incumbent must detach, disconnect, or undergo an explicit fenced
takeover before a new controller receives authority. A timeout alone cannot
prove the old writer stopped. At takeover, `arun` accounts for or finishes any
already admitted partial pipe write before allowing new writes. Fencing cannot
undo bytes already written.

`attachment_epoch`, ACP protocol generation, and execution generation are
different values. A socket reconnect can change the first while preserving the
other two. A fresh agent always receives a new run and execution generation.

## 2. Framing and independent directions

Use a bounded outer record protocol on a full-duplex Unix stream. Its fixed
header exposes version, kind, and payload length before payload allocation.
Data records carry opaque bytes; control records carry a bounded typed body.
The encoding gate must define integer widths, endianness, malformed-header
handling, and how future versions reject unsupported fields.

Each record has an absolute byte ceiling. A logical ACP frame may span many
outer data records. The receiver retains partial outer-frame state across
timers and control events. An incomplete or malformed outer record never
reaches agent stdin. No newline, envelope, or terminator is inserted into agent
bytes by this transport.

Independent bounded readers and writers allow stdout consumption while stdin
waits for progress. Small control records have reserved queue capacity and
priority at outer-record boundaries. They cannot overtake bytes already queued
in a kernel socket or pipe. Systemd's stop path remains available independently
of this transport.

## 3. Operations

All mutating operations bind the current attachment epoch. Responses include
the run identity and an operation ID where correlation is required.

| Operation     | Required fields or result                                         | Meaning                                                                                            |
| ------------- | ----------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| `Hello`       | Protocol range, run ID, boot ID, limits                           | Negotiate the private transport before data transfer                                               |
| `Attach`      | Controller instance, requested stdout byte offset, recovery mode  | Establish one fenced writer; return retained interval and current lifecycle                        |
| `Output`      | Start offset, opaque bytes, retained-through offset               | Deliver a contiguous stdout byte interval; duplicates can occur after reconnect                    |
| `AckOutput`   | Durable daemon byte offset                                        | Permit reclamation only through the daemon's recoverable contiguous prefix                         |
| `Write`       | Write sequence, payload digest, opaque bytes                      | Admit a complete bounded chunk to the sole stdin writer                                            |
| `WriteResult` | Sequence, admitted/written/failed state, bytes written            | Report transport progress; never agent acceptance or execution                                     |
| `QueryWrites` | Bounded sequence range                                            | Reconcile outstanding writes after attachment loss                                                 |
| `AckWrites`   | Contiguous retired sequence                                       | Reclaim receipts after the daemon commits their outcomes                                           |
| `PoisonInput` | Reason and last known write sequence                              | Permanently fence stdin when the host abandons a logical publication; no ACP parsing in the runner |
| `Lifecycle`   | Child exit/signal, pipe EOF state, runner failure, output offsets | Report process and transport evidence separately                                                   |
| `Detach`      | Final acknowledged offsets and attachment epoch                   | Release the controller without closing the agent's pipes                                           |
| `Stop`        | Run identity, reason, deadline                                    | Request process shutdown; systemd remains the final containment owner                              |

_Table 1: Proposed operations and their acknowledgement boundaries._

`Attach` reports an explicit gap if the requested prefix has expired, is beyond
the retained end, or belongs to another run. The adapter must not concatenate
that stream onto an existing decoder. Unsupported protocol or identity fails
before any stdin write.

## 4. Stdout spool and durable transfer

`arun` assigns monotonically increasing byte offsets to stdout. It appends
bounded records with checksums and commits a contiguous durable watermark. Only
committed bytes enter the replayable output stream. Group commit has finite
byte and age limits; account for the uncommitted batch separately. Disk append
and synchronization must not block the runner's control path.

The daemon commits received bytes, their run identity, and a contiguous inbox
cursor before sending `AckOutput`. ACP parsing can follow that commit. This
allows the spool to release bytes without claiming that semantic application or
remote publication has completed. Duplicate intervals must match the committed
bytes; a mismatching replay is a transport-integrity failure.

The daemon retains the raw inbox until a compatible protocol checkpoint and all
earlier domain effects make replay unnecessary. A byte cursor alone cannot
justify deletion if reconstruction still needs those bytes. Partial JSONL
records either remain in that journal from a known frame boundary or form part
of the checkpoint; discarding a decoder prefix loses continuity.

Arun's spool and daemon SQLite cannot share a transaction. The order is:

1. Runner commits the stdout interval.
2. Daemon commits its matching inbox interval and recoverable cursor.
3. Daemon acknowledges that cursor.
4. Runner reclaims only acknowledged segments.

Lost acknowledgements cause replay. They must not cause early deletion. During
handoff, both copies consume their respective quotas. Batch limits include
headers, indices, temporary files, and synchronization scratch.

Agent exit is distinct from pipe EOF: a descendant may retain a pipe. The
runner drains through EOF within a finite deadline, records the durable final
offset, and exits. A timeout records incomplete output and asks systemd to end
the remaining cgroup. A process exit code cannot substitute for an ACP prompt
result.

Before normal exit, the runner atomically installs bounded terminal evidence
containing final committed stdout offsets, observed EOF/exit status, and all
unacknowledged stdin sequence/digest/disposition records. Synchronize the file
and containing directory under the declared durability policy. If finalization
fails, report incomplete evidence rather than claiming a complete record.

When no live runner remains, the daemon verifies termination and reads the
committed, checksummed spool and terminal records directly. It imports the
contiguous prefix through the normal inbox transaction before reclaiming any
file. No new runner or agent starts merely to read old output. A finalized EOF
and a valid prefix recovered after runner failure are distinct outcomes;
missing receipts or an interrupted tail preserve uncertainty. Importing bytes
does not authorize replaying ACP host effects.

## 5. Stdin receipts and uncertainty

The daemon journals exact outbound bytes and their semantic operation before
submitting `Write`. Write sequences increase for the whole run and do not
restart on reattachment. Repeating an unretired sequence with the same digest
returns its existing receipt; a different digest fails. Requests older than the
retired high-water mark are rejected, never interpreted as new writes.

`arun` retains accepted chunks and partial write progress until their receipts
can be reconciled. It serializes chunks in sequence order. Disconnecting the
controller does not abandon an admitted prefix or permit another chunk to
overtake it. The daemon must reconcile ambiguous chunks before submitting new
ones, and must not retransmit arbitrary ACP frames through a fresh sequence.

An admitted receipt means retained by the runner. A written receipt means the
OS accepted those bytes on stdin. Neither means the agent parsed the request,
started the prompt, completed a tool call, or durably recorded an effect.
`youxiad` therefore retains `delivery_uncertain` where semantic evidence is
missing even if every byte was written.

A pipe error or expired deadline after a partial write poisons that byte
conversation. `arun` reports the written prefix and stops further writes; the
owning lifecycle policy terminates the run within its deadline. Later JSON must
never follow an abandoned prefix. Death of `arun` ends this execution; its
input receipts do not authorize replay in another run.

The daemon adapter also owns logical-frame abandonment. If any prefix of an ACP
frame may have reached the runner and the host abandons the remaining bytes, it
sends generic `PoisonInput` or stops the run. This applies even when the prefix
ends exactly between complete `Write` chunks, so no runner chunk looks partial.
Poisoning rejects every later write. Ordinary controller loss alone does not
poison stdin: recovery first reconciles unfinished logical publications and
either continues the original bytes through the qualified restoration path or
terminates the conversation.

## 6. Overflow and unattended operation

Stdout has a finite spool budget and a finite detached/stalled lifetime. At its
high watermark the runner stops reading stdout and lets the pipe backpressure
the agent. It preserves already retained bytes. If the configured stall or
detachment deadline expires, the runner records the reason and terminates the
run, with systemd enforcing the final deadline.

Never overwrite unacknowledged stdout in a ring. No policy can guarantee all
three of unlimited output, unlimited daemon absence, and finite storage.
Backpressure can also block an agent from reading cancellation; process
termination remains the fallback when protocol progress is impossible.

Stderr uses a separate bounded tail and explicit dropped-byte counters. It can
discard diagnostic bytes under its declared policy. It must not be mixed into
protocol stdout, fed to Magitek, or copied unboundedly into journald.

Global spool admission reserves a per-run allocation before launch. `arun`
enforces its own allocation while the daemon is absent. Starting, live,
completed-but-retained, and recovery-held spools all count against the same
host budget. Execution-slot retirement does not release a disk reservation:
only actual acknowledged reclamation does. Daemon startup reconstructs these
reservations before admitting new runs. Physical filesystem exhaustion remains
possible and produces a distinct storage-failed outcome. Reserve a small
disposition area; if that write also fails, retain the error through available
systemd/journal evidence without claiming durability.

## 7. Recovery capability gate

A surviving Magitek driver can tolerate a socket interruption through an
adapter that preserves contiguous bytes, pending writes, decoder state, and
protocol identity. It must also classify read/write deadlines and pause policy
explicitly; a transport timeout does not become an unlimited reconnect loop.

A restarted daemon has lost that driver. Safe continuation additionally needs a
versioned host/Magitek restoration contract containing:

- Negotiated ACP version, capabilities, session routes, and protocol identity.
- Request-ID allocation and every unresolved outbound request.
- Inbound reverse-request IDs, permission decisions, and host-effect receipts.
- Raw-input and semantic-application checkpoints, including a partial frame or
  a known preceding frame boundary.
- Retained byte/event credits, pending outcomes, and deadlines.
- Replay rules that reconstruct state without repeating sends, approvals,
  filesystem writes, terminal creation, or other completed effects.

The current Magitek proposal does not supply this contract. Implementation must
qualify it before advertising transparent turn continuation after daemon
failure. If restoration cannot prove continuity, the daemon enters
`recovery_required`, fences new mutations, and preserves uncertain outcomes. It
can keep the process temporarily for inspection within its run budget or
terminate it under explicit policy. A new initialized process may use a
capability-qualified session load; it must not blindly resend the old prompt.

## 8. Required witnesses

The implementation tests the actual runner, socket adapter, and process
boundary. Mocked transport calls alone cannot establish these promises.

- Kill only the daemon during a split JSONL record, reattach, and prove exact
  byte reconstruction with no duplicated effect.
- Drop each acknowledgement around both journal commits and reclaim; prove
  contiguous retained recovery or an explicit gap.
- Lose a `WriteResult`, query the original sequence, and prove no second pipe
  write; then prove that a pipe receipt still leaves semantic uncertainty.
- Fence an old attachment while a write is partial; reject stale commands and
  prove the new controller cannot interleave another prefix.
- Fill stdout and stderr independently; prove stdout preserves its prefix,
  stderr reports truncation, and the final stop path remains bounded.
- Crash `arun`, trigger a run cgroup memory kill, and retain a pipe in a
  descendant; prove no automatic replacement executes accepted work.
- Restart the daemon with an incompatible checkpoint version; prove it does
  not initialize a new ACP conversation on the surviving byte stream.
- Replay a permission/file-operation request after recovery; prove its stored
  disposition prevents a repeated effect or a newly invented approval.
- Finish the agent while the daemon is absent; import the finalized spool and
  outstanding write receipts without launching another agent.
- Accumulate retained spools from completed runs; prove they block new disk
  admission until reclaim and remain accounted for across daemon restart.
- Abandon a logical ACP frame exactly between complete outer chunks; prove
  poisoning prevents the next frame from following its incomplete prefix.

These are acceptance requirements. This document reports no executed runner or
protocol recovery test.
