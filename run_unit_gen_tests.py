import scaffold.generator as gen

failed = False
try:
    test_vals = [
        ('INTEGER32', 'INTEGER'),
        ('Unsigned32', 'INTEGER'),
        ('OCTET STRING', 'TEXT'),
        ('OBJECT IDENTIFIER', 'TEXT'),
        ('Counter32', 'INTEGER'),
        ('Counter64', 'INTEGER'),
    ]
    for inp, exp in test_vals:
        r = gen._snmp_type_to_sql(inp)
        print(inp, '->', r)
        if r != exp:
            print('FAIL:', inp, 'expected', exp, 'got', r)
            failed = True
    base, c = gen._parse_snmp_syntax('OCTET STRING (SIZE (0..64))')
    print('parse', base, c)
    if c.get('max_length') != 64:
        print('FAIL: expected max_length 64')
        failed = True
    base2, c2 = gen._parse_snmp_syntax('INTEGER (0..255)')
    print('parse', base2, c2)
    if c2.get('min') != 0 or c2.get('max') != 255:
        print('FAIL: integer range')
        failed = True
except Exception as e:
    print('EXCEPTION', e)
    failed = True

if failed:
    raise SystemExit(1)
print('ALL OK')
