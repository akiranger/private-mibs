import subprocess
import sys
import os

# Simple smoke test: run agentx_demo with generated handlers

def test_agentx_demo_smoke():
    cmds = [
        [sys.executable, os.path.join('scaffold', 'agentx_demo.py'), 'myScalar', 'set', '321'],
        [sys.executable, os.path.join('scaffold', 'agentx_demo.py'), 'myScalar', 'get'],
    ]
    for c in cmds:
        print('RUN:', c)
        p = subprocess.run(c, capture_output=True, text=True)
        print(p.stdout)
        assert p.returncode == 0, f"Command {c} failed: {p.stderr}"
    print('SMOKE OK')
