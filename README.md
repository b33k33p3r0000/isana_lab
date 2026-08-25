# ISANA — witness repository

ISANA is a one-person systematic research lab. It pre-registers its trading hypotheses before it looks at the data, runs them through a fixed statistical ladder, and publishes the outcome either way — the strategies that survive and, in more detail, the ones that did not. The track record it publishes is a **paper (simulated) record**: it verifies costs, execution and operations, not edge. This repository is where the lab's public output is timestamped by parties that are not the lab.

## What is in here

| Path | What it is |
|---|---|
| `site/` | The published site, exactly as it is served: the daily gate (`index.html`), The Ledger (`ledger.html`), The Tales (`tales/`), The Graveyard (`graveyard.html`), the machine-readable payloads (`status.json`, `equity.json`, `graveyard.json`), the Atom feed (`feed.xml`) and the hash chain (`chain.jsonl`). |
| `verify/` | The open-source verifier — one dependency-free Python script that recomputes every hash in `site/chain.jsonl` from the published bytes. Start at [`verify/README.md`](verify/README.md). |
| `proofs/ots/` | Pre-registration hashes and their OpenTimestamps (`.ots`) proofs — each one a Bitcoin-anchored attestation that a given hash existed at a given time. |

Everything here is written by an automated daily publish; each push is one day's entry.

## What the record proves

> Anchors prove a hash existed, unedited, at a time — not that a number is true, and not that we didn't peek (the no-peek claim rests on the vault-gate discipline and says so).

Three independent witnesses carry the daily entry: the GitHub Archive (which ingests public push events hourly and keeps them), OpenTimestamps (Bitcoin), and the Internet Archive (a copy of the day's `status.json`). None of them is operated by the lab, and none of them can tell you whether a published percentage is correct — only that the bytes claiming it have not changed since the day they were pushed. Recomputing the hashes yourself is the point of `verify/`.

## Disclaimer

ISANA is operated by a private individual. It is not an investment firm, is not registered with the ČNB or any other regulator, and nothing here is offered or sold. Nothing on this site is investment advice or a personal recommendation, and nothing is an offer or solicitation to transact in any financial instrument. The track record shown is a PAPER (simulated) record: it verifies costs, execution and operations — not edge. Simulated results have inherent limitations and do not represent actual trading. Past performance is not indicative of future results.

---

ISANA is operated by b33k33p3r · hello@isana.io
