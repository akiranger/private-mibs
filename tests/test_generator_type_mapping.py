import scaffold.generator as gen


def test_snmp_type_to_sql():
    assert gen._snmp_type_to_sql('INTEGER32') == 'INTEGER'
    assert gen._snmp_type_to_sql('Unsigned32') == 'INTEGER'
    assert gen._snmp_type_to_sql('OCTET STRING') == 'TEXT'
    assert gen._snmp_type_to_sql('OBJECT IDENTIFIER') == 'TEXT'
    assert gen._snmp_type_to_sql('Counter32') == 'INTEGER'
    assert gen._snmp_type_to_sql(None) == 'TEXT'
