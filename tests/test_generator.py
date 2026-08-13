import subprocess
import sys

# Simple smoke test: run agentx_demo with generated handlers
import os
cmds = [
    [sys.executable, os.path.join('scaffold','agentx_demo.py'), 'myScalar', 'set', '321'],
    [sys.executable, os.path.join('scaffold','agentx_demo.py'), 'myScalar', 'get']
]
for c in cmds:
    print('RUN:', c)
    p = subprocess.run(c, capture_output=True, text=True)
    print(p.stdout)
    if p.returncode != 0:
        print('ERR:', p.stderr)
        raise SystemExit(1)
print('SMOKE OK')
