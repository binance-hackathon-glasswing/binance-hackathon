"""Bounded JSON-only workers; Linux bubblewrap is mandatory for isolation.

The child sees read-only Python/system libraries and this project's larp package,
an empty environment and scratch /tmp. No home, .env, network or database mounts.
No pickle deserialization is used. Provider workers require separate deployment
capabilities and are not granted credentials by this generic offline runner.
"""

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from larp.contracts import ContractError,Document


class WorkerFailure(ContractError):
    pass


class IsolatedWorker:
    def __init__(self,*,timeout=1,max_bytes=262144,memory_mb=256):
        if timeout<=0 or max_bytes<1 or memory_mb<32:
            raise ValueError('Invalid worker limits')
        self.timeout,self.max_bytes,self.memory_mb=timeout,max_bytes,memory_mb

    def call(self,entrypoint,request):
        if not entrypoint.startswith('larp.') or ':' not in entrypoint:
            raise WorkerFailure('Unregistered worker entrypoint')
        if len(request.payload)>self.max_bytes:
            raise WorkerFailure('Worker request exceeds budget')
        bwrap=shutil.which('bwrap')
        if sys.platform!='linux' or not bwrap:
            raise WorkerFailure('Linux sandbox unavailable; no policy action')
        package=Path(__file__).resolve().parents[1]
        # Resolve venv interpreter but mount the environment prefix too (site libs).
        python=Path(sys.executable).resolve()
        command=[bwrap,'--unshare-all','--die-with-parent','--new-session','--clearenv',
                 '--ro-bind','/usr','/usr','--ro-bind','/lib','/lib']
        if Path('/lib64').exists():
            command+=['--ro-bind','/lib64','/lib64']
        prefix=Path(sys.base_prefix).resolve()
        command+=['--ro-bind',str(prefix),'/python']
        isolated_python='/python/'+str(python.relative_to(prefix))
        command+=['--dir','/app','--ro-bind',str(package),'/app/larp',
                  '--tmpfs','/tmp','--proc','/proc','--dev','/dev','--chdir','/app',
                  isolated_python,'-I','-S','/app/larp/runtime/worker_child.py',entrypoint,
                  str(self.max_bytes),str(self.memory_mb)]
        # Output goes to bounded temporary files rather than unbounded pipes.
        with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
            try:
                result=subprocess.run(command,input=request.payload,stdout=output,stderr=errors,
                                      timeout=self.timeout,env={'PATH':'/usr/bin:/bin'},check=False)
            except (OSError,subprocess.TimeoutExpired):
                raise WorkerFailure('Worker unavailable or deadline exceeded') from None
            if result.returncode:
                raise WorkerFailure('Worker rejected or failed')
            output.seek(0); raw=output.read(self.max_bytes+1)
            if len(raw)>self.max_bytes:
                raise WorkerFailure('Worker output exceeds budget')
            try:
                return Document(raw)
            except ContractError:
                raise WorkerFailure('Invalid worker result') from None


class ServiceLanes:
    """One bounded in-flight task per lane, no shared evidence work queue."""
    def __init__(self):
        from larp.runtime.scheduler import LANES
        self.pools={lane:ThreadPoolExecutor(max_workers=1) for lane in LANES}
        self.futures={}

    def submit(self,lane,operation):
        previous=self.futures.get(lane)
        if previous is not None and not previous.done():
            return False
        self.futures[lane]=self.pools[lane].submit(operation)
        return True

    def close(self):
        for pool in self.pools.values():
            pool.shutdown(wait=True,cancel_futures=True)
