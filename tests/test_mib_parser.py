import unittest
from src.mib.mib_parser import parse_mib_to_json
import os

class TestMibParser(unittest.TestCase):
    def test_simple_parse(self):
        sample = """
MY-MIB DEFINITIONS ::= BEGIN
myScalar OBJECT-TYPE
    SYNTAX      INTEGER
    MAX-ACCESS  read-only
    DESCRIPTION "A simple scalar"
    ::= { myModule 1 }
END
"""
        p = os.path.join(os.path.dirname(__file__), 'sample_mib.txt')
        with open(p, 'w', encoding='utf-8') as f:
            f.write(sample)
        schema = parse_mib_to_json(p)
        self.assertIn('objects', schema)
        self.assertEqual(len(schema['objects']), 1)
        obj = schema['objects'][0]
        self.assertEqual(obj['name'], 'myScalar')
        self.assertEqual(obj['syntax'].strip(), 'INTEGER')
        self.assertIn('simple scalar', obj['description'])

if __name__ == '__main__':
    unittest.main()
