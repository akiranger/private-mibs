"""
Attempt pysmi compilation with combined readers and verbose output.
"""
import os, tempfile, traceback
from pysmi.reader import FileReader, get_readers_from_urls
from pysmi.writer import FileWriter
from pysmi.compiler import MibCompiler
from pysmi.codegen.pysnmp import PySnmpCodeGen

mib_path='example/EXAMPLE-MIB'
mib_dir=os.path.dirname(os.path.abspath(mib_path))
mib_name=os.path.splitext(os.path.basename(mib_path))[0]
outdir=tempfile.mkdtemp(prefix='mib_py_')
print('mib_dir=', mib_dir)
print('outdir=', outdir)

# Build readers: local and HTTP
readers = []
readers.append(FileReader(mib_dir))
# pysmi provides helper to create HttpReader from URLs
try:
    http_readers = get_readers_from_urls(['https://mibs.snmplabs.com/asn1/'])
    readers.extend(http_readers)
except Exception as e:
    print('get_readers_from_urls failed:', e)

# Try compiling with each reader separately and then with the list via the first reader (MibCompiler expects a single reader)
success = False
for r in readers:
    try:
        print('Trying reader:', type(r))
        writer = FileWriter(outdir)
        codegen = PySnmpCodeGen()
        compiler = MibCompiler(codegen, r, writer)
        compiler.compile(mib_name)
        print('Compile OK with reader', type(r))
        success = True
        break
    except Exception:
        traceback.print_exc()

if not success:
    print('All readers failed; showing outdir listing')
    for root, dirs, files in os.walk(outdir):
        for fn in files:
            p=os.path.join(root,fn)
            print(p, os.path.getsize(p))
else:
    # list generated files
    for root, dirs, files in os.walk(outdir):
        for fn in files:
            print('generated:', os.path.join(root,fn), os.path.getsize(os.path.join(root,fn)))
    genfile = os.path.join(outdir, mib_name + '.py')
    if not os.path.exists(genfile):
        genfile = genfile.upper()
    if os.path.exists(genfile):
        print('\n---- head of generated file ----')
        with open(genfile, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i>200: break
                print(line.rstrip())
    else:
        print('No generated module found in outdir')
