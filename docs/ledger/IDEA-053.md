### IDEA-053 — Local CI: run the `runtime.yml` jobs on a developer machine
- Date / author: 2026-10-15 SGT / Yao Zhu with Claude Code
- Status: open (pass criteria written before the script exists)
- What: `tools/local_ci.sh` runs the three jobs of `.github/workflows/runtime.yml` on a developer Mac with Docker: `infrastructure`, `runtime` and `host-bundle`. It prints one PASS, FAIL or NOT RUN line per job, and it exits non-zero if any job fails.
- Why it might help: the team reports that the organisation's GitHub Actions usage has reached its limit (2026-10-15). PRs and ledger results have so far cited hosted "Linux CI" runs as acceptance evidence. Without hosted runs, a scripted local run is the closest substitute, and it must state its own gaps.
- Cost / risk: Docker Desktop and internet access are needed (images, wheels, the python-build-standalone download, the RDS CA). The script contacts no AWS account and reads no secrets. Local results are **not** the same evidence as a hosted run; the differences are listed below and printed on every run.
- Links: `.github/workflows/runtime.yml`; IDEA-045 H05 (pinned local Terraform); IDEA-047 H01/H02, R6, R13 (host bundle, bundle hash, real-systemd test).

## Design
| `runtime.yml` step | Local equivalent | Difference |
|---|---|---|
| `infrastructure`: checksum-pinned Terraform 1.13.5; `fmt -check -recursive`, `init -backend=false -input=false -lockfile=readonly`, `validate`, `test`, for `deploy/aws` and `deploy/bootstrap` | The same commands, with the binary installed by IDEA-045 H05 (`~/.local/opt/terraform-1.13.5/terraform`, or `$TERRAFORM`), on a disposable copy of the tracked tree | darwin_arm64 binary instead of linux_amd64; the lock files carry both hashes (IDEA-045) |
| `runtime`: PostgreSQL 14.24 service (same digest), Python 3.12.15, bubblewrap, `pip install -r deploy/requirements-test.lock`, `pip check`, `pytest -q -p no:cacheprovider` | The same Postgres image on a private Docker network. The tests run in `python:3.12.15-slim-bookworm` (the Dockerfile's pinned digest) with bubblewrap installed, on the committed tree from `git archive HEAD` | Debian bookworm instead of Ubuntu 22.04; arm64 instead of x86_64; the container runs `--privileged` so bubblewrap can create namespaces |
| `runtime`: `LARP_TEST_SYSTEMD=1 pytest tests/runtime/test_systemd_conditions.py` | **NOT RUN.** It needs a disposable host with real systemd and passwordless sudo | Gap |
| `runtime`: `python -m larp.runtime.demo` | The same command, in the same container | — |
| `runtime`: `docker build -f deploy/Dockerfile`, then `docker run --rm --network none --read-only --cap-drop ALL` | The same, with the committed tree as the build context | arm64 image |
| `host-bundle`: `tools/build_release_bundle.py --arch x86_64`, the hash summary, the artifact upload, `tools/test_host_bundle.sh` | The build and the test (`linux/amd64`, emulated). The bundle and its SHA-256 are kept in a local output directory | No artifact is uploaded, so the activation pack needs the hosted artifact or a recorded local hash. The builder refuses a HEAD that is not the pushed branch head, as in CI |

## Pass criteria (written and committed before the script exists)
1. **Mirror.** Every step of `runtime.yml` at this branch's base is either run, or printed as NOT RUN with its reason. No step is silently dropped.
2. **Green on the base.** On a clean, pushed HEAD of this branch, the script reports PASS for `infrastructure`, `runtime` and `host-bundle`. The pytest summary line is recorded here. Any test that fails locally but passes in hosted CI is explained, not hidden.
3. **Failure detected.** A run with a broken input (`TERRAFORM=/usr/bin/false`) reports FAIL for `infrastructure` and exits non-zero.
4. **No side effects.**
   - The developer's checkout is not modified, apart from the output directory, which is git-ignored or outside the repository.
   - The script's containers and network are removed when it exits, on failure too.
   - It contacts no AWS account and uses no credentials.
5. **Static checks.** `bash -n` passes, and `shellcheck` passes if it is installed.

## Results
