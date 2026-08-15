"""
MIB -> JSON schema using pysmi

This script attempts to use pysmi to compile a MIB into pysnmp Python modules and then
extract OBJECT-TYPE and table metadata into a normalized JSON schema.

Usage:
  python src/mib/mib_parser_pysmi.py path/to/MIB > schema.json

Notes:
- Requires pysmi and pysnmp for full extraction (pip install pysmi pysnmp)
- If dependencies are missing, falls back to the simple text scanner (like mib_parser.py)
"""
import sys
import os
import json
import re
import tempfile

try:
    from pysmi.reader import FileReader, HttpReader
    from pysmi.compiler import MibCompiler
    from pysmi.codegen.pysnmp import PySnmpCodeGen
    from pysmi.writer import FileWriter
    PYSPI_AVAILABLE = True
except Exception:
    PYSPI_AVAILABLE = False


def fallback_parse(path):
    # reuse simple logic from mib_parser.py
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
    return {'mib': os.path.basename(path), 'objects': objs, 'note': 'fallback/text-scan'}


def parse_with_pysmi(mib_path):
    # Create temp output dir for generated pysnmp modules
    outdir = tempfile.mkdtemp(prefix='mib_py_')
    try:
        # Reader expects a directory containing MIBs; include local dir and HTTP fallback
        mib_dir = os.path.dirname(os.path.abspath(mib_path)) or '.'
        file_reader = FileReader(mib_dir)
        http_reader = HttpReader('https://mibs.snmplabs.com/asn1/')
        # pysmi supports combining readers via a ReaderProxy; simplest is to try file reader first then http
        # We'll implement a simple sequence: attempt compile with file reader, on failure try with http reader
        writer = FileWriter(outdir)
        codegen = PySnmpCodeGen()
        mib_name = os.path.splitext(os.path.basename(mib_path))[0]
        # First try local-only
        try:
            compiler = MibCompiler(codegen, file_reader, writer)
            compiler.compile(mib_name)
        except Exception as e_local:
            # try HTTP-enabled reader
            try:
                compiler = MibCompiler(codegen, http_reader, writer)
                compiler.compile(mib_name)
            except Exception as e_http:
                return {'mib': os.path.basename(mib_path), 'objects': [], 'note': f'compile-failed-local:{e_local} http:{e_http}'}
        # read generated file
        genfile = os.path.join(outdir, mib_name + '.py')
        if not os.path.exists(genfile):
            # try uppercase name
            genfile = os.path.join(outdir, mib_name.upper() + '.py')
        if not os.path.exists(genfile):
            return {'mib': os.path.basename(mib_path), 'objects': [], 'note': 'no-generated-file'}

        with open(genfile, 'r', encoding='utf-8') as f:
            code = f.read()

        # crude regex-based extraction from generated pysnmp module
        objects = []

        # Find scalar/table definitions like: myScalar = MibScalar((1,3,6,1,...), Integer32()).setMaxAccess("readwrite")
        scalar_re = re.compile(r"(?m)^(?P<name>\w+)\s*=\s*Mib(?:Scalar|Identifier)\s*\(\s*\((?P<oid>[^\)]*)\)\s*,\s*(?P<type>\w+)\s*\)\s*(?:\.setMaxAccess\(\s*['\"](?P<access>[^'\"]+)['\"]\s*\))?", re.MULTILINE)
        for m in scalar_re.finditer(code):
            name = m.group('name')
            oid = tuple(int(x.strip()) for x in m.group('oid').split(',') if x.strip())
            typ = m.group('type')
            access = m.group('access') or 'unknown'
            objects.append({'name': name, 'oid': '.'.join(str(x) for x in oid), 'type': typ, 'access': access, 'kind': 'scalar'})

        # Table/row/column patterns: MibTable, MibTableRow, MibTableColumn
        # Find columns like: myValue = MibTableColumn((1,3,6,...), OctetString()).setMaxAccess("readwrite")
        col_re = re.compile(r"(?m)^(?P<name>\w+)\s*=\s*MibTableColumn\s*\(\s*\((?P<oid>[^\)]*)\)\s*,\s*(?P<type>\w+)\s*\)\s*(?:\.setMaxAccess\(\s*['\"](?P<access>[^'\"]+)['\"]\s*\))?", re.MULTILINE)
        cols = {}
        for m in col_re.finditer(code):
            name = m.group('name')
            oid = tuple(int(x.strip()) for x in m.group('oid').split(',') if x.strip())
            typ = m.group('type')
            access = m.group('access') or 'unknown'
            cols[name] = {'name': name, 'oid': '.'.join(str(x) for x in oid), 'type': typ, 'access': access}

        # Heuristic: detect table names from MibTable definitions
        table_re = re.compile(r"(?m)^(?P<name>\w+)\s*=\s*MibTable\s*\(\s*\(\s*(?P<oid>[^\)]*)\)\s*\)", re.MULTILINE)
        tables = []
        for m in table_re.finditer(code):
            tname = m.group('name')
            toid = tuple(int(x.strip()) for x in m.group('oid').split(',') if x.strip())
            tables.append({'name': tname, 'oid': '.'.join(str(x) for x in toid), 'columns': []})

        # associate columns to nearest table by OID prefix
        for c in cols.values():
            for t in tables:
                if c['oid'].startswith(t['oid']):
                    t['columns'].append(c)
        # add tables and columns to objects
        for t in tables:
            objects.append({'name': t['name'], 'oid': t['oid'], 'type': 'table', 'columns': t['columns'], 'kind': 'table'})

        # attach any standalone columns as scalars if not mapped
        for c in cols.values():
            if not any(c in t.get('columns', []) for t in tables):
                objects.append({'name': c['name'], 'oid': c['oid'], 'type': c['type'], 'access': c['access'], 'kind': 'column'})

        return {'mib': os.path.basename(mib_path), 'objects': objects, 'generated_py': genfile}
    finally:
        # leaving generated files in temp dir may help debugging; do not remove
        pass


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python mib_parser_pysmi.py path/to/MIB', file=sys.stderr)
        sys.exit(2)
    path = sys.argv[1]
    if PYSPI_AVAILABLE:
        try:
            schema = parse_with_pysmi(path)
        except Exception as e:
            schema = {'mib': os.path.basename(path), 'objects': [], 'error': str(e)}
    else:
        schema = fallback_parse(path)
    print(json.dumps(schema, indent=2, ensure_ascii=False))
