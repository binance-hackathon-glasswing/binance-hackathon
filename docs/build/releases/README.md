# Sendable release handoff

`larp-7a0ea14-handoff.zip` is the sendable handoff folder for the accepted unsigned
LLM shadow-trial release. **It does not contain the original CI deployment
binary.** The included fetch/verification helper requires access to the private
CI mirror, or the original archive/manifest/sidecar from the host owner.

The ZIP and its checksum are stored on this separate branch because the cloud
session can create GitHub release metadata but `uploads.github.com` rejects its
asset-upload authentication with HTTP401. The GitHub prerelease links these exact
committed files instead of claiming they are uploaded release assets.

The release tag points to the original accepted build7a0ea14. This branch and
handoff documentation do not replace or rebuild its deployment bytes. No
credentials, host configs, model calls, installation or signing are included.
