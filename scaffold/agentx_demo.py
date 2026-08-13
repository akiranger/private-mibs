"""
Simple demo harness that simulates AgentX invoking generated handler functions.
Usage:
  python agentx_demo.py <name> get
  python agentx_demo.py <name> set <value>
"""
import sys
import importlib
import os

# Ensure repo root is on sys.path so 'scaffold' package imports resolve even when executing from scaffold/
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

if len(sys.argv) < 3:
    print('Usage: python agentx_demo.py <name> get|set [value]')
    sys.exit(2)

name = sys.argv[1]
op = sys.argv[2]

# Ensure scaffold package is importable
try:
    import scaffold
    import scaffold.persistence
except Exception as e:
    print('Failed to import scaffold package:', e)
    # continue, it may still work when loading module

# Load handler module by file path from generated_handlers directory
handlers_dir = os.path.join(os.path.dirname(__file__), 'generated_handlers')
modpath = os.path.join(handlers_dir, f'{name}.py')
if not os.path.exists(modpath):
    print(f'Handler file not found: {modpath}')
    sys.exit(1)

import importlib.util
fullname = f'scaffold.generated_handlers.{name}'
spec = importlib.util.spec_from_file_location(fullname, modpath)
mod = importlib.util.module_from_spec(spec)
# ensure parent package is set so relative imports resolve
mod.__package__ = 'scaffold.generated_handlers'
try:
    spec.loader.exec_module(mod)
    import sys as _sys
    _sys.modules[fullname] = mod
except Exception as e:
    print(f'Failed to load module from {modpath}: {e}')
    sys.exit(1)

if op == 'get':
    func_name = f'get_{name}'
    fn = getattr(mod, func_name, None)
    if not fn:
        print(f'Handler {func_name} not found in {module_name}')
        sys.exit(1)
    res = fn(None)
    print('GET result:', res)
elif op == 'set':
    if len(sys.argv) < 4:
        print('set requires a value')
        sys.exit(2)
    value = sys.argv[3]
    func_name = f'set_{name}'
    fn = getattr(mod, func_name, None)
    if not fn:
        print(f'Handler {func_name} not found in {module_name}')
        sys.exit(1)
    fn(None, value)
    print('SET invoked')
else:
    print('Unknown op', op)
    sys.exit(2)
