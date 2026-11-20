# Architectural decision record (ADR) 0001: Linux supervision and agent transport

## Status

Proposed. The Linux/systemd platform and protocol-agnostic runner boundary
follow the user brief. The service topology and recovery contracts below
require review and implementation evidence; this ADR records no acceptance or
deployed capability.

[Proposed ADR 0002](adr-0002-acp-host-port-and-adapters.md) refines the
daemon's ACP engine boundary with an application-owned port and an early SDK
adapter. The independent runner lifetime and recovery requirements below remain
intact.

## Date

2026-11-17.

## Context and problem statement

RFC 0001 initially assigns agent process and stdio ownership to the daemon and
requires termination/reconciliation on daemon restart. The requested `arun`
component changes that lifetime: agents should retain their pipes when the
daemon disconnects. ACP interpretation and application policy stay in
`youxiad`. Preserving agents after runner death remains outside scope.

The inspected Lody architecture uses a watchdog or desktop host around a worker
that owns agent subprocesses. Compatibility depends on the selected public
protocols and outcomes, not that internal process topology.[^1]

## Decision drivers

- Preserve bounded agent transport during daemon maintenance or failure.
- Keep ACP and policy ownership in the daemon through the Magitek library.
- Use the Linux service manager for process lifecycle and cgroup enforcement.
- Bound aggregate, workspace, and run resources without duplicating systemd.
- Preserve uncertainty when transport evidence cannot prove semantic outcomes.
- Keep migration from Lody explicit and free from concurrent execution owners.

## Options considered

| Option                         | Benefit                                        | Cost or failure mode                                                                     |
| ------------------------------ | ---------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Daemon-owned stdio             | Few components                                 | Daemon death removes the transport owner                                                 |
| ACP-aware runner               | Protocol state can outlive daemon              | Duplicates host policy/runtime concerns across runners and changes the selected boundary |
| Independent raw runner service | Preserves process/pipes and isolates resources | Needs a private replay protocol and separate ACP restoration contract                    |
| Automatic runner restart       | Appears to restore availability                | Creates a new agent execution while the old effect may remain uncertain                  |

_Table 1: Process-lifetime alternatives._

## Decision outcome / proposed direction

Run `youxiad` and each `arun` as independently managed services. Put control,
replicas, and agents in separate child slices beneath `youxia.slice`; add
workspace agent slices for aggregate policy. Use a lingering user manager for
unattended cooperative operation. Systemd owns cgroups; no `Delegate=yes` or
custom cgroup hierarchy manager is required.[^2]

The runner service uses a known main process, group termination, no automatic
restart, finite start/stop deadlines, and a declared OOM policy. It has no
daemon lifecycle dependency. Runner sockets and persistent output remain
independent of daemon runtime-directory cleanup.[^3]

`arun` owns one agent's pipes, bounded stdout replay, bounded stderr
diagnostics, fenced transport writes, and child exit evidence. Magitek runs
inside `youxiad` and owns ACP protocol mechanics. The daemon owns durable
commands, permissions, effects, and recovery. Murder remains the native
Flock-compatible metadata library in replica workers; it has no supervision
role.

Durable launch intent precedes the manager request. Ambiguous launches query
the same run/unit. Daemon recovery reconciles services, byte cursors, protocol
state, and effects before advertising readiness. Neither pipe-write receipts
nor a surviving process establishes exactly-once execution.

The current Magitek design does not restore an old ACP driver after daemon
death.[^4] Require an explicit versioned restoration contract. Until it passes,
advertise bounded process/byte survival and a truthful recovery-required state,
not transparent continuation. Keep uncertain prompts fenced from automatic
resubmission.

## Migration plan

1. Add the proposed architecture and transport contract; amend RFC 0001 and
   relevant roadmap tasks without marking implementation complete.
2. Build and qualify the systemd/runner boundary before the first hosted agent.
3. Qualify Magitek restoration independently from ordinary live-driver socket
   reconnection; retain explicit failure outcomes if the gate remains open.
4. Drain and stop selected Lody executions before transferring identity.
   Existing Lody-owned pipes have no adoption protocol in this design.
5. Introduce new Youxia runs under the runner architecture and rehearse daemon
   maintenance, runner failure, host reboot, and compatible rollback.

## Known risks and limitations

Finite buffering cannot support unlimited output during unlimited daemon
absence. Backpressure and a bounded termination policy are required. A runner
failure ends its agent; the service must not automatically recreate uncertain
work. Host/user-manager loss also ends live executions.

User-level cgroups provide cooperative resource control. Same-user agents can
access user resources and manager IPC unless another isolation boundary
prevents it. CPU weights and quotas do not reserve latency, and inherited
limits can invalidate an illustrative capacity profile.[^2]

The manager's unit metadata is not durable application history. Persistent
identity/effect ledgers and bounded startup reconciliation remain necessary.
Process-state restoration and ACP-state restoration are separate problems.

## Outstanding decisions

- Pin the actual supported host/service-manager capabilities and workload
  resource profile after measurement.
- Select the runner wire encoding and publish byte-level conformance vectors.
- Specify and qualify Magitek protocol restoration, effect deduplication, and
  checkpoint upgrade/rollback compatibility.
- Complete murder reader/writer and deployed Lody compatibility qualification.

The [architecture design](../youxia-design.md) owns component relationships and
acceptance gates. The [runner contract](../contracts/arun-transport.md) owns
private transport semantics.

## References

[^1]: [Lody architecture at the inspected revision](https://github.com/leynos/lody-docs/blob/da27f215df33d6ee5938461d6c060acb959dd1fb/docs/architecture/README.md).

[^2]: [Systemd cgroup ownership](https://systemd.io/CGROUP_DELEGATION/)
    and [resource controls](https://www.freedesktop.org/software/systemd/man/latest/systemd.resource-control.html).

[^3]: [Systemd service lifecycle](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html),
    [termination](https://www.freedesktop.org/software/systemd/man/latest/systemd.kill.html),
    and [runtime directories](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html).

[^4]: [Magitek proposed design, including replacement-stream semantics](https://github.com/leynos/magitek/blob/bfef49cbf10912ccf8ed246d4760bbb21f96c01b/docs/magitek-design.md).
