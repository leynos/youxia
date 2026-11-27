# Architectural decision record (ADR) 0002: ACP host port and adapters

## Status

Proposed. This ADR refines ADR 0001's daemon protocol ownership and authorizes
a separate experimental delivery path. It claims no implemented adapter or
passed qualification gate.

## Date

2026-11-20.

## Context and problem statement

The architecture puts Agent Client Protocol (ACP) interpretation in `youxiad`
and raw process transport in `arun`. It names Magitek directly, while the
roadmap gates runner integration behind Magitek qualification. That sequencing
prevents a local runner experiment from informing the future integration.

Magitek defines the intended capability, event ownership, and outcome
semantics, but its API and resource guarantees remain implementation work.[^1]
An early adapter to the official Rust ACP SDK can exercise the host and runner
boundary without making those guarantees implicit or coupling domain policy to
SDK types.

## Decision drivers

- Develop the runner and daemon integration independently of Magitek delivery.
- Keep one application contract for the provisional and qualified adapters.
- Expose unsupported features and unqualified guarantees explicitly.
- Preserve process, byte, and semantic recovery as separate capabilities.
- Keep Magitek reusable without a dependency on Youxia or its runner protocol.

## Options considered

| Option                                                      | Consequence                                                                       |
| ----------------------------------------------------------- | --------------------------------------------------------------------------------- |
| Wait for Magitek before any runner experiment               | Delays evidence about the independent process and transport boundary              |
| Call the SDK directly from domain owners                    | Couples policy and persisted evidence to a temporary implementation               |
| Define the port from the SDK's current subset               | Makes later Magitek capabilities require domain restructuring                     |
| Own a Magitek-aligned port with explicit capability subsets | Allows early integration while keeping target semantics and qualification visible |

_Table 1: ACP integration alternatives._

## Decision outcome / proposed direction

Youxia owns `AcpHostPort`, domain evidence, and the `acpsdk` and `magitek`
adapters. The [port contract](../contracts/acp-host-port.md) defines
operations, capability dimensions, unavailable results, and shared witnesses.
The daemon composition root selects an adapter; session/operation owners
consume only the port. Both adapters use the same raw runner byte/lifecycle
boundary. `arun` remains independent of ACP, and Magitek remains independent of
Youxia.

Design the port around Magitek's planned semantics. Each adapter declares its
implemented subset and qualification evidence. Consumers reject unavailable
required features and handle optional features explicitly. Core correctness and
truthful uncertainty apply even when the experimental profile has not qualified
all resource bounds.

Select the adapter per protocol generation. Replacement targets new runs or
fresh connections after conformance checks; it does not move uncertain live
work between engines. Neither adapter inherits crash-restored ACP state from
raw byte replay.

## Migration plan

1. Implement the port vocabulary and a fault-capable fake in roadmap 1.5.1.
2. Build the raw runner and provisional SDK adapter independently in 1.5.2 and
   1.5.3, then exercise one local daemon-hosted agent in 1.5.4.
3. Complete failure and capability witnesses in 1.5.5, recording unsupported
   and unqualified behaviours without promoting the experiment to hosting.
4. Qualify resource ownership through 1.3.1 and 3.2.2. Prove the later Magitek
   adapter against the same corpus in 3.2.6 before the full 3.5.3 hosting gate.

## Known risks and limitations

A wrapper cannot establish bounds on hidden SDK allocations. The experimental
profile records those gaps and limits its process exposure without claiming
production capacity. The semantic contract will evolve with implementation
evidence; version its vocabulary and preserve explicit backend translation.
Optional-feature absence must not silently change an operation's meaning.

## Outstanding decisions

- Pin the SDK revision and exact supported subset in the spike report.
- Select concrete Rust signatures and runner encoding from the executable
  contract corpus; keep proposed names separate from released APIs.
- Qualify Magitek adapter parity and resource ownership before promotion.
- Specify restoration or cross-adapter checkpoint migration separately if
  those capabilities become required.

## References

[^1]: [Magitek design at the reviewed revision](https://github.com/leynos/magitek/blob/2296f8ac5d550a2f5706952fb6a641179605dfa5/docs/magitek-design.md),
    §§7–10; [Youxia architecture](../youxia-design.md), §§3 and 7.
