# Model-provider licence register — KMP-RIGHTS01

Keith, 2026-10-18 UTC; Keegan reviews before adoption. This is the model-provider
register alongside the ingestion rights in `config/sources/sources.v1.json`.
It does not enable a new data source or approve a signed release.

Public anonymous captures are indexed in
[provider-terms-manifest.json](evidence/model-prerequisites-20261018/provider-terms-manifest.json).
Raw bytes and rendered-source transcripts are retained outside Git at
`/private/tmp/larp-keith-prerequisites-20261018/provider-terms/` on Keith's Mac.
The manifest records exact URL, UTC capture, status, bytes and SHA-256. Raw403
responses are NOT_QUALIFIED. The relevant current OpenAI policy passages were separately
captured through `web.open`; its transcript is explicitly distinguished from
raw HTTP; these passages are not guaranteed complete page bodies. The downloaded agreement PDF is supplemental; equivalence to the
current HTML has not been established. Preserve these captures in the team's
durable private evidence store before release; a local temp path is not an
archival-retention guarantee.

An additional private copy was transferred to Keith's server at
`/home/keith/larp-interim-summaries/model-provider-terms-20261018.tar.gz`, mode0600.
Both ends verified SHA-256
`f3841ad79cab79d0de3b6fdb81e10e4324db6feefc3ef64f83aa4df1b24bccf3`
(469,863 bytes). The public capture manifest's file SHA is
`e7daa905e7fb2613d8b215bb0408ec1e321dcabe06051b18fd8ec2026a999dde`.
This preserves the actual bytes beyond the local temp copy; release-owner
retention/access/backup qualification remains separate.

## Submission, retention and sharing

| Provider / checked clauses | Public filings as input | Customer retention and audit sharing | Provider retention / qualification |
|---|---|---|---|
| [AIand inference terms](https://www.aiand.com/legal/inference-terms-of-service), effective July6 2026, A2/B1–5/C2–3/D2–3/E | API inference is offered, but customer must have rights to inputs; public availability alone grants no third-party rights. Incorporated exact model licences control on conflict. | Customer retains input rights and owns outputs subject to law/model terms. Inference: retaining its own lawful prompts/results and disclosing them to competition auditors is compatible with these clauses; exclude provider secrets/credentials and preserve source/licence notices. This is not an independent source licence. | No training on customer content; limited service/security/legal use; Japan processing with listed exceptions; default production retention up to30 days, subject to terms/law exceptions. Account/order-form differences unverified. |
| [OpenAI Services Agreement](https://openai.com/policies/services-agreement/), effective Jan1 2026, §§3.3/4/7/16.2; [Service Terms](https://openai.com/policies/service-terms/), updated Oct16 2026, §1 | Customer must hold input rights and follow incorporated policies; API application use is contemplated. Do not submit private labels, credentials or unlicensed extracts. | Customer retains input rights/owns output to the extent allowed by law. Inference: these support retaining and sharing the customer's lawful model-I/O audit record, subject to policies/source rights; not provider confidential information. The API output-indemnity clause is not a blanket third-party-rights clearance. | Account-specific agreement/order form and applicable policy precedence remain unverified. See data-control row for actual retention; ownership does not mean provider zero retention. |
| [OpenAI API data controls](https://developers.openai.com/api/docs/guides/your-data) | API content is not used for training by default, unless the customer opts in. | Keep the team's own complete prompt/input/reasoning-summary/output/stage records; provider storage is not the audit archive. No entitlement to inaccessible internal model reasoning is implied. | Ordinary abuse-monitoring logs can retain content up to30 days, with exceptions. Responses application state is stored by default; our reviewed provider sends `store:false`, which does not itself eliminate abuse-monitoring retention. No Zero Data Retention/account setting was verified. |
| [AIand DPA](https://www.aiand.com/legal/dpa), §§8–10 | Personal data still needs its own lawful basis; do not assume all filing contents are personal-data-free. | Its audit provisions govern auditing the provider, not a right to publish provider confidential records. They do not replace the customer's own competition audit record. | Production deletion default30 days with legal-process exceptions; backups can retain data subject to restrictions. Japan residency has subprocessor/order/consent/legal exceptions. |

The rights analysis is a scoped reading of public terms, not confirmation of
the account's negotiated contract or every submitted document's licence.

## Incorporated model licences and policies

- [Kimi K3 exact publisher licence](https://huggingface.co/moonshotai/Kimi-K3/blob/main/LICENSE),
  captured SHA `20c797ce19af0c17de52c6afb144644768a591c521655f5ebf5712c9850f2887`:
  custom licence, not MIT. Software copies/substantial portions require notices.
  Model-as-a-Service commercial-use/revenue and large-product attribution
  conditions have stated thresholds/exceptions. LARP's embedded assessment
  harness is not providing end users general inference control; auditor access
  to outputs should not be labelled “internal only” to bypass licence conditions.
  No weights/code are redistributed in the planned audit. Confirm that AIand
  serves this exact model under these terms and whether an account override applies.
- [GLM-5.3 exact publisher licence](https://huggingface.co/zai-org/GLM-5.3/blob/main/LICENSE),
  captured SHA `96e1622099fc9d6b70c9760f007d99e66d7497eec636b63c60fe208401e9170c`:
  custom licence, not an assumed Apache/MIT licence. Software-copy notices and
  law compliance apply; the defined high-revenue Model-as-a-Service use requires
  Z.AI security review. Embedded feature/request relaying are excluded from that
  definition. No weight redistribution is proposed. Confirm applicability with
  the exact AIand model/account; do not substitute another GLM version's licence.
- [AIand usage policy](https://www.aiand.com/legal/usage-policy), July6/revised
  Aug21 2026: retain verification/disclosure and legal safeguards; do not use
  output to train competing models. This comparison evaluates the LARP harness,
  not training a competing foundation model. [Supported regions](https://www.aiand.com/legal/supported-regions),
  Aug21 2026, includes Australia and Singapore; account/provider availability
  still needs the actual P0 identity/effort check. No region bypass is proposed.
- [OpenAI Sharing & Publication Policy](https://openai.com/policies/sharing-publication-policy/),
  updated Nov14 2022: public demonstrations/sharing require review, attribution
  and clear AI disclosure. Keep an audit index identifying model/stage/build,
  verification status and source attribution. Private auditor access is the
  planned use; public publication needs its own review of the applicable policy.
- [OpenAI Usage Policies](https://openai.com/policies/usage-policies/), effective
  Oct29 2025: automated high-stakes decisions in financial activities without
  human review are restricted. The unsigned evidence trial does not sign trades.
  **Signed/scored compatibility remains a concrete adoption question** because
  the intended scored system cannot rely on discretionary human intervention.
  Keegan must resolve whether the scoped evidence-extraction/reduce-only use and
  autonomous controls satisfy the applicable account terms; if not established,
  obtain provider clarification or select a compatible route before signed use.
  Do not treat the competition's permission as provider permission. No claim is
  made that this clause either bans all trading or approves this deployment.

Source rights stay document-specific: consult existing source-register exclusions
for issuer/third-party filings, images, attachments and incorporated material.
Neither model contract grants a licence to every public filing or press release.

## Evidence and remaining owner checks

Captures include AIand inference/DPA/usage/regions, public catalogue/pricing/models,
both exact publisher licences, OpenAI data/model documentation and the rendered
current agreement/service/usage/sharing policies. Each inaccessible raw page is
preserved as a failed capture rather than counted as a successful one.

AIand's public models endpoint currently advertises `moonshotai/kimi-k3` high
and `zai-org/glm-5.3` high; this is anonymous catalogue evidence, not account access.
Neither the owner-reported “140+” nor catalogue prices establish account currency,
current funding, negotiated rates, retention settings or affordability.

Remaining: Keegan reviews the register, resolves signed-policy compatibility and
account-contract/model-term applicability; Yao verifies account P0/region/settings
and privately archives captures with access/retention controls. Keith completes
measured funding from the usage export. GAP-23/source/host/adoption gates remain
open where these checks are missing. No terms were accepted or account settings
changed by this capture.
