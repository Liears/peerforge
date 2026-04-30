# peerforge Heartbeat Protocol

This document defines the minimal runtime heartbeat protocol for `peerforge`.
It is the implementation contract for the heartbeat registry and its interaction
with task dispatch.

## Scope

Heartbeat files are runtime state only.
They answer one question: is an agent currently eligible to receive work?

Heartbeat state must not become the source of truth for task ownership.
Task ownership lives on the board.

## Storage

Each agent writes one file:

- `.peerforge/runtime/heartbeats/<agent>.json`

Rules:

- `<agent>` must be the agent name used by the dispatcher, such as `codex` or `hermes`
- the file path is deterministic and agent-scoped
- the registry is local to the repository workspace
- board files and heartbeat files must not share the same schema

## Minimal Schema

The heartbeat file must contain these fields:

```json
{
  "agent": "codex",
  "state": "ready",
  "updated_at": "2026-04-30T00:00:00+00:00",
  "expires_at": "2026-04-30T00:01:00+00:00"
}
```

Required fields:

- `agent`: agent name
- `state`: one of `ready`, `busy`, or `offline`
- `updated_at`: UTC timestamp of the last heartbeat write
- `expires_at`: UTC timestamp when this heartbeat stops being valid

Optional fields:

- `task_id`: present only while the agent is working a claimed task
- `claim_token`: present only while the agent is working a claimed task
- `message`: short human-readable status note

Normative rules:

- `task_id` and `claim_token` are only valid when `state` is `busy`
- `message` must not be used as machine logic
- unknown extra fields should be ignored by readers

## State Model

`state` has three values:

- `ready`: the agent can accept a new claim
- `busy`: the agent currently owns a valid claim and is executing it
- `offline`: the agent is not eligible for dispatch

State meanings:

- `ready` means dispatch may consider this agent
- `busy` means dispatch must not assign a new task to this agent
- `offline` means dispatch must treat the agent as unavailable

The heartbeat registry is advisory for dispatch eligibility.
It does not own task lifecycle transitions.

## TTL and Expiry

`expires_at` is the heartbeat TTL boundary.

Rules:

- a heartbeat is valid only while `now < expires_at`
- if the file is missing, unreadable, malformed, or expired, treat the agent as `offline`
- `updated_at` is informational and does not control validity
- the dispatcher must not infer liveness from `updated_at` alone

Recommended TTL behavior:

- write heartbeats on dispatch boundaries and/or periodic keepalive ticks
- choose a TTL long enough to survive the expected task execution window
- keep the TTL short enough that dead agents age out quickly

Expiry semantics:

- expired heartbeat means the agent is no longer eligible for new claims
- expired heartbeat does not revoke an already valid board claim
- heartbeat expiry must not mutate `board.json`

## Dispatch Boundary

Dispatch uses heartbeat state as an eligibility filter.

Before dispatch:

1. read the current heartbeat file for each configured agent
2. treat only non-expired `ready` agents as eligible
3. treat `busy` and `offline` agents as ineligible
4. if an agent has no heartbeat file, treat it as `offline`

After dispatch starts:

- if the agent successfully claims work, write or update its heartbeat to `busy`
- the heartbeat should carry the `task_id` and `claim_token` for the active claim
- the claim token in the heartbeat must match the board claim token

After dispatch ends:

- if the task completed successfully, transition the heartbeat back to `ready` or `offline` depending on process lifetime
- if the task failed, timed out, or the process crashed, let the heartbeat expire naturally or mark it `offline`
- do not mark another agent `busy` as a side effect of one agent finishing

Important:

- dispatch may read heartbeat state before claiming, but the board claim is still authoritative
- a valid heartbeat does not reserve a task
- a task claim must still be made on the board under the board lock

## Board Claim Boundary

The board is the source of truth for task ownership.

Heartbeat state must never replace these board fields:

- `claimed_by`
- `claimed_at`
- `lease_expires_at`
- `claim_token`

Interaction rules:

- heartbeat state may inform which agent is allowed to attempt a claim
- the claim itself must be an atomic board mutation
- the claim token written to the board is the authoritative token
- the heartbeat may copy the same token for observability, but must not invent its own ownership token
- board lease expiry decides when a task can be reclaimed
- heartbeat expiry only decides whether the agent is eligible for new work

State separation:

- if the board says a task is claimed, the heartbeat must not override that fact
- if the heartbeat says `busy` but the board claim is gone, the heartbeat is stale and should be corrected on the next update
- if the heartbeat is missing but the board claim is active, the task is still owned until lease expiry

## Failure Semantics

Reader behavior:

- malformed heartbeat file => treat as `offline`
- missing heartbeat file => treat as `offline`
- expired heartbeat => treat as `offline`
- unexpected state value => treat as `offline`

Writer behavior:

- if the registry cannot write atomically, fail the heartbeat update
- if the process cannot determine the current claim token, do not write `busy`
- heartbeat updates must never block board claim progress indefinitely

Dispatcher behavior:

- never assign new work to `busy` or `offline` agents
- never auto-reclaim a board task because a heartbeat expired
- never use heartbeat state as a substitute for board locking

## Minimal Lifecycle

The smallest useful lifecycle is:

1. agent starts with `ready`
2. dispatcher selects the agent as eligible
3. agent claims a board task under the board lock
4. agent updates its heartbeat to `busy` with `task_id` and `claim_token`
5. agent finishes the task
6. agent updates its heartbeat back to `ready` or lets it expire to `offline`

If the process crashes:

- the board claim eventually expires by lease
- the heartbeat eventually expires by TTL
- reclaim happens from the board, not from the heartbeat registry

## Implementation Notes

This protocol intentionally stays small:

- no distributed consensus
- no cross-machine replication
- no shared in-memory registry
- no heartbeat-driven task ownership

The heartbeat registry exists to make readiness and dispatch safer, not to
replace the board.
