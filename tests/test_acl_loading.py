import tempfile
import json
import os
import unittest

from scaffold import pysnmp_agent


class TestAclLoading(unittest.TestCase):
    def test_load_acl_from_file_and_check(self):
        data = {
            '1.2.3.4': {'read': True, 'write': ['admin']},
            'testhandler': {'read': ['public'], 'write': ['admin']}
        }
        fd, path = tempfile.mkstemp(suffix='.json')
        os.close(fd)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f)
            n = pysnmp_agent.load_acl_from_file(path)
            self.assertEqual(n, 2)
            # check read allowed by default principal absent
            self.assertTrue(pysnmp_agent._check_acl('1.2.3.4', 'get', None))
            # write requires principal in list
            self.assertFalse(pysnmp_agent._check_acl('1.2.3.4', 'set', None))
            self.assertTrue(pysnmp_agent._check_acl('1.2.3.4', 'set', {'principal': 'admin'}))
            # handler name check
            self.assertTrue(pysnmp_agent._check_acl('testhandler', 'get', {'principal': 'public'}))
        finally:
            try:
                os.remove(path)
            except Exception:
                pass


if __name__ == '__main__':
    unittest.main()
