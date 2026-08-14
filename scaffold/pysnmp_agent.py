"""Prototype pysnmp agent bridge.

Provides a thin layer to map OIDs to generated handler modules and call
get_<name>/set_<name> functions. When pysnmp is available this module can be
integrated into a live SNMP responder; for testing it exposes handle_get,
handle_set and handle_getnext functions that can be driven directly.
"""
import importlib.util
import os
import logging
import time

# Simple OID -> handler name mapping. Populate as needed at runtime or edit
# this mapping for your generated handlers.
OID_MAP = {
    # '1.3.6.1.4.1.example.1.1': 'myScalar',
}

# Simple ACL map: provide per-OID or per-handler dicts like {'read': True, 'write': True}
# Replace with external policy storage (file/DB/service) in production.
ACL_MAP = {
    # '1.3.6.1.4.1.example.1.1': {'read': True, 'write': True},
    # 'myScalar': {'read': ['public'], 'write': ['admin']},
}

GENERATED_DIR = os.path.join(os.path.dirname(__file__), 'generated_handlers')

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def _check_acl(oid_or_handler, op, ctx):
    """Check ACL_MAP for either OID string or handler name. Conservative default: allow reads, deny writes."""
    entry = ACL_MAP.get(oid_or_handler)
    if entry is None:
        # try handler-name style
        entry = ACL_MAP.get(oid_or_handler)
    # if no explicit entry, default allow GET only
    if not entry:
        return op == 'get'
    # entry can be boolean flags or lists; normalize
    if isinstance(entry.get('read', entry), bool) or isinstance(entry.get('write', entry), bool):
        if op == 'get':
            return bool(entry.get('read', True))
        else:
            return bool(entry.get('write', False))
    # or lists of principals
    principal = None
    if ctx and isinstance(ctx, dict):
        principal = ctx.get('principal') or ctx.get('user')
    allowed = entry.get('read' if op == 'get' else 'write', [])
    if isinstance(allowed, list):
        if principal is None:
            return False
        return principal in allowed
    return False


def load_handler(name, retries=2, backoff=0.05):
    """Dynamically load a generated handler module by name.

    Retries on transient filesystem/import errors to reduce startup flakiness.
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


def _call_flexible(fn, *args):
    """Call fn trying multiple signatures for backwards compatibility.

    Tries: fn(*args), fn(args[1:]) etc. Useful when generated handlers vary.
    """
    try:
        return fn(*args)
    except TypeError:
        try:
            # drop first arg
            return fn(*args[1:])
        except TypeError:
            try:
                return fn()
            except TypeError:
                raise


def handle_get(oid_str, ctx=None):
    """Handle a GET for oid_str and return the Python value from the handler."""
    name = OID_MAP.get(oid_str)
    if not name:
        logger.warning("GET for unmapped OID: %s", oid_str)
        raise KeyError(f'OID not mapped: {oid_str}')
    try:
        mod = load_handler(name)
    except Exception as e:
        logger.exception("Failed to load handler '%s' for OID %s: %s", name, oid_str, e)
        raise
    fn = getattr(mod, f'get_{name}', None)
    if not fn:
        logger.error("Handler '%s' missing get_%s", name, name)
        raise AttributeError(f'get_{name} not found in handler')
    # ACL check using both OID and handler name
    if not (_check_acl(oid_str, 'get', ctx) and _check_acl(name, 'get', ctx)):
        logger.warning("Access denied for principal %s on GET %s", ctx.get('principal') if ctx else None, oid_str)
        raise PermissionError('access denied')
    try:
        # try flexible call (oid, ctx) then (ctx) then ()
        return _call_flexible(fn, oid_str, ctx)
    except Exception:
        logger.exception("Handler '%s' get failed for OID %s", name, oid_str)
        raise


def handle_set(oid_str, value, ctx=None):
    """Handle a SET for oid_str, passing value to the handler."""
    name = OID_MAP.get(oid_str)
    if not name:
        logger.warning("SET for unmapped OID: %s", oid_str)
        raise KeyError(f'OID not mapped: {oid_str}')
    # ACL check using both OID and handler name
    if not (_check_acl(oid_str, 'set', ctx) and _check_acl(name, 'set', ctx)):
        logger.warning("Access denied for principal %s on SET %s", ctx.get('principal') if ctx else None, oid_str)
        raise PermissionError('access denied')
    try:
        mod = load_handler(name)
    except Exception as e:
        logger.exception("Failed to load handler '%s' for OID %s: %s", name, oid_str, e)
        raise
    fn = getattr(mod, f'set_{name}', None)
    if not fn:
        logger.error("Handler '%s' missing set_%s", name, name)
        raise AttributeError(f'set_{name} not found in handler')
    try:
        return _call_flexible(fn, oid_str, value, ctx)
    except Exception:
        logger.exception("Handler '%s' set failed for OID %s with value %r", name, oid_str, value)
        raise


def _oid_to_tuple(oid_str):
    """Convert '1.2.3' -> (1,2,3). Treat empty segments as zero; non-int raises ValueError."""
    try:
        return tuple(int(x) for x in oid_str.strip().split('.') if x != '')
    except Exception:
        raise ValueError(f'Invalid OID string: {oid_str}')


def _sorted_oids():
    """Return OID_MAP keys sorted by numeric OID tuple."""
    try:
        return sorted(OID_MAP.keys(), key=lambda o: _oid_to_tuple(o))
    except Exception:
        # fallback to lexicographic
        logger.exception("Failed numeric sort of OID_MAP keys, falling back to lexicographic")
        return sorted(OID_MAP.keys())


def handle_getnext(oid_str, ctx=None):
    """Handle GETNEXT by returning value for the numerically-next mapped OID.

    This is a best-effort implementation: it selects the next OID in OID_MAP.
    For table semantics, generated handlers may implement next_oid_<name> for finer control.
    """
    logger.debug("GETNEXT request for %s", oid_str)
    try:
        requested = _oid_to_tuple(oid_str)
    except ValueError:
        logger.error("GETNEXT received invalid OID: %s", oid_str)
        raise
    oids = _sorted_oids()
    for candidate in oids:
        try:
            if _oid_to_tuple(candidate) > requested:
                logger.debug("GETNEXT maps %s -> %s", oid_str, candidate)
                # delegate to existing GET handler
                return handle_get(candidate, ctx)
        except Exception:
            logger.exception("Error comparing OIDs %s and %s", candidate, oid_str)
            continue
    logger.debug("No next OID found for %s", oid_str)
    return None


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print('Usage: python pysnmp_agent.py get|set|getnext <oid> [value]')
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
    elif op == 'getnext':
        val = handle_getnext(oid)
        if val is None:
            print('NO_SUCH_OBJECT')
        else:
            print(val)
    else:
        print('unknown op')
        raise SystemExit(2)
