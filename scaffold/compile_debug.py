import traceback
from pysmi.reader import FileReader, HttpReader
from pysmi.writer import FileWriter
from pysmi.compiler import MibCompiler
from pysmi.codegen.pysnmp import PySnmpCodeGen
import tempfile, os, sys

mib_path='example/EXAMPLE-MIB'
mib_dir=os.path.dirname(os.path.abspath(mib_path))
mib_name=os.path.splitext(os.path.basename(mib_path))[0]
outdir=tempfile.mkdtemp(prefix='mib_py_')
print('mib_dir=', mib_dir)
print('outdir=', outdir)
file_reader = FileReader(mib_dir)
http_reader = HttpReader('https://mibs.snmplabs.com/asn1/')
writer = FileWriter(outdir)
codegen = PySnmpCodeGen()
# Try local reader first
try:
    print('Trying local reader compile...')
    comp = MibCompiler(codegen, file_reader, writer)
    comp.compile(mib_name)
    print('Local compile succeeded')
except Exception as e:
    print('Local compile failed:')
    traceback.print_exc()
    print('\nTrying HTTP reader compile...')
    try:
        comp = MibCompiler(codegen, http_reader, writer)
        comp.compile(mib_name)
        print('HTTP compile succeeded')
    except Exception as e2:
        print('HTTP compile failed:')
        traceback.print_exc()
        print('\nGenerated files in outdir:')
        for root, dirs, files in os.walk(outdir):
            for fn in files:
                p=os.path.join(root,fn)
                print(p, os.path.getsize(p))
        sys.exit(1)
# List generated files
print('Generated files:')
for root, dirs, files in os.walk(outdir):
    for fn in files:
        print(os.path.join(root,fn))
# Dump first 200 lines of generated file if present
genfile = os.path.join(outdir, mib_name+'.py')
if not os.path.exists(genfile):
    genfile = genfile.upper()
if os.path.exists(genfile):
    print('\n---- generated code (first 200 lines) ----')
    with open(genfile,'r',encoding='utf-8') as f:
        for i,line in enumerate(f):
            if i>200: break
            print(line.rstrip())
else:
    print('No generated module found')
