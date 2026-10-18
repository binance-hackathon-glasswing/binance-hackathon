"""Verify downloaded original CI bytes without installing or executing the bundle."""
from pathlib import Path, PurePosixPath
import datetime, hashlib, json, os, tarfile, zipfile

base=Path(os.environ['VERIFICATION_DIR'])
out=base/'release'
build='d8aa7d53e5e27543135f8729ff7a7afd4450278a'
run_id=39111854179
name='larp-'+build[:12]+'-x86_64'
hash_bytes=lambda data:hashlib.sha256(data).hexdigest()
run=json.loads((base/'mirror-run.json').read_bytes())
jobs=json.loads((base/'mirror-jobs.json').read_bytes())['jobs']
artifacts=json.loads((base/'mirror-artifacts.json').read_bytes())['artifacts']
assert run['id']==run_id and run['head_sha']==build and run['conclusion']=='success'
assert len(jobs)==4 and all(j['conclusion']=='success' for j in jobs)
assert {j['name'] for j in jobs}=={'runtime','host-bundle','infrastructure (deploy/aws)','infrastructure (deploy/bootstrap)'}
for job in jobs:
    assert job['steps'] and all(s['conclusion']=='success' for s in job['steps']), job['name']
artifact=next(a for a in artifacts if a['name']=='larp-bundle-x86_64')
assert artifact['workflow_run']['id']==run_id and artifact['workflow_run']['head_sha']==build and not artifact['expired']
raw=(base/'original-ci-artifact.zip').read_bytes()
assert 'sha256:'+hash_bytes(raw)==artifact['digest']
expected={name+'.tar.gz',name+'.tar.gz.sha256',name+'.release.json'}
out.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(base/'original-ci-artifact.zip') as z:
    assert set(z.namelist())==expected, z.namelist()
    for item in z.infolist():
        assert not item.is_dir() and len(PurePosixPath(item.filename).parts)==1
        data=z.read(item)
        path=out/item.filename
        if path.exists(): assert path.read_bytes()==data, 'Refuse replacement of different bytes'
        else: path.write_bytes(data)
bundle=out/(name+'.tar.gz'); external=out/(name+'.release.json')
expected_sha, expected_name=(out/(name+'.tar.gz.sha256')).read_text().strip().split()
assert expected_name==bundle.name and hash_bytes(bundle.read_bytes())==expected_sha
manifest=json.loads(external.read_bytes())
assert manifest['schema']=='ReleaseManifest.v1' and manifest['build_id']==build
assert manifest['repository']=='https://github.com/binance-hackathon-glasswing/binance-hackathon'
assert manifest['build_origin'].removesuffix('.git')=='https://github.com/Keegan4/Keegan4-larp-ci-mirror'
assert manifest['remote_verified'] is True and manifest['registration_evidence'] is None
with tarfile.open(bundle,'r:gz') as t:
    members=t.getmembers()
    assert all((m.isdir() or m.isfile()) and not PurePosixPath(m.name).is_absolute()
               and '..' not in PurePosixPath(m.name).parts for m in members)
    assert all(PurePosixPath(m.name).parts[0]==name for m in members)
    read=lambda relative:t.extractfile(name+'/'+relative).read()
    assert read('release-manifest.json')==external.read_bytes()
    identity=dict(line.split('=',1) for line in read('BUNDLE.env').decode().splitlines())
    assert identity['build_id']==build and identity['arch']=='x86_64' and identity['python_version']=='3.12.15'
    ca=hash_bytes(read('rds-ca.pem'))
    assert ca==identity['rds_ca_sha256']
    assert hash_bytes(read('python/'+identity['python_file']))==identity['python_sha256']
    checksum_rows=[line.split('  ',1) for line in read('SHA256SUMS').decode().splitlines()]
    checksummed={path for _,path in checksum_rows}
    files={m.name[len(name)+1:] for m in members if m.isfile()}
    assert checksummed==files-{'SHA256SUMS'}
    for digest,path in checksum_rows: assert hash_bytes(read(path))==digest, path
    for path,digest in manifest['files'].items():
        assert hash_bytes(read('release/'+path))==digest, path
        assert hashlib.sha256((Path(os.environ['GITHUB_WORKSPACE'])/path).read_bytes()).hexdigest()==digest, path
    assert json.loads(read('release/config/release/services.v1.json'))==manifest['services']
    config=json.loads(read('release/config/intelligence/aiand-routing.openai-preferred.example.json'))
    assert config['schema']=='AIandRouting.v3' and config['openai_model']=='gpt-6.1-sol'
    assert config['openai_effort']=='medium' and all(x['effort']=='high' for x in config['external_reviewers'])
    assert hash_bytes(read('release/larp/intelligence/routing.py'))==manifest['files']['larp/intelligence/routing.py']
    routing_hash=hash_bytes(read('release/config/intelligence/aiand-routing.openai-preferred.example.json'))
    (out/'BUNDLE.env').write_bytes(read('BUNDLE.env'))
report=dict(schema='UnsignedTrialReleaseVerification.v1',verified_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    scope='UNSIGNED_V3_TRIAL_ONLY',build_id=build,mirror_repository='Keegan4/Keegan4-larp-ci-mirror',run_id=run_id,
    run_url=run['html_url'],artifact_id=artifact['id'],artifact_digest=artifact['digest'],all_four_jobs_passed=True,
    bundle=bundle.name,bundle_sha256=expected_sha,bundle_bytes=bundle.stat().st_size,
    manifest=external.name,manifest_sha256=hash_bytes(external.read_bytes()),external_embedded_manifest_equal=True,
    registered_repository=manifest['repository'],build_origin=manifest['build_origin'],
    manifest_file_count=len(manifest['files']),bundle_file_checksums_verified=len(checksum_rows),rds_ca_sha256=ca,
    routing_spec_sha256=routing_hash,bundle_identity=identity,
    jobs=[dict(id=j['id'],name=j['name'],conclusion=j['conclusion'],html_url=j['html_url']) for j in jobs],
    host_deployment_performed=False,paid_provider_calls_performed=False,
    pending=['Yao host/provider identity/funding/rights checks and actual trial-cap enforcement before paid jobs',
             'Yao AWS/host install/bind/activation', 'Gap-report review after Yao supplies it after 19:00 SGT'])
(out/'VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
(base/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
