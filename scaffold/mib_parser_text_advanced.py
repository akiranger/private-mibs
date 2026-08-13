"""
Advanced text-based MIB parser (fallback when pysmi/pysnmp compilation unavailable).
Extracts OBJECT-TYPE blocks, SYNTAX, MAX-ACCESS, OID assignment, and SEQUENCE fields for ENTRYs.

Usage:
  python scaffold\mib_parser_text_advanced.py path/to/MIB > schema.json
"""
import re
import sys
import json
import os


def parse_mib(path):
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()
    # normalize line endings
    lines = text.splitlines()
    schema = {'mib': os.path.basename(path), 'objects': []}

    # Find all OBJECT-TYPE occurrences with a preceding name
    obj_pattern = re.compile(r'(?P<name>\w+)\s+OBJECT-TYPE', re.IGNORECASE)
    for m in obj_pattern.finditer(text):
        name = m.group('name')
        # find start index in lines
        start_pos = text[:m.start()].count('\n')
        # collect block lines until a blank line followed by something not indented or next OBJECT-TYPE
        block_lines = []
        for i in range(start_pos, len(lines)):
            block_lines.append(lines[i])
            if '::=' in lines[i]:
                # capture OID assignment and stop
                break
            # guard: if next object-type found, break
            if i>start_pos and re.search(r'\w+\s+OBJECT-TYPE', lines[i]):
                break
        block = '\n'.join(block_lines)
        obj = {'name': name, 'raw': block}
        # SYNTAX
        syntax_m = re.search(r'SYNTAX\s+([^{\n]+)', block, re.IGNORECASE)
        if syntax_m:
            syntax = syntax_m.group(1).strip()
            obj['syntax'] = ' '.join(syntax.split())
        # MAX-ACCESS
        access_m = re.search(r'MAX-ACCESS\s+(\w+)', block, re.IGNORECASE)
        if access_m:
            obj['access'] = access_m.group(1)
        # DESCRIPTION
        desc_m = re.search(r'DESCRIPTION\s+"([\s\S]*?)"', block, re.IGNORECASE)
        if desc_m:
            obj['description'] = ' '.join(desc_m.group(1).split())
        # OID assignment ::= { parent num }
        oid_m = re.search(r'::=\s*\{\s*([^\}]+)\s*\}', block)
        if oid_m:
            oid_text = oid_m.group(1).strip()
            # attempt to compute dotted OID if parent is known numeric or name
            obj['oid_assignment'] = oid_text
        # detect table
        if re.search(r'SYNTAX\s+SEQUENCE\s+OF', block, re.IGNORECASE):
            obj['kind'] = 'table'
            # extract entry type
            entry_m = re.search(r'SYNTAX\s+SEQUENCE\s+OF\s+(\w+)', block, re.IGNORECASE)
            if entry_m:
                obj['entry_type'] = entry_m.group(1)
        else:
            obj['kind'] = 'scalar'
        schema['objects'].append(obj)

    # Additionally, parse ENTRY definitions for SEQUENCE fields
    entry_pattern = re.compile(r'(?P<name>\w+)\s+OBJECT-TYPE[\s\S]*?SYNTAX\s+SEQUENCE\s*\{(?P<body>[\s\S]*?)\}', re.IGNORECASE)
    for m in entry_pattern.finditer(text):
        name = m.group('name')
        body = m.group('body')
        fields = []
        for line in body.splitlines():
            line = line.strip().rstrip(',')
            if not line: continue
            parts = line.split()
            if len(parts) >= 2:
                fname = parts[0]
                ftype = parts[1]
                fields.append({'name': fname, 'type': ftype})
        schema['objects'].append({'name': name, 'kind': 'entry', 'fields': fields})

    return schema


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python mib_parser_text_advanced.py path/to/MIB', file=sys.stderr)
        sys.exit(2)
    schema = parse_mib(sys.argv[1])
    print(json.dumps(schema, indent=2, ensure_ascii=False))
