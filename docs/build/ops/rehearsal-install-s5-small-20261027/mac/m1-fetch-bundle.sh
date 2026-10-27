#!/bin/bash
# M1 (Mac, read-only): download the ORIGINAL CI artifact for the run-8 S5 build, verify it, write build.env.
#   [BUILD=<full sha>] bash mac/m1-fetch-bundle.sh <run id> [mirror repo, default Keegan4/Keegan4-larp-ci-mirror]
# BUILD defaults to the canonical head; pin it to the commit Keegan qualified as RC7 if canonical has moved since.
# The qualified mirror runs (RC3, RC3a, RC4) are in Keegan's mirror (PR244 review). Install only this artifact, never a
# local rebuild (LD15). The zip must match GitHub's recorded artifact digest.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
RUN=$1
REPO=${2:-Keegan4/Keegan4-larp-ci-mirror}
BUILD=${BUILD:-$(git -C /Users/songyaozhu/binance-hackathon rev-parse origin/codex/system-testing-20261012)}
# RC7 must contain IDEA-085 (PR257 merge a971685e, RV1 eadd5d4), IDEA-086 (PR262), SJ-11-QV01 (PR268) and S2 (IDEA-089).
git -C /Users/songyaozhu/binance-hackathon merge-base --is-ancestor eadd5d44 "$BUILD" || { echo "BUILD lacks IDEA-085 RV1"; exit 3; }
git -C /Users/songyaozhu/binance-hackathon cat-file -e "$BUILD:larp/marketdata/basis.py" 2>/dev/null || { echo "BUILD lacks IDEA-086 (PR262)"; exit 3; }
# Run 4 also needs the SJ-11-QV01 quote verifier (PR268) and the S2 hours, scope and profile (IDEA-089).
git -C /Users/songyaozhu/binance-hackathon cat-file -e "$BUILD:larp/marketdata/quote_verifier.py" 2>/dev/null || { echo "BUILD lacks SJ-11-QV01 (PR268)"; exit 3; }
git -C /Users/songyaozhu/binance-hackathon grep -q KIT_OPEN_STATE "$BUILD" -- larp/strategy/execution_bounds.py || { echo "BUILD lacks the S2 hours (IDEA-089)"; exit 3; }
# Run 5 also needs the IDEA-097 carry-over and the IDEA-096 allowance recovery (PR282).
git -C /Users/songyaozhu/binance-hackathon grep -q holdings_carry_over "$BUILD" -- larp/strategy/carry_over.py || { echo "BUILD lacks the S4 carry-over (IDEA-097)"; exit 3; }
git -C /Users/songyaozhu/binance-hackathon grep -q allowance_recovery "$BUILD" -- larp/marketdata/quote_verifier.py || { echo "BUILD lacks allowance recovery (IDEA-096)"; exit 3; }
# Run 8 (S5, IDEA-104 R2) also needs FS1's token history (PR295, IDEA-103) required for S5, and the R2 S5 profile.
git -C /Users/songyaozhu/binance-hackathon grep -q larp-s5-rehearsal-v1 "$BUILD" -- larp/marketdata/history.py || { echo "BUILD lacks S5 token history (IDEA-103/104)"; exit 3; }
[[ $(git -C /Users/songyaozhu/binance-hackathon show "$BUILD:docs/build/evidence/s5-rehearsal-profile-20261026/rehearsal-s5.json" | shasum -a 256 | cut -c1-64) == 10882b9a* ]] \
  || { echo "BUILD lacks the run-8 S5 profile 10882b9a (IDEA-104 R3)"; exit 3; }
[[ $(gh run view "$RUN" -R "$REPO" --json headSha -q .headSha) == "$BUILD" ]] || { echo "run is for another commit"; exit 3; }
[[ $(gh run view "$RUN" -R "$REPO" --json conclusion -q .conclusion) == success ]] || { echo "run did not succeed"; exit 3; }
gh run view "$RUN" -R "$REPO" --json jobs -q '.jobs[] | .name + " " + .conclusion'
B=$HERE/bundle; [[ ! -e $B ]] || { echo "bundle/ exists; move it aside first"; exit 3; }
mkdir -p "$B"
read -r AID DIGEST <<<"$(gh api "repos/$REPO/actions/runs/$RUN/artifacts" \
  -q '.artifacts[] | select(.name=="larp-bundle-x86_64") | "\(.id) \(.digest)"')"
[[ -n ${AID:-} && ${DIGEST:-} == sha256:* ]] || { echo "artifact larp-bundle-x86_64 not found"; exit 3; }
gh api "repos/$REPO/actions/artifacts/$AID/zip" > "$B/artifact.zip"
ZIP=$(shasum -a 256 "$B/artifact.zip" | cut -c1-64)
[[ "sha256:$ZIP" == "$DIGEST" ]] || { echo "zip differs from GitHub's artifact digest"; exit 3; }
unzip -q "$B/artifact.zip" -d "$B"
N=larp-${BUILD:0:12}-x86_64
GZ=$(shasum -a 256 "$B/$N.tar.gz" | cut -c1-64)
grep -q "$GZ" "$B/$N.tar.gz.sha256" || { echo "sidecar differs"; exit 3; }
mkdir "$B/x" && tar -xzf "$B/$N.tar.gz" -C "$B/x"
grep -q "^build_id=$BUILD$" "$B/x/$N/BUNDLE.env" || { echo "bundle is for another build"; exit 3; }
(cd "$B/x/$N" && shasum -a 256 -c --quiet SHA256SUMS) || { echo "bundle checksum mismatch"; exit 3; }
cmp -s "$B/$N.release.json" "$B/x/$N/release-manifest.json" || { echo "published manifest differs from the bundle's"; exit 3; }
cat > "$HERE/build.env" <<ENV
BUILD=$BUILD
BUNDLE=$N
BUNDLE_SHA256=$GZ
MANIFEST_SHA256=$(shasum -a 256 "$B/x/$N/release-manifest.json" | cut -c1-64)
PROVISION_SHA256=$(shasum -a 256 "$B/x/$N/provision.sh" | cut -c1-64)
CA_SHA256=$(grep '^rds_ca_sha256=' "$B/x/$N/BUNDLE.env" | cut -d= -f2)
MIRROR_RUN=$REPO/$RUN/artifact-$AID
ENV
cat "$HERE/build.env"
echo "artifact $AID zip sha256 $ZIP"
echo M1_DONE
