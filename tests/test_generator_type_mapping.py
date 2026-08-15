from src.mib import generator as gen


def test_snmp_type_to_sql():
    assert gen._snmp_type_to_sql('INTEGER32') == 'INTEGER'
    assert gen._snmp_type_to_sql('Unsigned32') == 'INTEGER'
    assert gen._snmp_type_to_sql('OCTET STRING') == 'TEXT'
    assert gen._snmp_type_to_sql('OBJECT IDENTIFIER') == 'TEXT'
    assert gen._snmp_type_to_sql('Counter32') == 'INTEGER'
    assert gen._snmp_type_to_sql('Counter64') == 'INTEGER'
    assert gen._snmp_type_to_sql(None) == 'TEXT'


def test_parse_snmp_syntax_constraints():
    base, c = gen._parse_snmp_syntax('OCTET STRING (SIZE (0..64))')
    assert 'max_length' in c and c['max_length'] == 64
    base2, c2 = gen._parse_snmp_syntax('INTEGER (0..255)')
    assert 'min' in c2 and c2['min'] == 0 and c2['max'] == 255
