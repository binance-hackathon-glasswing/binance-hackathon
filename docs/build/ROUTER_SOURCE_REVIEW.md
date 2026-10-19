# Isaac task 3: router source review (#138)

Status reviewed 2026-10-19: **source/ABI unavailable in this evidence packet;
current explorer verification status unresolved**, not ready for deployment. Record: IDEA-070 RE-01 / RV139. Decoder
PR130 is merged into integration; this handoff uses its current RV-130 checks.
This task has its own branch, `codex/isaac-03-router-evidence-20261017`.

## Historical browser finding (RE-01 B1, 2026-10-17)

Isaac's screenshot shows “Verify and Publish”, “Add Custom ABI”, and hexadecimal
bytecode rather than published source/ABI. The hexadecimal is compiled code;
it is not the source or ABI requested below. Do not add a custom ABI or attempt
to verify/publish this third-party contract.

The **Read Facets** tab also failed: Isaac reports “unable to retrieve a valid
contract ABI” (RE-01 B2). There is no ABI to copy from that failed view.

A bounded public read-only lookup found a candidate for the swap selector:
**[0xa9fa1b56f4d7bd25375c2d40b4c8e36a9509e603 on BscScan](https://bscscan.com/address/0xa9fa1b56f4d7bd25375c2d40b4c8e36a9509e603#code)**.
The standard `facetAddress(bytes4)` lookup for `0xad43f73d` returned this address
at finalized block `0x7a2eb81`; it has8622 deployed code bytes there. The block
hash was rechecked; the evidence report is `evidence/router-facet-lookup-20261017.json`.
This is an identity lead from one provider, not source/safety or upgrade proof.
Sourcify returned404 for this candidate too.

**Next browser step:** open that distinct candidate page and report whether its
Code tab displays verified source or only Verify and Publish/bytecode. If source
exists, the conditional export steps below apply to that candidate, while the
router's dispatch/mapping and any additional helpers still require review.
Do not try to publish a custom ABI to repair the failed explorer view.

## Evidence needed from Isaac's browser

1. Open [the router's BscScan Contract tab](https://bscscan.com/address/0xb44446b0c8e56988c34f7ff73ae904982b5fdda5#code).
   Confirm this is BNB Smart Chain, chain56, and the exact router address above.
2. If verified source is displayed, save the complete source (all files/imports,
   or the explorer's source/standard-JSON export) and Contract ABI JSON **outside
   the repository**. Retain the original files without reformatting. Also save
   the page or a plain-text note of its URL, verification status, compiler,
   contract name and UTC retrieval time. These are public artifacts; no wallet
   connection, signing or secret is needed.
3. Inspect the proxy information. If it identifies an implementation, include
   its address, verified source and ABI too. An unknown proxy status is not
   evidence for `implementation: null`. A proxy shell alone is insufficient;
   any facets/delegated implementation handling the selector must be reviewed.
4. Tell Codex the local folder path. Codex can read and hash the files and
   continue the source review. There is no need to paste source or API keys
   into chat.
5. If the source is unverified or your browser is blocked too, report that
   result. Keep task3 open; the team must resolve source availability before
   this evidence path can proceed.

The automated attempt returned a Cloudflare challenge (HTTP403). Sourcify's
documented v2 lookup returned HTTP404 with no match. Neither result determines
BscScan's verification status. Retained response bytes/headers are outside Git
at `/private/tmp/larp-isaac-router-20261017`; the committed acquisition report
contains response-body hashes and outcomes only. **Those hashes must never be
used as source or ABI hashes.** The authenticated Etherscan source API is an
alternative if suitable account access already exists; no API key was read or
used here. Do not create a paid subscription for this handoff.

## Review after the source is available

Isaac's source review must establish each item; all remain unresolved today:

| Requirement | Evidence to record |
|---|---|
| Provenance | Exact source/ABI file SHA256, explorer URL, verification/compiler metadata, retrieval time and implementation/facet identity where applicable |
| Swap signature | Canonical ABI tuple signature whose keccak selector is `0xad43f73d`; derive from source/ABI, not a selector registry |
| Economic field paths | Zero-based tuple paths and leaf types for pay/receive token, amount, minimum output, recipient and deadline |
| Native BNB | Source-defined native sentinels and the treatment of `msg.value` |
| Minimum output | Concrete code proving the minimum is enforced on the recipient's balance, including helper/delegated route behavior |
| Deadline | Concrete code enforcing the encoded deadline |
| Input authority | Concrete code proving the input is pulled only from `msg.sender`, including helper/delegated route behavior |
| Wallet debit bound | Concrete code proving all nested/delegated calls can debit only the decoded pay token and amount, with no access to other wallet assets or approval authority (RV-130 R11) |
| Independent review | Keegan's actual review reference; never attribute review before it happens |

If any guarantee is false or unsupported, stop the evidence path and record the
finding for the team. A schema accepting `true` does not establish a guarantee.
No runtime config or signer policy should reference this acquisition report.

When the facts are established, fill the existing `RouterEvidence.v1` template
in [GATE_B.md](GATE_B.md), push it before running the evidence/selector checks,
and obtain Keegan's review. Only then can this task's PR become ready and close
#138. Keep parent #33/GAP-29 open for the remaining acceptance requirements.

Task4 is the separate recorded-route replay over Keith's existing IDEA-063
quote artifacts after Keegan's evidence review, using merged PR130. No new capture
is needed here. Signing lifetime #27, caps #44, gas, signer access, deployment
and the first agent trades remain later tasks.

## If the candidate's source is also unavailable

Keep the task and live signing blocked. Isaac can forward this draft request to
the team supporting the router returned by the Web3 API; it has **not** been sent:

> Our BSC quote-and-swap responses target router
> `0xb44446b0c8e56988c34f7ff73ae904982b5fdda5`, selector `0xad43f73d`.
> On 2026-10-17 our browser observation showed no published router source/ABI,
> and Read Facets failed to retrieve an ABI. Later automated Code requests were
> blocked (HTTP403), so current explorer verification status remains unknown.
> A public `facetAddress(bytes4)` lookup at finalized block `0x7a2eb81` returned
> `0xa9fa1b56f4d7bd25375c2d40b4c8e36a9509e603`. Could you provide the
> complete verified source/ABI and compiler settings for this selector's code,
> router dispatch, and relevant helpers, plus how to verify their chain56 code
> identities and detect implementation upgrades? We need to establish recipient
> minimum-output, deadline, sender-only input enforcement, and wallet debits
> limited to the decoded pay token/amount across every nested call before signing.

Do not mark these guarantees true on the strength of an unsupported statement
or decompiled bytecode. Source provenance, source-to-code binding and independent
review remain required.

## SP-01 recheck — 2026-10-18 07:44UTC

User requested obtaining source or recording the exact blocker. Bounded public
reads after pushed SP-01/T1 criteria946edfc are retained in
[evidence/router-source-recheck-20261018.json](evidence/router-source-recheck-20261018.json).
System curl with TLS verification reached the candidate facet Code page:
HTTP403, Cloudflare challenge,5549bytes, body hash
02abae28a7f42917badf2c92803bc42706aacacec7df35ebda0167df0965a263.
Sourcify v2: HTTP404,125bytes, all match fields null, hash
d7ab73b48ed5ffaad1ab9898b249500c806f723b81eb2e4f3d908705cbbb0a0c.
The initial Python transport had no CA file and received no HTTP bodies; it
did not establish endpoint availability or verification status. No TLS bypass.

No verified source/ABI, dispatch/helper/deployed-code binding or independent
four-guarantee review was obtained. The403 does not prove the candidate is
unverified; the old router-unverified finding remains Isaac's attributed browser
evidence. Exact-address web search and checked LiquidMesh overview did not
supply attributable chain56 source. Keep this PR draft, #138/#33 open and signing
blocked. No compiler/signature/field path/upgrade guarantee has been invented.

Keith's interim handoff is now in PR133: all29 file hashes/lengths verify;15
latest successful BUY/SELL/requote artifacts cover all five stock directions.
**Router check NOT_RUN** until truthful source evidence and Keegan's actual
independent review exist. A source export from a permitted ordinary browser or
the existing vendor-request draft remains the next action; no vendor message
was sent. Current source, fee, native and gas findings/owner decisions are
recorded in PR133's docs/build/SIGNED_PREREQUISITES_20261018.md (SP-01).

## RE-02 — current separate-PR source point (2026-10-18)

Isaac asks for each immediate point in its own PR and confirms no source export
is available. This existing source-only draft PR139 remains that point's PR.
Three bounded public GETs at10:59:10–11UTC returned:

| Alternative | Result / significance |
|---|---|
| Candidate facet BscScan Code |403/Cloudflare challenge; still no source body, no inference about verification status |
| BscScan public legacy source API |301, not followed under no-redirect acquisition policy; not source evidence |
| Etherscan v2, chainid56, exact facet, no account key |HTTP200 but status failure/NOTOK, Missing/Invalid API Key; authenticated source retrieval is unavailable without account access |

[Exact report](evidence/router-source-alternatives-20261018.json), SHA256
3d04c7186a398794f53b0818bd891ee3b09a80a8e8de541f261f3b00a85495e4. These are request/response hashes, never source/ABI hashes.
Existing Sourcify no-match evidence stands. No source export or account access
was invented, no paid signup/key search was attempted and no external message
was sent. Independent source review and route checker remain NOT_RUN.

**Concrete missing input:** a permitted browser export or authenticated source
retrieval for the exact candidate plus router dispatch/all delegated helpers,
including full source imports, ABI, compiler/settings and deployed-code binding.
The wallet/private key is irrelevant to acquiring public contract source. An
explorer API key, if the owner already has one, is a distinct account credential
and stays outside Git/chat; none was supplied or read here.

The existing vendor request above is ready to forward through the team's own
confirmed contact; no contact or permission to impersonate a teammate is assumed.
After delivery: retain/hash original bytes, establish signature/paths/native
semantics and all four guarantees from complete code, obtain Keegan's actual
review, then run the existing real-artifact checker. Keep this PR draft and
#138/#33/GAP29/signing blocked until that evidence actually exists.

## RE-03 — additional public retrieval, 2026-10-18

Both direct public Routescan Etherscan-compatible chain56 source requests
(router and candidate facet) returned HTTP200/status0, `chain not supported`,
at13:59:09–10UTC. This API cannot supply BSC source. It says nothing about
whether the actual router/facet is verified elsewhere. Browser BscScan access
also failed (router403; facet inaccessible); same-address Ethereum/Polygon
search results and cached Ethereum bytecode are not chain56 source evidence.
No cross-chain code match or source review is inferred.

[Exact two-request report](evidence/router-source-routescan-20261018.json),
SHA256 `f7b24db6572f2c43e314dcc4daa99d83af588a5cb0a6cc93fa14424193f39047`. Raw public60-byte response hashes/lengths/JSON were recomputed
against the retained local bodies. Normal TLS,20s/no retries/no redirects,
no credentials/signing/AWS. No further blind retries.

The complete verified source/imports/ABI/compiler/settings and deployed-code
binding remain absent. Next: obtain the existing export/request packet above
through the team's own approved source/account contact; no vendor message was
sent here. Guarantees, Keegan review and router check remain NOT_RUN; PR139
stays draft. The independent SR-01 startup fix is in PR176; that code cannot
replace source acquisition or authorize a policy.
