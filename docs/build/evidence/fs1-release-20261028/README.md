# FS1 release `fs1-4ebf65fe` (2026-10-28, before the F-127 freeze)

[Published assets](https://github.com/binance-hackathon-glasswing/binance-hackathon/releases/tag/fs1-4ebf65fe) /
[machine receipt](release-receipt.json).

Build `4ebf65fe390577d7d77c6c427d3c619423b5fa9f` is the head of `codex/system-testing-20261012` after the FS1 merges
(release branch `release/fs1-4ebf65fe` points at the same commit). Bundle `larp-4ebf65fe3905-x86_64.tar.gz`,
SHA-256 `7b8e504dfdc27e2626e37021b372e76036d28bd3d874f620d469020146c7e10d`; manifest
`e3c190ab7afc79ebadee523c43ce36f2450e1fbbe55f271edb8b4465e71f1c8f`.

What it contains beyond the temp release `e261bcfc`:
- final declarations: 25 FINAL, 0 DRAFT/OPEN; services ACTIVE (IDEA-042 GAP62-F03), so live FS1 activation passes the
  declaration gate;
- PR323 FINAL caps inputs (`tools/deploy/final_caps_inputs.py`, Mac-side preparation);
- PR325 / IDEA-111: no refusal of a swap after its approve (the temp self-check's failure);
- IDEA-112: idle signed safety rounds at most every 120 s (`safety_round_interval_ms` in the prepared runtime).

Pins for preparation: profile `b8ba06e2…`, routing `9b86c732…`, router policy `05759e90…`,
`--model-adoption-ref "IDEA-093 MA-01"`, RDS CA `d7389074…`.

Checks: 256/256 bundle checksums, 217/217 manifest files equal to the commit, register 25/0/0 inside the manifest;
offline Amazon Linux 2023 provisioning PASS twice per role (primary, signer); pinned Linux Python 3.12.15 /
PostgreSQL 14.24 3182 passed / 12 skipped / 0 failed (3 git-dependent tests rerun on a standalone clone, see
receipt); macOS 3181 passed with only the known `test_ar7` probe failing. Not run: real systemd, bubblewrap cases,
hosted CI. Python/wheels/CA are reused from the checksum-verified `e261bcfc` archive with unchanged lockfiles.

Not done here: installation. FS1 deployment follows [the run sheet](../../ops/final-fs1/README.md): retire the
IDEA-110 run, fresh final-wallet Q1/M3 caps, A1 approval, DB1/DB2, install, P6 only at 2026-10-29T02:00Z.
