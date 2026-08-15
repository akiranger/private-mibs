"""
MIB を解析して内部 JSON スキーマを作るスクリプト（pysmi 利用想定）。

依存: pysmi (pip install pysmi)

使い方例:
  python mib_parser.py path/to/EXAMPLE-MIB > example_schema.json
"""
import sys
import json


def _has_valid_objects(schema):
    return isinstance(schema, dict) and isinstance(schema.get('objects'), list) and len(schema['objects']) > 0


# Lazy import to keep file usable even if deps are missing
try:
    from pysmi.reader import file
    from pysmi.parser.smi import parser
    from pysmi.codegen import pysnmp as pysnmp_codegen
    from pysmi.compiler import MibCompiler
    from pysmi.writer import callback
except Exception:
    # Fallback stub: parse minimal OBJECT-TYPE lines
    file = None


def simple_parse_mib_text(path):
    """Improved naive parser for MIB text when newer parsers are unavailable.

    This scans for OBJECT-TYPE blocks and attempts to extract name, syntax,
    access, description, and oid_assignment lines when present.
    """
    import re

    objs = []
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()

    lines = text.replace('\r\n', '\n').split('\n')
    n = len(lines)

    i = 0
    while i < n:
        line = lines[i]
        if 'OBJECT-TYPE' in line:
            name = None
            parts = line.strip().split()
            if len(parts) >= 2 and 'OBJECT-TYPE' in parts:
                try:
                    idx = parts.index('OBJECT-TYPE')
                    if idx >= 1:
                        name = parts[idx-1]
                except ValueError:
                    pass
            if not name:
                j = i - 1
                while j >= 0 and lines[j].strip() == '':
                    j -= 1
                if j >= 0:
                    name = lines[j].strip().split()[0]

            syntax = None
            access = None
            description = None
            oid_assignment = None

            k = i + 1
            desc_lines = []
            in_description = False
            while k < n and 'OBJECT-TYPE' not in lines[k] and lines[k].strip() != '':
                l = lines[k].strip()
                if l.startswith('SYNTAX'):
                    syntax = l[len('SYNTAX'):].strip()
                elif l.startswith('MAX-ACCESS') or l.startswith('ACCESS'):
                    parts = l.split()
                    if len(parts) >= 2:
                        access = parts[-1].strip()
                elif l.startswith('DESCRIPTION'):
                    in_description = True
                    rest = l[len('DESCRIPTION'):].lstrip()
                    if '"' in rest:
                        pos = rest.find('"')
                        rest_content = rest[pos+1:]
                        if rest_content.endswith('"'):
                            desc_lines.append(rest_content[:-1])
                            in_description = False
                        else:
                            desc_lines.append(rest_content)
                elif in_description:
                    if l.endswith('"'):
                        desc_lines.append(l[:-1])
                        in_description = False
                    else:
                        desc_lines.append(l)
                elif '::=' in l and '{' in l and '}' in l:
                    rhs = l.split('::=')[-1].strip()
                    oid_assignment = rhs
                k += 1

            if desc_lines:
                description = '\n'.join([d.strip() for d in desc_lines if d is not None])

            objs.append({'name': name or 'unknown', 'syntax': syntax, 'access': access, 'description': description, 'oid_assignment': oid_assignment})
            i = k
        else:
            i += 1

    return {'mib': path, 'objects': objs, 'source': 'text-simple'}


try:
    from . import mib_parser_pysmi as _mib_parser_pysmi
except Exception:
    _mib_parser_pysmi = None

try:
    from . import mib_parser_pysnmp_loader as _mib_parser_pysnmp_loader
except Exception:
    _mib_parser_pysnmp_loader = None

try:
    from . import mib_parser_text_advanced as _mib_parser_text_advanced
except Exception:
    _mib_parser_text_advanced = None


def parse_mib_to_json(mib_path):
    """Automatically select the best parser based on available dependencies.

    Priority order:
      1. pysmi-backed parser
      2. pysnmp MibBuilder loader
      3. advanced text parser
      4. legacy simple text scanner
    """
    candidates = []

    if _mib_parser_pysmi is not None and getattr(_mib_parser_pysmi, 'PYSPI_AVAILABLE', False):
        candidates.append(('pysmi', lambda: _mib_parser_pysmi.parse_with_pysmi(mib_path)))

    if _mib_parser_pysnmp_loader is not None and getattr(_mib_parser_pysnmp_loader, 'PYSNMP_AVAILABLE', False):
        candidates.append(('pysnmp-loader', lambda: _mib_parser_pysnmp_loader.parse_with_pysnmp(mib_path)))

    if _mib_parser_text_advanced is not None:
        candidates.append(('text-advanced', lambda: _mib_parser_text_advanced.parse_mib(mib_path)))

    for source_name, parser_fn in candidates:
        try:
            parsed = parser_fn()
            if _has_valid_objects(parsed):
                return parsed
        except Exception:
            continue

    return simple_parse_mib_text(mib_path)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python mib_parser.py path/to/MIB', file=sys.stderr)
        sys.exit(2)
    schema = parse_mib_to_json(sys.argv[1])
    print(json.dumps(schema, indent=2, ensure_ascii=False))