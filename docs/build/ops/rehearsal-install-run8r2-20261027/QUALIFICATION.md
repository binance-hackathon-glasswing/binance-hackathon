# Release qualification receipt and remaining checks

The runtime source is fixed at a22527603ad34c545ff30b5ef996f575b3435b53. Python3.12.15 came from the delivered
bundle's checksum-pinned standalone interpreter; tests used deploy/requirements-test.lock and the exact PostgreSQL
image digest in .github/workflows/runtime.yml. pip check passed. All256 bundle member checksums passed.

- Full pytest: **3056 passed,7 skipped,4124 subtests passed,3 failed** in960.12seconds.
- Three failures are environment-dependent and remain failures in the retained result: AR7 cannot write
  /proc/self/clear_refs; two real-bubblewrap worker tests cannot set up the uid namespace here (read-only filesystem).
- The separate operator package tests: **5 passed** (archive corruption, unsafe links, wrong build, checksums,
  fast SSM AccessDenied refusal).
- Both primary and signer offline AL2023 bundle provisioning checks passed, including repeat installation,
  permissions, entrypoints, key-loader boundary and bound-manifest preflight. Provisioning ran without network.
  Only the container build's proxy CA mount/dnf TLS trust was adapted; the provisioning assertions were unchanged.
- Actual operator staging passed against the delivered original bundle and fixed source checkout.
- The offline demo was attempted and failed to produce its entry record under the isolated-worker restriction.
- Real-systemd tests were not run because PID1 is not systemd. No live provider, wallet or hosted run check is claimed.

## Yao's remaining qualification gate

On a disposable supported Linux runner (not an active trading host), check out the fixed source and follow its
.github/workflows/runtime.yml, with Python3.12.15, deploy/requirements-test.lock, exact pinned PostgreSQL and
bubblewrap. Use a disposable LARP_TEST_DATABASE_URL, then run:

```bash
python -m pip check
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q -p no:cacheprovider
LARP_TEST_SYSTEMD=1 python -m pytest -q tests/runtime/test_systemd_conditions.py -p no:cacheprovider
python -m larp.runtime.demo > offline-trace.json
bash tools/test_host_bundle.sh PATH_TO_DELIVERED_BUNDLE
```

The systemd cases need a runner with real systemd as PID1 and the test's normal unit-management permissions.
Keep original failure history; do not weaken assertions, replace bubblewrap with an unsandboxed worker, or mark
skipped/failed gates passed. This package is prepared for operator review and qualification, not certified for launch.
