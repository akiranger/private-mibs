"""Prototype pysnmp agent bridge.

Provides a thin layer to map OIDs to generated handler modules and call
get_<name>/set_<name> functions. When pysnmp is available this module can be
integrated into a live SNMP responder; for testing it exposes handle_get and
handle_set functions that can be driven directly.
"""
import importlib.util
import os
import logging
import time

logger = logging.getLogger(__name__)
if not logger.handlers:
    # conservative basic config for CLI/debug runs; applications can reconfigure logging
    logging.basicConfig(level=logging.INFO)

# Simple OID -> handler name mapping. Populate as needed at runtime or edit
# this mapping for your generated handlers.
OID_MAP = {
    # '1.3.6.1.4.1.example.1.1': 'myScalar',
}

# Simple ACL map: provide per-OID dicts like {'read': True, 'write': False}
# Replace with external policy storage (file/DB/service) in production.
ACL_MAP = {
    # '1.3.6.1.4.1.example.1.1': {'read': True, 'write': True},
}

GENERATED_DIR = os.path.join(os.path.dirname(__file__), 'generated_handlers')


def load_handler(name, retries=2, backoff=0.05):
    """Dynamically load a generated handler module by name.

    Retries once on transient filesystem/import errors to reduce startup flakiness.
    """
    modpath = os.path.join(GENERATED_DIR, f'{name}.py')
    if not os.path.exists(modpath):
        raise FileNotFoundError(modpath)
    fullname = f'scaffold.generated_handlers.{name}'
    spec = importlib.util.spec_from_file_location(fullname, modpath)
    mod = importlib.util.module_from_spec(spec)
    # set package so relative imports in generated modules resolve
    mod.__package__ = 'scaffold.generated_handlers'
    import sys
    # reuse cached module if already loaded so module-level state persists
    if fullname in sys.modules:
        return sys.modules[fullname]

    attempts = 0
    while True:
        try:
            spec.loader.exec_module(mod)
            sys.modules[fullname] = mod
            return mod
        except Exception as e:
            attempts += 1
            logger.exception('failed loading handler %s (attempt %d): %s', name, attempts, e)
            if attempts > retries:
                raise
            time.sleep(backoff * attempts)


def handle_get(oid_str, ctx=None):
    """Handle a GET for oid_str and return the Python value from the handler.

    Errors from handlers are logged and re-raised so callers can decide an SNMP error code.
    """
    try:
        name = OID_MAP.get(oid_str)
        if not name:
            raise KeyError(f'OID not mapped: {oid_str}')
        mod = load_handler(name)
        fn = getattr(mod, f'get_{name}', None)
        if not fn:
            raise AttributeError(f'get_{name} not found in handler')
        # handler signature: get_<name>(oid=None, ctx=None)
        return fn(oid_str, ctx)
    except Exception:
        logger.exception('handle_get failed for %s', oid_str)
        # Reraise to let caller decide SNMP error handling, but keep agent alive
        raise


def handle_set(oid_str, value, ctx=None):
    """Handle a SET for oid_str, passing value to the handler."""
    try:
        name = OID_MAP.get(oid_str)
        if not name:
            raise KeyError(f'OID not mapped: {oid_str}')
        # ACL check
        acl = ACL_MAP.get(oid_str)
        if acl is not None and not acl.get('write', False):
            raise PermissionError(f'write denied for {oid_str}')
        mod = load_handler(name)
        fn = getattr(mod, f'set_{name}', None)
        if not fn:
            raise AttributeError(f'set_{name} not found in handler')
        # handler signature: set_<name>(oid, value, ctx=None)
        return fn(oid_str, value, ctx)
    except Exception:
        logger.exception('handle_set failed for %s with value %r', oid_str, value)
        # Reraise so caller can convert to an appropriate SNMP error response
        raise


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print('Usage: python pysnmp_agent.py get|set <oid> [value]')
        raise SystemExit(2)
    op = sys.argv[1]
    oid = sys.argv[2]
    if op == 'get':
        print(handle_get(oid))
    elif op == 'set':
        if len(sys.argv) < 4:
            print('set requires a value')
            raise SystemExit(2)
        handle_set(oid, sys.argv[3])
        print('OK')
    else:
        print('unknown op')
        raise SystemExit(2)
