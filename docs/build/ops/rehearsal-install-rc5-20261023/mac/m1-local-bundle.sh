#!/bin/bash
# M1-local (Mac): build RC5 locally from the pushed canonical head with tools/build_release_bundle.py (no CI, per Yao
# 2026-10-23, IDEA-049-C SJ-10-A2; same route as SJ-06-A1 and PC-BUILD01), then compare it file by file with the
# CI-built RC4 bundle 270fe81f... (artifact 12419733594) and write build.env. Replaces M1 when mirror CI is skipped.
#   PY=<venv python> RC4=<extracted CI RC4 bundle dir larp-d03bbb16cf51-x86_64> bash mac/m1-local-bundle.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
MAIN=/Users/songyaozhu/binance-hackathon
PY=${PY:?set PY to a Python 3.12 venv built from requirements.lock}
RC4=${RC4:?set RC4 to the extracted CI RC4 bundle directory}
# The reference must be the CI RC4 bundle itself, not SJ-06-A1's superseded local build.
[[ $(shasum -a 256 "$RC4/release-manifest.json" | cut -c1-64) == 5ea11a84* ]] || { echo "RC4 is not the CI RC4 bundle (manifest 5ea11a84...)"; exit 3; }
BUILD=$(git -C "$MAIN" rev-parse origin/codex/system-testing-20261012)
git -C "$MAIN" merge-base --is-ancestor eadd5d44 "$BUILD" || { echo "BUILD lacks IDEA-085 RV1"; exit 3; }
WT=$MAIN/.claude/worktrees/release-${BUILD:0:7}
# The builder refuses a commit that is not the pushed head of its own branch name, so the release checkout is on the
# local branch codex/system-testing-20261012 at BUILD (detach any other worktree that holds that branch first).
[[ -d $WT ]] || git -C "$MAIN" worktree add -B codex/system-testing-20261012 "$WT" "$BUILD" >/dev/null
[[ $(git -C "$WT" rev-parse HEAD) == "$BUILD" && $(git -C "$WT" branch --show-current) == codex/system-testing-20261012 \
   && -z $(git -C "$WT" status --porcelain) ]] || { echo "release checkout not clean canonical $BUILD"; exit 3; }
B=$HERE/bundle; [[ ! -e $B ]] || { echo "bundle/ exists; not overwriting"; exit 3; }
mkdir -p "$B"
(cd "$WT" && "$PY" tools/build_release_bundle.py --arch x86_64 --out "$B")
N=larp-${BUILD:0:12}-x86_64
GZ=$(shasum -a 256 "$B/$N.tar.gz" | cut -c1-64)
grep -q "$GZ" "$B/$N.tar.gz.sha256" || { echo "sidecar differs"; exit 3; }
mkdir "$B/x" && tar -xzf "$B/$N.tar.gz" -C "$B/x"
X=$B/x/$N
grep -q "^build_id=$BUILD$" "$X/BUNDLE.env" || { echo "bundle is for another build"; exit 3; }
(cd "$X" && shasum -a 256 -c --quiet SHA256SUMS) || { echo "bundle checksum mismatch"; exit 3; }
cmp -s "$B/$N.release.json" "$X/release-manifest.json" || { echo "published manifest differs from the bundle's"; exit 3; }
# Every file other than the manifest, BUNDLE.env and SHA256SUMS must match CI RC4 except release files the commits
# d03bbb1..BUILD changed (expected: release/larp/runtime/database.py and release/larp/storage/postgres.py).
CHANGED=$(git -C "$WT" diff --name-only d03bbb16cf51277c73d7f381b08f9551d0c10415 "$BUILD" | sed 's#^#release/#')
DIFF=$( (cd "$X" && find . -type f ! -name SHA256SUMS ! -name BUNDLE.env ! -name release-manifest.json | sort) | while read -r f; do
  f=${f#./}
  if [[ ! -f $RC4/$f ]]; then echo "NEW $f"; elif ! cmp -s "$X/$f" "$RC4/$f"; then echo "CHANGED $f"; fi
done)
GONE=$( (cd "$RC4" && find . -type f ! -name SHA256SUMS ! -name BUNDLE.env ! -name release-manifest.json | sort) | while read -r f; do
  f=${f#./}; [[ -f $X/$f ]] || echo "REMOVED $f"; done)
echo "$DIFF$GONE" | sed '/^$/d'
UNEXPECTED=$(echo "$DIFF$GONE" | sed '/^$/d' | awk '{print $2}' | grep -v -x -F "$CHANGED" || true)
[[ -z $UNEXPECTED ]] || { echo "unexpected differences from CI RC4:"; echo "$UNEXPECTED"; exit 3; }
diff <(grep -v '^build_id=' "$RC4/BUNDLE.env") <(grep -v '^build_id=' "$X/BUNDLE.env") || { echo "BUNDLE.env differs beyond build_id"; exit 3; }
cat > "$HERE/build.env" <<ENV
BUILD=$BUILD
BUNDLE=$N
BUNDLE_SHA256=$GZ
MANIFEST_SHA256=$(shasum -a 256 "$X/release-manifest.json" | cut -c1-64)
PROVISION_SHA256=$(shasum -a 256 "$X/provision.sh" | cut -c1-64)
CA_SHA256=$(grep '^rds_ca_sha256=' "$X/BUNDLE.env" | cut -d= -f2)
MIRROR_RUN=LOCAL-BUILD-SJ-10-A2
ENV
cat "$HERE/build.env"
echo M1_DONE
