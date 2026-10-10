"""Internal sandbox entrypoint. Only JSON crosses the boundary."""

import importlib
import resource
import sys


def main():
    entrypoint,limit,memory=sys.argv[1:]
    limit,memory=int(limit),int(memory)
    resource.setrlimit(resource.RLIMIT_AS,(memory*1024*1024,memory*1024*1024))
    resource.setrlimit(resource.RLIMIT_FSIZE,(limit,limit))
    resource.setrlimit(resource.RLIMIT_CPU,(2,2))
    resource.setrlimit(resource.RLIMIT_NOFILE,(32,32))
    resource.setrlimit(resource.RLIMIT_NPROC,(0,0))
    sys.path.insert(0,'/app')
    from larp.contracts import Document
    raw=sys.stdin.buffer.read(limit+1)
    if len(raw)>limit:
        raise ValueError('Input too large')
    module,name=entrypoint.split(':',1)
    result=getattr(importlib.import_module(module),name)(Document(raw))
    if type(result) is not Document or len(result.payload)>limit:
        raise ValueError('Invalid output')
    sys.stdout.buffer.write(result.payload)


if __name__=='__main__':
    main()
