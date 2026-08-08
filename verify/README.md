# Verifying the ISANA daily chain

Every publish day appends one record to `site/chain.jsonl`. Each record hashes the day's published payloads, and each record's own hash is chained to the previous one, so a single edited byte anywhere in the history breaks the links from that day forward. This directory holds the script that checks that, and nothing else — no dependencies, no network, no trust in us.

## What this proves, and what it does not

> Anchors prove a hash existed, unedited, at a time — not that a number is true, and not that we didn't peek (the no-peek claim rests on the vault-gate discipline and says so).

Read that literally. The chain is a **tamper-evidence** mechanism, not an audit:

- **It proves** that the day's `status.json` and `equity.json` are byte-for-byte the ones the chain committed to, that the record for each day is linked to the one before it, and — via the witnesses below — that those bytes existed at a stated time, before the outcomes they would have to be lucky about were known.
- **It does not prove** that any published number is a correct calculation of a real result. That is a paper (simulated) record produced by the lab's own code, and cryptography has nothing to say about arithmetic it did not perform.
- **It does not prove that nobody peeked.** The claim that a strategy's out-of-sample data was read once, after pre-registration, rests on the lab's read-once vault discipline — a process claim, not a mathematical one. It is stated here as a process claim on purpose.

Nothing here is investment advice, and the track record it verifies is a **PAPER (simulated) record: it verifies costs, execution and operations — not edge.**

## Running the verifier

```
git clone https://github.com/b33k33p3r0000/isana_lab
cd isana_lab
python3 verify/verify_chain.py
```

Python 3 and nothing else — no `pip install`, no virtualenv. Options:

- `--all` — attempt the payload-hash recompute for every record instead of only the latest. A clone's working tree holds one day of payloads, so older days report `SKIP` with the commit to check out; the linkage check always covers the whole history.
- `--root <dir>` — verify a copy of the repo somewhere else.

Each check prints one `PASS` / `FAIL` line. The exit code is 0 when nothing failed, 1 otherwise. Three checks run, in order:

1. **Chain linkage** over `site/chain.jsonl` — `entry` starts at 1 and strictly increases, each `h_entry` is the hash of its own record, and each `prev` is the previous record's `h_entry`. A record marked `superseded` is reported, not failed: a corrected day is published *beside* the original, never over it.
2. **Payload hash** — the day's `h_pub` recomputed from the published bytes.
3. **Cross-reference** — the `chain` block printed inside `status.json` names the same entry and day hash as the chain file does.

## The recipe, so you can write your own verifier

Canonical bytes of any JSON object:

```python
json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
```

Then:

- `h_pub` = `sha256(canonical(status.json minus "generated_utc" and "chain") || canonical(equity.json))`. Those two keys are excluded because `generated_utc` stamps the render rather than the data, and the `chain` block cannot hash itself — including either would make a re-render of identical data look like a rewrite.
- `h_entry` = `sha256(canonical(the chain record minus "h_entry"))`.
- `prev` = the previous record's `h_entry`; `null` for the first.
- `h_raw` is reserved and currently `null` — it is where the hash of the private broker export lands when that pipeline ships (commit now, reveal later).
- `plate_seed` is the daily plate's deterministic seed. It is deliberately **not** part of the `h_pub` preimage: `h_pub` covers the published data, and the plate is an artwork derived from public market data.

## The three witnesses

| Witness | What it timestamps | How to check it yourself |
|---|---|---|
| **GitHub Archive** | The push. Public GitHub events are ingested hourly and archived permanently, so the commit that carries a day's chain entry is timestamped by a third party that cannot be asked to forget it. | Query the GH Archive dataset for `PushEvent`s on `b33k33p3r0000/isana_lab`, or read the commit dates in `git log`. |
| **OpenTimestamps** | Pre-registration hashes, anchored in the Bitcoin blockchain. A `.ots` proof in `proofs/ots/` attests that a hypothesis's hash existed before the data was looked at. | `ots verify proofs/ots/<hash>.txt.ots` with the OpenTimestamps client, or drag-and-drop at opentimestamps.org. |
| **Internet Archive** | The day's `status.json` as served, captured through Save Page Now. | Look up the site URL in the Wayback Machine and compare the captured bytes against this repo's `site/status.json` for that date. |

Each one is independent of the others and none is operated by the lab. That redundancy is the point: any single witness could in principle be argued with; three that would have to agree on a lie could not be arranged after the fact.
