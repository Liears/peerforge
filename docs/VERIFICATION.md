# peerforge Verification Matrix

Use this matrix for workflow changes that affect `task-run-next`, board locking, claims, or heartbeat state.

## P0 Coverage

1. `task-run-next` smoke test
   - command returns a transcript path or structured result
   - next pending task is marked with run metadata
   - no duplicate claim occurs under a single run

2. Board locking test
   - concurrent `task-add` or `task-update` calls do not corrupt `board.json`
   - `task-run-next` does not write the board without taking the lock
   - read-only commands (`check`, `ready`, `task-list`, `task-next`) stay read-only

3. Atomic claim test
   - two runners contending for the same task produce one winner
   - the losing path is deterministic and non-destructive
   - claim fields are written before dispatch starts

4. Heartbeat registry test
   - `ready|busy|offline` state is persisted under `.peerforge/`
   - dispatch reads the same status model it writes
   - stale or missing heartbeat data does not mutate the board

## Baseline Commands

```bash
python3 peerforge/bus.py check --config .peerforge/config.json
python3 peerforge/bus.py ready --config .peerforge/config.json
python3 peerforge/bus.py task-next --root .peerforge
python3 peerforge/bus.py task-run-next --root .peerforge --config .peerforge/config.json --ready-only --bootstrap
```

## Recommended Run Order

1. lock board writes
2. verify atomic claim behavior
3. wire heartbeat registry into readiness
4. re-run the smoke test commands above
