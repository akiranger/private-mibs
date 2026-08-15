"""
Simple net-snmp pass_persist helper that forwards GET/SET for configured OIDs to generated Python handlers.

This is a pragmatic integration alternative to a full AgentX subagent. Configure snmpd.conf like:

pass_persist .1.3.6.1.4.1.53864 /usr/bin/python3 /path/to/agentx_pass_persist.py /path/to/mapping.json

mapping.json format:
{
  "1.3.6.1.4.1.53864.1.0": "myScalar"
}

Handler module layout (src/deploy/generated_handlers/<name>.py):
- get_<name>(ctx) -> returns string or int
- set_<name>(ctx, value) -> returns True/False or raise

The helper implements a tiny text protocol expected by net-snmp's pass_persist interface:
- on startup, snmpd invokes the program and uses the following exchange:
  - snmpd sends: "PING" -> program replies: "PONG"
  - snmpd sends: "GET <oid>" -> program replies two lines: "<type>" and "<value>" (type is SNMP type name, e.g. INTEGER, STRING)
  - snmpd sends: "SET <oid> <value>" -> program replies: "OK" or "ERROR"

Note: This minimal protocol is compatible with many configurations; for full protocol parity use a proper AgentX subagent.
"""
import sys
import os
import json
import importlib.util
import traceback


def load_mapping(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_handler(name):
    # Load src.deploy.generated_handlers.<name> by file path
    handlers_dir = os.path.join(os.path.dirname(__file__), 'generated_handlers')
    modpath = os.path.join(handlers_dir, f'{name}.py')
    if not os.path.exists(modpath):
        raise FileNotFoundError(modpath)
    fullname = f'src.deploy.generated_handlers.{name}'
    spec = importlib.util.spec_from_file_location(fullname, modpath)
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = 'src.deploy.generated_handlers'
    spec.loader.exec_module(mod)
    sys.modules[fullname] = mod
    return mod


def snmp_type_of(value):
    # Map Python value to a simple SNMP type name
    if isinstance(value, int):
        return 'INTEGER'
    return 'STRING'


def handle_get(oids_map, oid):
    name = oids_map.get(oid)
    if not name:
        return ('NOSUCH', '')
    try:
        mod = load_handler(name)
        fn = getattr(mod, f'get_{name}', None)
        if fn is None:
            return ('NOSUCH', '')
        val = fn(None)
        t = snmp_type_of(val)
        return (t, str(val))
    except Exception as e:
        traceback.print_exc()
        return ('ERROR', str(e))


def handle_set(oids_map, oid, value):
    name = oids_map.get(oid)
    if not name:
        return False, 'NOSUCH'
    try:
        mod = load_handler(name)
        fn = getattr(mod, f'set_{name}', None)
        if fn is None:
            return False, 'NOSUCH'
        res = fn(None, value)
        return True, 'OK' if res is None or res is True else str(res)
    except Exception as e:
        traceback.print_exc()
        return False, str(e)


def repl(oids_map):
    # Simple synchronous stdin/stdout loop
    # Expect commands: PING, GET <oid>, SET <oid> <value>
    try:
        while True:
            line = sys.stdin.readline()
            if not line:
                break
            line = line.strip()
            if line == '':
                continue
            parts = line.split()
            cmd = parts[0].upper()
            if cmd == 'PING':
                print('PONG')
                sys.stdout.flush()
            elif cmd == 'GET' and len(parts) == 2:
                oid = parts[1]
                t, v = handle_get(oids_map, oid)
                # reply type and value lines
                print(t)
                print(v)
                sys.stdout.flush()
            elif cmd == 'SET' and len(parts) >= 3:
                oid = parts[1]
                # rest is value (may contain spaces)
                value = ' '.join(parts[2:])
                ok, msg = handle_set(oids_map, oid, value)
                print(msg if ok else f'ERROR {msg}')
                sys.stdout.flush()
            else:
                # Unknown command — be tolerant
                print('ERROR UnknownCommand')
                sys.stdout.flush()
    except KeyboardInterrupt:
        pass


def main():
    if len(sys.argv) < 2:
        print('Usage: agentx_pass_persist.py <mapping.json>', file=sys.stderr)
        sys.exit(2)
    mapping_path = sys.argv[1]
    if not os.path.exists(mapping_path):
        print(f'Mapping file not found: {mapping_path}', file=sys.stderr)
        sys.exit(1)
    try:
        mapping = load_mapping(mapping_path)
    except Exception as e:
        print(f'Failed to load mapping: {e}', file=sys.stderr)
        sys.exit(1)
    # normalize OIDs: allow leading dot or not
    oids_map = { (k.lstrip('.')): v for k, v in mapping.items() }
    repl(oids_map)


if __name__ == '__main__':
    main()
