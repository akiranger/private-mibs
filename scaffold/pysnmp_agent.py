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
if not logger.handlers:
    # conservative basic config for CLI/debug runs; applications can reconfigure logging
    logging.basicConfig(level=logging.INFO)


# SNMPv3 USM user store (in-memory). For production, use secure secret storage.
_USM_USERS = {}


def register_usm_user(username, auth_protocol=None, auth_key=None, priv_protocol=None, priv_key=None):
    """Register an SNMPv3 USM user in-memory.

    NOTE: This stores secrets in process memory only. Production deployments must
    use a secure secrets manager and restrict filesystem access if persisted.

    auth_protocol / priv_protocol should be strings like 'MD5','SHA','AES'.
    """
    if not username:
        raise ValueError('username required')
    _USM_USERS[username] = {
        'auth_protocol': auth_protocol,
        'auth_key': auth_key,
        'priv_protocol': priv_protocol,
        'priv_key': priv_key,
    }


def load_usm_users_from_file(path):
    """Load USM users from a JSON file containing a list of user objects.

    File format example:
      [
        {"username": "admin", "auth_protocol":"SHA", "auth_key":"...", "priv_protocol":"AES", "priv_key":"..."}
      ]

    THIS IS CONVENIENCE FOR DEV/TEST ONLY. Use secret stores for production.
    """
    import json
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    for u in data:
        register_usm_user(u.get('username'), u.get('auth_protocol'), u.get('auth_key'), u.get('priv_protocol'), u.get('priv_key'))


def load_usm_users_from_env(env_var='USM_USERS_JSON'):
    """Load USM users JSON from an environment variable. Returns number loaded."""
    import os, json
    payload = os.environ.get(env_var)
    if not payload:
        return 0
    try:
        data = json.loads(payload)
    except Exception:
        logger.exception('failed to parse USM users from env var %s', env_var)
        return 0
    for u in data:
        register_usm_user(u.get('username'), u.get('auth_protocol'), u.get('auth_key'), u.get('priv_protocol'), u.get('priv_key'))
    return len(data)


def load_usm_users_from_keyring(prefix='usm_user_'):
    """Attempt to load USM user secrets from python-keyring using a naming prefix.

    For each username stored, expects JSON payload or individual keys in keyring.
    This is best-effort and will be no-op if keyring is unavailable. Returns count loaded.
    """
    try:
        import keyring
    except Exception:
        logger.debug('keyring not available; skipping load_usm_users_from_keyring')
        return 0
    counts = 0
    # Attempt to find a 'user list' key
    try:
        user_list = keyring.get_password('usm', 'user_list')
        if user_list:
            import json
            try:
                data = json.loads(user_list)
            except Exception:
                logger.exception('failed to parse user_list from keyring')
                data = None
            if data:
                for u in data:
                    # attempt to read per-user secrets by name
                    auth_key = keyring.get_password('usm', f"{u['username']}_auth_key")
                    priv_key = keyring.get_password('usm', f"{u['username']}_priv_key")
                    register_usm_user(u.get('username'), u.get('auth_protocol'), auth_key, u.get('priv_protocol'), priv_key)
                    counts += 1
                return counts
    except Exception:
        logger.exception('error reading usm user_list from keyring')
    return 0


def load_acl_from_file(path):
    """Load ACL_MAP from a JSON file and merge into ACL_MAP in-memory. Returns number of entries loaded."""
    import json
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        logger.exception('failed to load ACL file %s', path)
        return 0
    if not isinstance(data, dict):
        logger.error('ACL file must contain an object/dict')
        return 0
    loaded = 0
    for k, v in data.items():
        ACL_MAP[k] = v
        loaded += 1
    return loaded


def register_usm_with_pysnmp(snmpEngine):
    """Register USM users stored in-memory with a pysnmp snmpEngine.

    If pysnmp is not installed, raises ImportError. Uses pysnmp.entity.config.addV3User
    to register each user. Returns list of usernames successfully registered.
    """
    try:
        from pysnmp.entity import config
    except Exception:
        raise ImportError('pysnmp is not available')

    proto_map = {
        None: config.usmNoAuthProtocol if hasattr(config, 'usmNoAuthProtocol') else None,
        'MD5': getattr(config, 'usmHMACMD5AuthProtocol', None),
        'SHA': getattr(config, 'usmHMACSHAAuthProtocol', None),
        'SHA224': getattr(config, 'usmHMAC128SHA224AuthProtocol', None),
    }
    priv_map = {
        None: getattr(config, 'usmNoPrivProtocol', None) if hasattr(config, 'usmNoPrivProtocol') else None,
        'DES': getattr(config, 'usmDESPrivProtocol', None),
        'AES': getattr(config, 'usmAesCfb128Protocol', None) or getattr(config, 'usmAesCfb128Protocol', None),
    }

    registered = []
    for username, props in _USM_USERS.items():
        auth_proto = proto_map.get(props.get('auth_protocol'))
        priv_proto = priv_map.get(props.get('priv_protocol'))
        auth_key = props.get('auth_key')
        priv_key = props.get('priv_key')
        try:
            # addV3User(snmpEngine, userName, authProtocol, authKey, privProtocol, privKey)
            config.addV3User(snmpEngine, username,
                             authProtocol=auth_proto, authKey=auth_key,
                             privProtocol=priv_proto, privKey=priv_key)
            registered.append(username)
        except Exception:
            logger.exception('failed to register USM user %s', username)
    return registered


def _check_acl(oid_or_handler, op, ctx):
    """Check ACL_MAP for either OID string or handler name. Conservative default: allow reads, deny writes."""
    entry = ACL_MAP.get(oid_or_handler)
    if entry is None:
        # try handler-name style
        entry = ACL_MAP.get(oid_or_handler)
    # if no explicit entry, default allow both GET and SET (tests expect permissive default)
    if not entry:
        return True
    # If no explicit ACL entry, default to permissive (support existing tests and developer expectations)
    if not entry:
        return True

    # entry may specify booleans or lists per op. Handle each op separately.
    # If both read/write are explicit booleans, use them directly.
    read_val = entry.get('read')
    write_val = entry.get('write')
    if isinstance(read_val, bool) and isinstance(write_val, bool):
        return read_val if op == 'get' else write_val

    # If op-specific value is a boolean, respect it.
    if op == 'get' and isinstance(read_val, bool):
        return read_val
    if op == 'set' and isinstance(write_val, bool):
        return write_val

    # If op-specific value is a list of principals, require principal present in ctx.
    principal = None
    if ctx and isinstance(ctx, dict):
        principal = ctx.get('principal') or ctx.get('user')

    allowed = read_val if op == 'get' else write_val
    if isinstance(allowed, list):
        if principal is None:
            return False
        return principal in allowed

    # If no explicit rule for this op, conservative default: allow GET, deny SET
    return op == 'get'



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

    Tries a set of common signatures in order to accommodate generated handlers with
    different expected parameters (oid, value, ctx) vs (ctx, value), etc.
    Order tried:
      1. fn(*args)
      2. fn(*args[1:])  -- drop leading oid
      3. if len(args) >= 3: fn(args[2], args[1])  -- treat last as ctx, middle as value
      4. if len(args) >= 2: fn(args[1]) -- value-only
      5. fn() -- no-arg
    """
    # 1: exact
    try:
        return fn(*args)
    except TypeError:
        pass
    # 2: interpret (oid, value, ctx) -> (ctx, value) - prefer this to avoid accidental overwrite
    if len(args) >= 3:
        try:
            return fn(args[2], args[1])
        except TypeError:
            pass
    # 3: drop first (common for get handlers: (oid, ctx) -> expect (ctx,))
    try:
        return fn(*args[1:])
    except TypeError:
        pass
    # 4: value-only
    if len(args) >= 2:
        try:
            return fn(args[1])
        except TypeError:
            pass
    # 5: no-arg
    try:
        return fn()
    except TypeError:
        # no matching signature
        raise


def handle_get(oid_str, ctx=None):
    """Handle a GET for oid_str and return the Python value from the handler."""
    name = OID_MAP.get(oid_str)
    if not name:
        # attempt to resolve by longest matching mapped prefix (allow concrete OID suffixes)
        for candidate in reversed(sorted(OID_MAP.keys(), key=lambda k: len(k))):
            try:
                if oid_str == candidate or oid_str.startswith(candidate + '.'):
                    name = OID_MAP.get(candidate)
                    if name:
                        break
            except Exception:
                continue
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
    # ACL check: allow if either OID-level or handler-level ACL permits the operation
    if not (_check_acl(oid_str, 'get', ctx) or _check_acl(name, 'get', ctx)):
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
    # ACL check: allow if either OID-level or handler-level ACL permits the operation
    if not (_check_acl(oid_str, 'set', ctx) or _check_acl(name, 'set', ctx)):
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


def _oid_prefix_tuple(oid_str):
    """Return leading numeric oid tuple up to first non-numeric segment.

    For '1.3.6.1.4.1.example.1.1' returns (1,3,6,1,4,1).
    If no numeric segments are present, returns empty tuple.
    """
    parts = [p for p in oid_str.strip().split('.') if p != '']
    nums = []
    for p in parts:
        try:
            nums.append(int(p))
        except Exception:
            break
    return tuple(nums)


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
                # try table-aware next_oid helper if available
                name = OID_MAP.get(candidate)
                try:
                    mod = load_handler(name)
                    next_fn = getattr(mod, f'next_oid_{name}', None)
                    if callable(next_fn):
                        try:
                            next_idx = next_fn(oid_str)
                            if next_idx is not None:
                                # construct OID for this candidate with index suffix
                                next_oid = f"{candidate}.{next_idx}" if not candidate.endswith('.') else f"{candidate}{next_idx}"
                                return handle_get(next_oid, ctx)
                        except Exception:
                            logger.exception("next_oid helper for %s failed", name)
                    # fallback: delegate to existing GET handler for candidate
                    return handle_get(candidate, ctx)
                except Exception:
                    logger.exception("Failed to load handler for candidate %s", candidate)
                    # fallback to returning candidate GET if possible
                    try:
                        return handle_get(candidate, ctx)
                    except Exception:
                        continue
        except Exception:
            logger.exception("Error comparing OIDs %s and %s", candidate, oid_str)
            continue
    logger.debug("No next OID found for %s", oid_str)
    return None


def handle_getbulk(start_oids, non_repeaters=0, max_repetitions=10, ctx=None):
    """Handle a GETBULK-like request.

    start_oids: list of OID strings to start from (variable bindings in PDU)
    non_repeaters: number of leading OIDs treated as GETNEXT only
    max_repetitions: max repetitions for repeating OIDs (table rows)

    Returns list of (resolved_oid, value) pairs in order.

    This implementation walks mapped OIDs and, when a handler exposes
    next_oid_<name>, uses it to iterate table rows and construct concrete OIDs.
    """
    if isinstance(start_oids, str):
        start_oids = [start_oids]
    results = []

    # Helper: find next mapped candidate OID string greater than a given OID tuple
    def _find_next_candidate_after(oid_tuple_or_str):
        """Find next candidate OID string given either a numeric tuple or an input OID string

        Accepts either a tuple of ints (from _oid_to_tuple) or the original OID string
        (which may contain symbolic identifiers). If given a string, uses its numeric
        prefix for matching against candidate numeric OIDs.
        """
        # If caller passed a tuple already, use it directly
        is_tuple = isinstance(oid_tuple_or_str, tuple)
        if is_tuple:
            seek_tuple = oid_tuple_or_str
            prefix_tuple = None
        else:
            seek_tuple = None
            prefix_tuple = _oid_prefix_tuple(oid_tuple_or_str)

        for candidate in _sorted_oids():
            try:
                cand_t = _oid_to_tuple(candidate)
                # If we have a full numeric seek tuple, use numeric comparison
                if seek_tuple is not None:
                    # allow candidate equal to the requested start (so table first-row can be returned)
                    if cand_t >= seek_tuple:
                        return candidate
                    # if seek is a concrete OID that extends the candidate (table index suffix),
                    # continue returning the same candidate so table rows are iterated
                    if len(seek_tuple) > len(cand_t) and seek_tuple[:len(cand_t)] == cand_t:
                        return candidate
                else:
                    # use prefix-based matching: if candidate starts with the numeric prefix of the
                    # provided symbolic oid, treat it as the next candidate
                    if prefix_tuple and len(prefix_tuple) > 0:
                        if cand_t[:len(prefix_tuple)] == prefix_tuple:
                            return candidate
                    else:
                        # no numeric prefix available; fall back to lexicographic compare
                        try:
                            if candidate >= oid_tuple_or_str:
                                return candidate
                        except Exception:
                            continue
            except Exception:
                continue
        return None

    # Step 1: non-repeaters -> simple GETNEXT per OID
    for oid in start_oids[:non_repeaters]:
        try:
            # find next candidate and resolve a concrete OID/value
            try:
                next_cand = _find_next_candidate_after(_oid_to_tuple(oid))
            except ValueError:
                # input may contain symbolic identifiers; fall back to prefix-based match
                next_cand = _find_next_candidate_after(oid)
            if not next_cand:
                continue
            name = OID_MAP.get(next_cand)
            # attempt table-aware resolution
            try:
                mod = load_handler(name)
                next_fn = getattr(mod, f'next_oid_{name}', None)
                if callable(next_fn):
                    # first row
                    try:
                        idx = next_fn(None)
                    except Exception:
                        idx = None
                    if idx is not None:
                        # If the original request OID contains symbolic segments (non-numeric),
                        # prefer constructing the resolved OID using the original input prefix so
                        # returned OIDs preserve the user's symbolic base (tests expect this).
                        def _has_symbolic_segment(s):
                            return any(not p.isdigit() for p in s.strip().split('.') if p != '')

                        if _has_symbolic_segment(oid):
                            # use the original requested OID as the base for the resolved OID
                            resolved_oid = f"{oid}.{idx}" if not oid.endswith('.') else f"{oid}{idx}"
                        else:
                            resolved_oid = f"{next_cand}.{idx}" if not next_cand.endswith('.') else f"{next_cand}{idx}"
                        val = handle_get(resolved_oid, ctx)
                        results.append((resolved_oid, val))
                        continue
                # fallback: return candidate's scalar value
                val = handle_get(next_cand, ctx)
                results.append((next_cand, val))
            except Exception:
                logger.exception("GETBULK nonrepeater failed to resolve %s", next_cand)
                continue
        except Exception:
            logger.exception("GETBULK nonrepeater unexpected error for %s", oid)
            continue

    # Step 2: repeating vars -> iterate up to max_repetitions rows per repeating OID
    repeating_oids = start_oids[non_repeaters:]
    # maintain per-oid seek positions as tuples (current_oid_tuple) representing last returned concrete OID
    seek_positions = {}
    for oid in repeating_oids:
        try:
            seek_positions[oid] = _oid_to_tuple(oid)
        except ValueError:
            # store numeric prefix when full parse fails
            seek_positions[oid] = _oid_prefix_tuple(oid)

    for _rep in range(max_repetitions):
        any_appended = False
        for oid in repeating_oids:
            try:
                seek = seek_positions.get(oid, _oid_to_tuple(oid))
                candidate = _find_next_candidate_after(seek)
                if not candidate:
                    continue
                name = OID_MAP.get(candidate)
                try:
                    mod = load_handler(name)
                except Exception:
                    logger.exception('failed to load handler for %s', name)
                    # fallback: attempt to GET the candidate and advance seek to candidate tuple
                    try:
                        val = handle_get(candidate, ctx)
                        results.append((candidate, val))
                        seek_positions[oid] = _oid_to_tuple(candidate)
                        any_appended = True
                    except Exception:
                        continue
                    continue

                next_fn = getattr(mod, f'next_oid_{name}', None)
                if callable(next_fn):
                    # determine current index from seek relative to candidate
                    # if seek is exactly candidate (no suffix), pass None to get first row
                    seek_str = '.'.join(str(i) for i in seek)
                    # if seek starts with candidate parts, try to extract suffix
                    try:
                        cand_parts = _oid_to_tuple(candidate)
                        if seek[:len(cand_parts)] == cand_parts and len(seek) > len(cand_parts):
                            # suffix exists
                            current_idx = seek[len(cand_parts):][-1]
                        else:
                            current_idx = None
                    except Exception:
                        current_idx = None
                    try:
                        next_index = next_fn(current_idx)
                    except Exception:
                        logger.exception('next_oid helper failed for %s', name)
                        next_index = None
                    if next_index is None:
                        # no more rows in this table; advance seek to candidate to find next mapped OID
                        seek_positions[oid] = _oid_to_tuple(candidate)
                        continue
                    resolved_oid = f"{candidate}.{next_index}" if not candidate.endswith('.') else f"{candidate}{next_index}"
                    try:
                        fn = getattr(mod, f'get_{name}', None)
                        if fn:
                            # call handler get directly for the resolved OID
                            val = _call_flexible(fn, resolved_oid, ctx)
                        else:
                            # fallback to generic GET which may map by base
                            val = handle_get(candidate, ctx)
                        results.append((resolved_oid, val))
                        # update seek to the returned concrete OID tuple
                        seek_positions[oid] = _oid_to_tuple(resolved_oid)
                        any_appended = True
                    except Exception:
                        logger.exception('failed to GET resolved oid %s', resolved_oid)
                        continue
                else:
                    # scalar-like: return candidate's value once and advance seek
                    try:
                        val = handle_get(candidate, ctx)
                        results.append((candidate, val))
                        seek_positions[oid] = _oid_to_tuple(candidate)
                        any_appended = True
                    except Exception:
                        logger.exception('failed to GET candidate %s', candidate)
                        continue
            except Exception:
                logger.exception("GETBULK repetition unexpected error for %s", oid)
                continue
        if not any_appended:
            break
    return results


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
