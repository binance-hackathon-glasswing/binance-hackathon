# Who does what: the per-person split (IDEA-064)

This page is for the four of us. The agent briefs (1–4) prepare each item; the person named does it, decides it or reviews it. Times are UTC (F-121); SGT is UTC+8. "Brief" says which agent prepares the commands, memo or evidence for you.

**Settled by the team, outside these briefs:** final-wallet ownership, the on-call rota, the go-ahead to promote to `main`, and GitHub billing/Actions minutes. Agents only record these; nobody is assigned them here.

## Isaac: execution, signing, market data

| By (UTC) | Task | Ref | Brief |
|---|---|---|---|
| **Oct 17 00:00** (08:00 SGT) | Start the read-only quote-cost capture on your machine with the Web3 API key. Let it run through Mon Oct 19 so it covers 3 UTC days including the weekend | #118, DR-01, IDEA-063 | 1 |
| Oct 17 | Choose the BSC balance RPC with `finalized` support and give its source ID | #92, GAP-71 | 1 |
| Oct 17 | Approve the per-unit network destination list, with Keegan | #32, IDEA-062 | 2 |
| Oct 17–18 | Capture real **unsigned** route bytes (buy and sell for all five tokens, plus USDT → BNB) for the swap decoder | GAP-29, #33 | 2 |
| Oct 18 | MetaMask USDT → BNB first-gas swap on the **dev** wallet (≈ 4 USDT, gas paid in USDT), before any agent trade. Tell brief 1 it's done so the balance capture can be re-taken | #106, F-120 | 2 |
| Oct 19 | Review the measured cost summary and the LIVE profile (with Keith); confirm the `fee_bps` finding | #119, #120 | 1 |
| Oct 19 | Decide the signer's per-token caps and fee cap (with Keith) | #44 (WR-C) | 2 |
| Oct 19 | Owners' review: chain-balance reconciliation D1–D6, and gas top-up rounds (with Keith) | #90/#36, #30 (IDEA-061) | 2 |
| Oct 20 | Place the signer key file on the signer host only (`/etc/larp/signer/wallet.key`, root, `0600`) | DR-03 | 2 |
| **Oct 20** | Run the Gate B proof: one approve + one swap on the dev wallet from committed code, plus the crash tests at each execution step. If it slips, tell Keegan the same day | DR-02..05, DR-19 | 2 |
| ongoing | Review briefs 1 and 3's PRs | — | 1, 3 |

## Keith: strategy and risk

| By (UTC) | Task | Ref | Brief |
|---|---|---|---|
| Oct 19 | Review the measured cost summary and the LIVE profile (with Isaac) | #120 | 1 |
| Oct 19 | Signer caps (with Isaac); owners' review of gas top-ups (with Isaac) | #44, #30 | 2 |
| Oct 19 | Decide: HALT semantics for mandatory sells, and exits during a price-jump hold (with Yao Zhu) | D-DN-09 (#34/#52), IDEA-055 POLICY-HOLD | 3 |
| Oct 19 | Decide: keep the Nov 11 15:00 UTC flatten or move it | #107, DR-14 | 3 |
| before the trial | Confirm the model shadow trial's proposed bars (with Yao Zhu) | #97, IDEA-057 | 3 |
| **Oct 21** | Blind independent labels for the model trial sample | M9, IDEA-057 | 3 |
| **Oct 22** | Confirm every S1 value in the trading plan (§12) and its open decisions (§16), with Yao Zhu | PR #123, GAP-13 | 3 |
| **Oct 22** | Decide SKHYB's red-flag coverage: build it, or record a deviation | #39 | 3 |
| **Oct 22** | Model decision (with Yao Zhu): adopt AIand routing, keep the current provider, or go deterministic | DR-11 | 3 |
| Oct 26 | Sign off your DR items (DR-08, 09, 10, 14) in IDEA-042 | DR-22 | 4 |

## Yao Zhu: evidence, model, hosting records, decisions

| By (UTC) | Task | Ref | Brief |
|---|---|---|---|
| Oct 17 | Point brief 1 to where the AWS setup is recorded (applied plan, hosts, bundle hash, migrations 012/013, alarms); fill any gaps | IDEA-058/051, PR99-RV1 | 1 |
| Oct 17 | Put the public dev wallet address and a real SEC contact in the host config; run the terms capture and install the artifacts on the host | GAP-70, GAP-23 | 1 |
| Oct 17 | Decide whether to add a short dev-shadow window profile so real buy decisions show before Oct 21 | brief 1 item 2 | 1 |
| after Gate A | Model trial host steps: AIand secret, budget `init` with the real prior OpenAI spend, provider check P0, then start the trial | #97, IDEA-057 | 1 |
| Oct 19 | Decide the rehearsal shape (with Keegan) | D-DN-02, GAP-04 | 4 |
| Oct 19 | HALT semantics and price-jump hold exits (with Keith); confirm the trial bars (with Keith) | D-DN-09, POLICY-HOLD | 3 |
| Oct 19–22 | Operations decisions with Keegan: standby, delivery-bound HALT, watchdog, crash loop, memory, clock-HALT clear, restore during the run | D-DN-01/04/06/07/08/10/11 | 4 |
| **Oct 22** | Set the 11 live evidence settings, each with a reason | `intelligence.v1.json` | 3 |
| **Oct 22** | S1 values and the model decision (with Keith) | PR #123, DR-11 | 3 |
| Oct 26 | Review brief 4's work; Gate C sign-off; sign off DR-11, DR-12 | DR-22 | 4 |

## Keegan: runtime, integration, gates

| By (UTC) | Task | Ref | Brief |
|---|---|---|---|
| as soon as evidence lands | Review Gate A item by item in IDEA-042; pin the exact-release CI bundle evidence | GAP-72 | 1 |
| Oct 17 | Approve the destination list (with Isaac); confirm how the signer host is reached and where it's recorded | #32, D-DN-05 | 2 |
| after caps are decided | Install the decided `/etc/larp/signer.json` on the signer host | #44 | 2 |
| Oct 19 | Rehearsal shape (with Yao Zhu); if Gate B slips, record the shortfall as a deviation that day | D-DN-02, GAP-04 | 4 |
| **Oct 20** | Gate B review in IDEA-042 | — | 2 |
| Oct 21–26 | Run the signed rehearsal; keep the daily rehearsal log | DR-21 | 4 |
| Oct 21–25 | Drills on the host: automatic HALT, hourly anchoring criteria 1–6, restore into an empty database, an alarm reaching a person; rehearse the final-wallet switch with a throwaway config | DR-13, 15, 16, 17 | 4 |
| **Oct 22** | Cut line: remove or block whatever isn't working, each recorded as a deviation | GAP-05 | 4 |
| **Oct 26** | Every deviations-register row FINAL; services list; activation pack; Gate C review | DR-18, DR-22, GAP-62 | 4 |
| ongoing | Review brief 2's PRs | — | 2 |

## Dates everyone shares

Oct 17 00:00 capture starts · Oct 19 rehearsal shape and decision day · **Oct 20 Gate B** · Oct 21 rehearsal starts · **Oct 22 cut line, parameters and model frozen** · **Oct 26 build freeze, Gate C** · Oct 27–29 final activation · Oct 29 – Nov 12 scored run.
