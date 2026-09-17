# Connector agent restrictions

A Step’s connector does not run on every agent. Look the connector `Guid` up in [`data/connector-restrictions.json`](../../data/connector-restrictions.json) before setting `AgentCopyID`.

## Lookup

```text
data/connector-restrictions.json
  defaultIfAbsent → ["remote"]
  byGuid[<guid lowercase>] → ["shared"] | ["remote"] | ["shared", "remote"]
```

Missing Guid = `defaultIfAbsent` = **remote only**. The key is an allow-list, not extra bans.

Catalog is lowercase Guids. Node.js processor (`5a70dfd2-9803-4bcf-b090-652b156f7236`) and Python processor (`e14ea2c1-42d4-4224-b308-8ed55168e0c8`) are **shared only** — they must not run on a remote agent.

## Agents

| Value | Agent |
|---|---|
| `shared` | Built-in Shared agent (`AgentCopyID` `11111111-1111-1111-1111-111111111111`) |
| `remote` | A company remote agent (`Agents[]` entry) |

There is no Background agent.

## When generating a transfer

`AgentCopyID` on a Step must be a kind listed for that Guid (or remote, if the Guid is absent). Echo / hash / `fetch()` steps that use Node.js or Python stay on Shared. For a remote-agent Step pick a connector whose `byGuid` entry includes `remote` (JS Mapper does).
