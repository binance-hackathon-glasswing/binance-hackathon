"""#64 item 4 reproduction (IDEA-049-D WR-D4): two OS users share the evidence SQLite store.

Not part of pytest discovery: it creates OS users, so run it as root in a disposable Linux container, e.g.

    git archive 9bfffcd larp | tar -x -C /tmp/old
    docker run --rm --network none -v "$PWD:/repo:ro" -v /tmp/old:/old:ro python:3.12.15-bookworm \\
        python /repo/tests/runtime/proofs/issue64_sqlite_sidecars.py /old old      # the issue's baseline
    docker run --rm --network none -v "$PWD:/repo:ro" python:3.12.15-bookworm \\
        python /repo/tests/runtime/proofs/issue64_sqlite_sidecars.py /repo new     # this tree

`old` = the store at 9bfffcd (WAL writer, mode=ro reader); `new` = this tree (DELETE-journal shared writer,
read-only reader that refuses WAL files; IDEA-047 R15). The directory is 0770 larp-evidence and the runtime user is in
that group, with no systemd sandbox, so the reader has write access to the directory: the issue's premise
(ReadWritePaths at 9bfffcd). It prints a JSON report and exits 1 if any file ends up owned by larp-runtime or the
writer cannot reopen.
"""
import grp, json, os, pwd, shutil, subprocess, sys, time

tree, variant = sys.argv[1], sys.argv[2]
state = '/var/lib/larp-evidence'
for cmd in (['groupadd', '-f', 'larp-evidence'], ['groupadd', '-f', 'larp-runtime']):
    subprocess.run(cmd, check=True)
for user, group, extra in (('larp-evidence', 'larp-evidence', []),
                           ('larp-runtime', 'larp-runtime', ['-G', 'larp-evidence'])):
    if subprocess.run(['id', user], capture_output=True).returncode:
        subprocess.run(['useradd', '-r', '-M', '-g', group, *extra, user], check=True)
ev, rt = pwd.getpwnam('larp-evidence'), pwd.getpwnam('larp-runtime')
egid = grp.getgrnam('larp-evidence').gr_gid
shutil.rmtree(state, ignore_errors=True)
os.makedirs(state)
os.chown(state, ev.pw_uid, egid)
os.chmod(state, 0o770)

PRE = f"import os, sys; sys.path.insert(0, {tree!r})\n"
WRITER = PRE + f"os.setgroups([]); os.setgid({egid}); os.setuid({ev.pw_uid}); os.umask(0o007)\n"
READER = PRE + f"os.setgroups([{egid}]); os.setgid({rt.pw_gid}); os.setuid({rt.pw_uid}); os.umask(0o077)\n"
OPEN_W = ("from larp.sources.store import SQLiteEvidenceStore\n"
          + ("s = SQLiteEvidenceStore(P)\n" if variant == 'old'
             else "s = SQLiteEvidenceStore(P, journal_mode='DELETE')\n"))
COMMIT = ("from larp.contracts import Document\n"
          "v = (s.read_state('ISSUER').read()['version'] if s.read_state('ISSUER') is not None else 0)\n"
          "s.commit(Document.from_dict({'schema': 'EvidenceStateBatch.v1', 'batch_id': 'b%d' % (v + 1), "
          "'issuer_id': 'ISSUER', 'expected_state_version': v, 'state': {'version': v + 1}, 'jobs': []}))\n"
          "print('writer committed version', v + 1)\n")
P = f"P = {state + '/evidence.sqlite'!r}\n"


def run(code, background=False):
    if background:
        return subprocess.Popen([sys.executable, '-c', code], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True)
    r = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, timeout=60)
    return (r.returncode, (r.stdout + r.stderr).strip().splitlines()[-1:] or [''])


def files():
    out = {}
    for name in sorted(os.listdir(state)):
        st = os.stat(os.path.join(state, name))
        out[name] = '%s %o' % (pwd.getpwuid(st.st_uid).pw_name, st.st_mode & 0o777)
    return out


report = {'variant': variant}
report['1_writer_initial'] = run(WRITER + P + OPEN_W + COMMIT + "s.close()\n")
report['1_files_after_writer_close'] = files()
# (i) The runtime opens first after a clean writer close, and stays open while the writer restarts.
reader = run(READER + P + "from larp.sources.store import SQLiteEvidenceStore\nimport time\n"
             "s = SQLiteEvidenceStore(P, read_only=True)\nprint('reader saw', s.read_state('ISSUER').read())\n"
             "time.sleep(4)\nprint('reader done')\n",
             background=True)
time.sleep(1.5)
report['2_files_while_reader_open'] = files()
report['2_writer_restart_while_reader_open'] = run(WRITER + P + OPEN_W + COMMIT + "s.close()\n")
out, _ = reader.communicate(timeout=30)
report['2_reader_output'] = out.strip().splitlines()
report['3_files_after_reader_close'] = files()
report['3_writer_restart_after_reader_close'] = run(WRITER + P + OPEN_W + COMMIT + "s.close()\n")
report['3_files_after'] = files()
if variant == 'new':
    # (iii) The writer dies inside a transaction, leaving its rollback journal; the runtime then opens first.
    report['4_writer_killed_mid_transaction'] = run(
        WRITER + P + OPEN_W + "s.db.execute('BEGIN IMMEDIATE')\n"
        "s.db.execute(\"INSERT INTO estates VALUES('KILLED', 99, randomblob(200000))\")\n"
        "print('files', sorted(os.listdir(os.path.dirname(P))))\nos._exit(9)\n")
    report['4_files_after_kill'] = files()
    report['4_reader_after_kill'] = run(READER + P + "from larp.sources.store import SQLiteEvidenceStore\n"
                                        "s = SQLiteEvidenceStore(P, read_only=True)\n"
                                        "print('reader saw', s.read_state('ISSUER').read())\n")
    report['4_files_after_reader'] = files()
    report['4_writer_recovers'] = run(WRITER + P + OPEN_W + COMMIT
                                      + "print('killed row', s.db.execute(\"SELECT count(*) FROM estates \"\n"
                                      + "                                   \"WHERE issuer_id='KILLED'\").fetchone())\n"
                                      + "s.close()\n")
    report['4_files_final'] = files()
owned = sorted({name for value in report.values() if isinstance(value, dict)
                for name, owner in value.items() if owner.startswith('larp-runtime ')})
writers = [value[0] for key, value in report.items()
           if isinstance(value, tuple) and 'writer' in key and 'killed' not in key]
report['files_ever_owned_by_larp_runtime'] = owned
report['every_writer_open_succeeded'] = all(code == 0 for code in writers)
print(json.dumps(report, indent=1))
sys.exit(0 if not owned and report['every_writer_open_succeeded'] else 1)
