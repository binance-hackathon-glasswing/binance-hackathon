#!/bin/bash
# M1-local (Mac): build the bundle locally from the pushed canonical head with tools/build_release_bundle.py (no CI,
# per Yao 2026-10-22; same route as PC-BUILD01), then compare it file by file with the CI-built RC3a bundle and write
# build.env. Replaces M1 when mirror CI is skipped (IDEA-049-C SJ-06-A1).
#   PY=<venv python> RC3A=<extracted RC3a bundle dir larp-fa1b6c966f18-x86_64> bash mac/m1-local-bundle.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
MAIN=/Users/songyaozhu/binance-hackathon
PY=${PY:?set PY to a Python 3.12 venv built from requirements.lock}
RC3A=${RC3A:?set RC3A to the extracted CI RC3a bundle directory}
BUILD=$(git -C "$MAIN" rev-parse origin/codex/system-testing-20261012)
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
# Every file other than the manifest, BUNDLE.env and SHA256SUMS must match RC3a except release files the commits
# fa1b6c9..BUILD changed.
CHANGED=$(git -C "$WT" diff --name-only fa1b6c966f186103c8dfaee5438e0d00e4edec9a "$BUILD" | sed 's#^#release/#')
DIFF=$( (cd "$X" && find . -type f ! -name SHA256SUMS ! -name BUNDLE.env ! -name release-manifest.json | sort) | while read -r f; do
  f=${f#./}
  if [[ ! -f $RC3A/$f ]]; then echo "NEW $f"; elif ! cmp -s "$X/$f" "$RC3A/$f"; then echo "CHANGED $f"; fi
done)
GONE=$( (cd "$RC3A" && find . -type f ! -name SHA256SUMS ! -name BUNDLE.env ! -name release-manifest.json | sort) | while read -r f; do
  f=${f#./}; [[ -f $X/$f ]] || echo "REMOVED $f"; done)
echo "$DIFF$GONE" | sed '/^$/d'
UNEXPECTED=$(echo "$DIFF$GONE" | sed '/^$/d' | awk '{print $2}' | grep -v -x -F "$CHANGED" || true)
[[ -z $UNEXPECTED ]] || { echo "unexpected differences from RC3a:"; echo "$UNEXPECTED"; exit 3; }
diff <(grep -v '^build_id=' "$RC3A/BUNDLE.env") <(grep -v '^build_id=' "$X/BUNDLE.env") || { echo "BUNDLE.env differs beyond build_id"; exit 3; }
cat > "$HERE/build.env" <<ENV
BUILD=$BUILD
BUNDLE=$N
BUNDLE_SHA256=$GZ
MANIFEST_SHA256=$(shasum -a 256 "$X/release-manifest.json" | cut -c1-64)
PROVISION_SHA256=$(shasum -a 256 "$X/provision.sh" | cut -c1-64)
CA_SHA256=$(grep '^rds_ca_sha256=' "$X/BUNDLE.env" | cut -d= -f2)
MIRROR_RUN=LOCAL-BUILD-SJ-06-A1
ENV
cat "$HERE/build.env"
echo M1_DONE
