"""Build the dashboard Lambda's deployment package (IDEA-091).

  python -m tools.dashboard.aws.package --out <zip>

Only the files the handler needs, at their repository paths, with fixed timestamps and modes so the same commit
always gives the same bytes (the Terraform `source_code_hash`). The AWS SDK comes from the Lambda runtime. `.git` is an
empty marker: the RC7 chain monitor finds the repository root as the folder holding both `larp/` and `.git`.
"""
import argparse
import hashlib
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[3]
FILES = (
    'tools/dashboard/aws/handler.py', 'tools/dashboard/build.py', 'tools/dashboard/decisions.py',
    'tools/dashboard/refresh.py', 'tools/dashboard/template.html', 'tools/dashboard/decisions-export.sh',
    'tools/dashboard/tx-export.sh', 'docs/build/ops/rehearsal-install-rc7-20261024/mac/chain-monitor.py',
    'larp/__init__.py', 'larp/contracts.py', 'larp/marketdata/__init__.py', 'larp/marketdata/web3.py',
)
MARKERS = ('.git',)
STAMP = (2026, 1, 1, 0, 0, 0)


def entry(name):
    info = zipfile.ZipInfo(name, STAMP)
    info.external_attr = 0o644 << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    return info


def package(out, root=ROOT):
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, 'w') as z:
        for name in sorted(FILES + MARKERS):
            z.writestr(entry(name), b'' if name in MARKERS else (Path(root) / name).read_bytes())
    return hashlib.sha256(out.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', required=True)
    print(package(ap.parse_args().out))


if __name__ == '__main__':
    main()
