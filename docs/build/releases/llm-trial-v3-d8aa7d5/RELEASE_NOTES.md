Unsigned OpenAI-primary LLM v3 trial release from the reviewed integration branch, including merged PR167 and PR165 plus the KMP-P2 dispatch-cutoff fix. OpenAI GPT-6.1 Sol medium is primary; AIand Kimi K3 high then GLM-5.3 high supplies independent review/fallback. Yao-approved PR168 protocol and blind-label rubric apply.

Frozen source: `d8aa7d53e5e27543135f8729ff7a7afd4450278a`.
CI mirror: `Keegan4/Keegan4-larp-ci-mirror`.
Run: [39111854179](https://github.com/Keegan4/Keegan4-larp-ci-mirror/actions/runs/39111854179).

The tar.gz, sha256 sidecar and release.json are the original CI-produced deployment files. They have been downloaded and independently verified without rebuilding. This release supersedes7a0ea14 for the new v3 trial; the old documentation handoff ZIP is not this binary.

| Verified item | SHA-256 |
|---|---|
| Original deployment bundle | `9930f361dce63480ec1966082b2ca0d0e4360ad1512b35a9eca57ef00bd90b89` |
| External and embedded manifest | `8bed25395fa23947f93193f2eb48acfbf1091e8b0ad3aa37ca4cafc899b149e0` |
| Packaged RDS CA | `d73890748b5a95551800df8a6f07c9c800e32ed34da7e6c9505918bf8ac2398b` |


Private mirror CI: **4/4 jobs green**. Linux/Python3.12.15/PostgreSQL14.24: **2029 passed,6 skipped,2981 subtests**; separate actual-systemd run **5 passed/5 subtests**. Both Terraform jobs, offline demo, restricted Docker smoke and both-role bundle provisioning pass. The remaining opt-in skip is the external corpus; five systemd skips in the full run are exercised separately.

Original verification includes the Actions artifact ZIP digest, tarball sidecar, matching embedded/external manifest, all manifested files and bundle file checksums, registered repository, mirror build_origin, BUNDLE.env and included RDS CA. VERIFICATION.json records the evidence.

Scope: unsigned trial only. The v3 protocol uses full US$50 pacing including US$2 owner-reported prior spend with zero permanent reserve. Yao retains AWS/host provisioning, installation/binding/activation, actual provider/funding/rights checks and in-flight enforcement of the US$8 trial / US$2.50 UTC-day stops before paid work. No host deployment or paid provider call was performed by the release agent. Signed/scored adoption remains separate. PR133 and PR126 stay open.

PC-AWS06 existing migration/primary-role/TLS evidence was reviewed with its limits; gap-report review remains pending until Yao supplies the fixed-window report after Oct18 19:00 SGT. That pending report did not delay building this bundle.
