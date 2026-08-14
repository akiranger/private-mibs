"""
MIB を解析して内部 JSON スキーマを作るスクリプト（pysmi 利用想定）。

依存: pysmi (pip install pysmi)

使い方例:
  python mib_parser.py path/to/EXAMPLE-MIB > example_schema.json
"""
import sys
import json

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
    """Improved naive parser for MIB text when pysmi is unavailable.

    This scans for OBJECT-TYPE blocks and attempts to extract name, syntax,
    access, description, and oid_assignment lines when present.
    """
    import re

    objs = []
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()

    # Normalize line endings and split into lines for scanning
    lines = text.replace('\r\n', '\n').split('\n')
    n = len(lines)

    i = 0
    while i < n:
        line = lines[i]
        if 'OBJECT-TYPE' in line:
            # find name: prefer token before OBJECT-TYPE on the same line, fallback to previous non-empty line
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

            # scan forward for fields until blank line or next OBJECT-TYPE
            syntax = None
            access = None
            description = None
            oid_assignment = None

            k = i + 1
            desc_lines = []
            in_description = False
            while k < n and 'OBJECT-TYPE' not in lines[k] and lines[k].strip() != '':
                l = lines[k].strip()
                # SYNTAX
                if l.startswith('SYNTAX'):
                    syntax = l[len('SYNTAX'):].strip()
                # ACCESS or MAX-ACCESS
                elif l.startswith('MAX-ACCESS') or l.startswith('ACCESS'):
                    parts = l.split()
                    if len(parts) >= 2:
                        access = parts[-1].strip()
                # DESCRIPTION block
                elif l.startswith('DESCRIPTION'):
                    # may begin with DESCRIPTION "... possibly multi-line ..."
                    in_description = True
                    # capture following lines until closing quote
                    # find the first occurrence of '"' on this line
                    rest = l[len('DESCRIPTION'):].lstrip()
                    if '"' in rest:
                        # start of description content
                        pos = rest.find('"')
                        rest_content = rest[pos+1:]
                        if rest_content.endswith('"'):
                            desc_lines.append(rest_content[:-1])
                            in_description = False
                        else:
                            desc_lines.append(rest_content)
                    else:
                        # description starts on next lines
                        pass
                elif in_description:
                    # look for closing quote
                    if l.endswith('"'):
                        desc_lines.append(l[:-1])
                        in_description = False
                    else:
                        desc_lines.append(l)
                # OID assignment ("::= { parent n }")
                elif '::=' in l and '{' in l and '}' in l:
                    # capture the RHS as oid_assignment
                    # e.g. myScalar ::= { parent 1 }
                    rhs = l.split('::=')[-1].strip()
                    oid_assignment = rhs
                k += 1

            if desc_lines:
                description = '\n'.join([d.strip() for d in desc_lines if d is not None])

            objs.append({'name': name or 'unknown', 'syntax': syntax, 'access': access, 'description': description, 'oid_assignment': oid_assignment})
            i = k
        else:
            i += 1

    return {'mib': path, 'objects': objs}


def parse_mib_to_json(mib_path):
    if file is None:
        return simple_parse_mib_text(mib_path)

    # Example pipeline using pysmi. Real-world usage configures searchPaths and codegen.
    # Placeholder: fall back to simple parser to ensure prototype runs without deps.
    return simple_parse_mib_text(mib_path)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python mib_parser.py path/to/MIB', file=sys.stderr)
        sys.exit(2)
    schema = parse_mib_to_json(sys.argv[1])
    print(json.dumps(schema, indent=2, ensure_ascii=False))