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
| #49 WR07 release integrity | Repository side resolved (IDEA-049-D D-FND-011). Under PC-DEC01 the mirror-CI build is the release build: the `c5be269` bundle and manifest were built in mirror CI, and on 2026-10-19 the host check found runtime/manifest binding consistent (IDEA-055 RPC-H03). **Candidate to close; Keegan decides.** |
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

All seven still exist on origin and have no open PR. Each needs keep, reopen
or delete. Deleting is irreversible on GitHub, so it is done only after the
owner's explicit answer.

| Branch | Last commit by | Earlier PR | Head |
|---|---|---|---|
| `claude/gate-a-inputs` | Claude session | #89 (closed) | `a3f284f` |
| `claude/issue31-day-roll-tests` | Claude session | #82 (closed) | `09c3ed6` |
| `claude/issue59-systemd-runtime-dirs` | Claude session | #83 (closed) | `96a474d` |
| `claude/local-ci-20261015` | Cookiemunchrr | none | `4cf9412` |
| `docs/idea-052-timesfm-20261015` | Cookiemunchrr | none | `6a3a336` |
| `codex/pr-review-system-20261012` | wtvlol | none | `3c837f7` |
| `codex/thin-path` | Keegan | #10 (closed) | `c4a16ec` |

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

1. #98: keep open, or close as not planned citing PC-DEC01.
2. #49: close, citing PC-DEC01, the mirror-built `c5be269` manifest and the
   Oct19 binding check, or keep open.
3. Post a short current-state comment on #22 and #42 (counts and open
   children above), or leave the trackers as they are.
4. Disposition of each of the seven branches.
5. Send the organiser message above (Keegan sends it; no agent does).
