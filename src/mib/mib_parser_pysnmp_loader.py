"""
MIB -> JSON schema using pysnmp.MibBuilder

Usage:
  python src/mib/mib_parser_pysnmp_loader.py path/to/MIB > schema.json

This script attempts to load the MIB using pysnmp's MibBuilder. It adds the MIB's directory
as a local source and also configures the online SNMPlabs source as a fallback to fetch
standard MIBs if not present locally.

The output is a simple JSON list of symbols with best-effort OID, type and access information.
"""
import sys
import os
import json

try:
    from pysnmp.smi import builder, view, compiler
    from pysnmp.smi.rfc1902 import ObjectName
    PYSNMP_AVAILABLE = True
except Exception:
    PYSNMP_AVAILABLE = False


def fallback(path):
    # reuse simple textual scan
    objs = []
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        if 'OBJECT-TYPE' in line:
            name = None
            tokens = line.strip().split()
            if len(tokens) >= 2 and tokens[0] != 'OBJECT-TYPE':
                name = tokens[0]
            else:
                j = i-1
                while j >= 0 and lines[j].strip() == '':
                    j -= 1
                if j >= 0:
                    token = lines[j].strip().split()[0]
                    name = token
            objs.append({'name': name or f'obj_{i}', 'raw': line.strip()})
    return {'mib': os.path.basename(path), 'objects': objs, 'note': 'fallback'}


def parse_with_pysnmp(mib_path):
    mib_dir = os.path.dirname(os.path.abspath(mib_path)) or '.'
    mib_name = os.path.splitext(os.path.basename(mib_path))[0]

    mb = builder.MibBuilder()
    # add local dir as MIB source
    mb.addMibSources(builder.DirMibSource(mib_dir))
    # configure pysnmp to fetch missing MIBs from snmplabs
    try:
        compiler.addMibCompiler(mb, sources=['http://mibs.snmplabs.com/asn1/@mib@'])
    except Exception:
        # older pysnmp may require different API; ignore
        pass

    schema = {'mib': mib_name, 'objects': [], 'note': None}
    try:
        mb.loadModules(mib_name)
    except Exception as e:
        schema['error'] = f'loadModules failed: {e}'
        # continue to try to introspect available symbols

    # gather symbols known for this module
    symbols = {}
    try:
        symbols = mb.mibSymbols.get(mib_name, {})
    except Exception:
        symbols = {}

    # if no symbols found, fallback
    if not symbols:
        schema['note'] = 'no_symbols_found'
        return schema

    for symname, symobj in symbols.items():
        entry = {'name': symname}
        try:
            # importSymbols returns pysnmp object(s)
            objs = mb.importSymbols(mib_name, symname)
            if not objs:
                entry['note'] = 'import_failed'
                schema['objects'].append(entry)
                continue
            obj = objs[0]
            # try to extract oid
            oid = None
            try:
                # many pysnmp objects expose getName()
                name_tuple = obj.getName()
                if isinstance(name_tuple, (list, tuple)):
                    oid = '.'.join(str(x) for x in name_tuple)
                else:
                    oid = str(name_tuple)
            except Exception:
                oid = None
            entry['oid'] = oid
            # try to extract syntax/type
            try:
                syntax = obj.getSyntax()
                entry['type'] = syntax.__class__.__name__
            except Exception:
                # fallback to class name
                entry['type'] = obj.__class__.__name__
            # try to get access (getMaxAccess)
            try:
                access = obj.getMaxAccess()
                entry['access'] = str(access)
            except Exception:
                entry['access'] = None
            # detect table/column heuristics
            try:
                clsname = obj.__class__.__name__
                entry['class'] = clsname
                if 'Table' in clsname or 'Entry' in clsname or 'Column' in clsname:
                    entry['isTable'] = True
                else:
                    entry['isTable'] = False
            except Exception:
                entry['isTable'] = False

        except Exception as e:
            entry['error'] = str(e)
        schema['objects'].append(entry)

    return schema


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python mib_parser_pysnmp_loader.py path/to/MIB', file=sys.stderr)
        sys.exit(2)
    path = sys.argv[1]
    if not os.path.exists(path):
        print(json.dumps({'error': 'mib path not found', 'path': path}))
        sys.exit(1)
    if PYSNMP_AVAILABLE:
        try:
            out = parse_with_pysnmp(path)
        except Exception as e:
            out = {'mib': os.path.basename(path), 'error': str(e)}
    else:
        out = fallback(path)
    print(json.dumps(out, indent=2, ensure_ascii=False))
