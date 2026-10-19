# C12 reconciliation — trackers, CI issue, branches and organiser questions (2026-10-19)

Keegan's C12 slice from [PR133 remaining actions](PR133_REMAINING_ACTIONS_20261019.md).
GitHub states were read on 2026-10-19 UTC through the GitHub API. Nothing was
closed, deleted, edited or sent by writing this file. The decisions it asks
for are listed at the end.

## #22 — IDEA-046 R01–R18 tracker

9 of 18 children are closed: #23, #24, #26, #28, #29, #31, #34, #35, #40.
The tracker's own checkboxes are all still unticked.

| Open child | What remains (owner, where recorded) |
|---|---|
| #25 R03 issuer IDs | Keith confirms A-T15, then close (checklist "Housekeeping") |
| #27 R05 signing lifetime | Keegan B10: adopt and implement the finite authority model after B02 and A02 timing |
| #30 R08 gas path | Isaac B05 native-proof qualification; operator host check |
| #32 R10 deployment routes | Approved operator: host route qualification for the signed configuration |
| #33 R11 deployable app blocked | B01–B03 verified router source, review and replay (draft #139) |
| #36 R14 chain reconciliation | Waits only on #92 (process balance-health check, IDEA-055 RPC-H03) |
| #37 R15 economic edge | Keith C03 after-cost evaluation |
| #38 R16 cost conventions | Keith C03 staggered evaluation |
| #39 R17 SKHYB red flag | Keith C03 implementation or deviation |

## #42 — whole-repo review WR01–WR22 tracker

17 of 22 children are closed: #43, #45–#48, #50–#54, #57–#59, #61–#64.

| Open child | What remains |
|---|---|
| #44 WR02 signer approve caps | Keith B08 measured review, then Isaac B09 exact policy approval |
| #49 WR07 release integrity | Repository side resolved (IDEA-049-D D-FND-011). Under PC-DEC01 the mirror-CI build is the release build; the step has been followed end to end. The mirror-built `bb46234` passed the production `bind_manifest` byte check on the host (PC-AWS07), and `c5be269`'s bundle and manifest were built and published in mirror CI. The current host build `ea25b52` is a documented local non-CI exception (PC-DEPLOY02), so the Oct19 binding check (IDEA-055 RPC-H03) is not #49 evidence. The next signed release goes through the CI path (C06). **Closed as completed 2026-10-19 (Keegan).** |
| #55 WR13 stale marks | Keith decision (C03) |
| #56 WR14 flatten split / top-up | Keith decision (C03) |
| #60 WR18 memory limits | Isaac decides from measured routed-service memory (C05) |

## #98 — org Actions re-run

The organisation's Actions are still blocked by billing (the latest org run,
39216599144, ran no steps). PC-DEC01 (2026-10-17) accepts mirror-CI builds as
the release builds for every gate, and the latest exact-source mirror
acceptance is run 39227766192 (PR187, all four jobs pass). The issue's own
close condition, an org-repository run, cannot be met while billing is
blocked. **Options:** keep #98 open as a billing reminder, or close it as
"not planned" with a comment citing PC-DEC01 and the mirror runs. Either way,
do not describe billing as fixed.

## Seven retained branches

All seven existed on origin on 2026-10-19 with no open PR. **Keegan decided
2026-10-19:** delete the three Claude-session branches whose PRs are closed and
keep the other four. The full head SHAs of the deleted branches are recorded
below so they can be restored.

| Branch | Last commit by | Earlier PR | Head |
|---|---|---|---|
| `claude/gate-a-inputs` | Claude session | #89 (closed) | `a3f284f139fd6d668b0bcde78014394e1f9db7ac` — **deleted 2026-10-19 (Keegan)** |
| `claude/issue31-day-roll-tests` | Claude session | #82 (closed) | `09c3ed631310cc363cd5580380c111ccefe5bdeb` — **deleted 2026-10-19 (Keegan)** |
| `claude/issue59-systemd-runtime-dirs` | Claude session | #83 (closed) | `96a474de20a535c5e6d9100b9fe8b1e108a5c62f` — **deleted 2026-10-19 (Keegan)** |
| `claude/local-ci-20261015` | Cookiemunchrr | none | `4cf9412` — kept |
| `docs/idea-052-timesfm-20261015` | Cookiemunchrr | none | `6a3a336` — kept |
| `codex/pr-review-system-20261012` | wtvlol | none | `3c837f7` — kept; ask Keith |
| `codex/thin-path` | Keegan | #10 (closed) | `c4a16ec` — kept |

`wtvlol` is the GitHub account that posts Keith's updates on PR133 (for
example the 2026-10-18 prerequisite comment), so Keith is the likely owner of
`codex/pr-review-system-20261012`. Keegan confirms before asking him.

## Organiser questions still to send

Checked against SKILL.md Q-items and F-113..F-124 (the latest organiser
answers). No answer newer than F-124 is recorded.

- **Drop Q-33** from the send list. SKILL.md records it as resolved in practice
  (IDEA-035 C6: the repository registration is done; manifests and version
  events are our own obligation). GAP-42 and the checklist still listed it.
- **Still open, to send:** Q-39 (scoring), Q-04 (valuation), Q-06 (exact
  instants), Q-08 (gas top-up log format only), Q-14 (incident-upload
  deadline only), Q-35 (new secret for the final wallet only).

Draft for Keegan to send in the organisers' chat. It contains no internal IDs,
and agents never send it.

> Hi, a few questions before the scored run:
>
> 1. **Scoring.** Is the ranking the change in total wallet equity from the
>    start to the end of the run, or realised profit on completed trades? How
>    much do drawdown, the decision logs and the code repository count? If it
>    is equity, does BNB held for gas count, and are positions still open at
>    the end valued at market?
> 2. **Valuation.** Which price and which moment are used to value holdings
>    for equity and drawdown (for example the on-chain token price or the
>    reference price, and at what time)?
> 3. **Exact window.** With all times in UTC+0, does the scored run start at
>    2026-10-29 00:00:00 UTC, and does it end at 2026-11-12 00:00:00 or
>    23:59:59 UTC? Oct 29 – Nov 12 covers 15 UTC days, while the page says
>    14 days.
> 4. **Gas top-ups.** Our agent buys BNB for gas with a USDT → BNB swap through
>    quote-and-swap. We log it as its own round with one order (symbol "BNB",
>    side "BUY", amount = the USDT spent, the tx hash) and a reasoning line
>    saying it is a gas top-up. Is that the format you want?
> 5. **Incident uploads.** Batch logs are due by 02:00 UTC the next day. Is
>    there a deadline for the log upload after a material incident?
> 6. **Final wallet.** When we register the final wallet, does it get a new
>    AI_SEEDS secret, separate from the development wallet's, and how will we
>    receive it?

Record each answer as a new F-item in SKILL.md §1.10 and update the matching
Q-item, GAP-42 and the checklist line in the same change.

## Decisions requested from Keegan

Decided 2026-10-19 (Keegan):

1. #98 closed as not planned, with a comment citing PC-DEC01, mirror run
   39227766192 and the still-blocked billing.
2. #49 closed as completed, with a comment citing D-FND-011, PC-DEC01,
   `bb46234`'s host bind PASS (PC-AWS07) and the `c5be269` mirror release.
   The current host's `ea25b52` is a non-CI exception and not #49 evidence.
3. Current-state comments posted on #22 (9/18 closed) and #42 (18/22 closed
   after #49).
4. Branches as in the table above. Keith decides `codex/pr-review-system-20261012`.

Still open: Keegan sends the organiser message above (no agent sends it).
