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
    objs = []
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    # Naive pass: find lines with "::= {" to identify symbols and OBJECT-TYPE blocks
    for i, line in enumerate(lines):
        if 'OBJECT-TYPE' in line:
                # try to extract the identifier from the same line first, fallback to previous non-empty line
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