import unittest
import os

from scaffold import pysnmp_agent


class TestPysnmpIntegration(unittest.TestCase):
    def setUp(self):
        # write a test handler module dynamically so tests can run without committing it
        import os
        handlers_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scaffold', 'generated_handlers')
        os.makedirs(handlers_dir, exist_ok=True)
        fh = os.path.join(handlers_dir, 'testscalar.py')
        with open(fh, 'w', encoding='utf-8') as f:
            f.write("""# dynamic handler for tests
_val = None

def get_testscalar(ctx):
    return _val


def set_testscalar(ctx, v):
    global _val
    _val = v
    return True
""")
        pysnmp_agent.OID_MAP['1.2.3.4'] = 'testscalar'

    def tearDown(self):
        # remove the dynamic handler file
        import os
        fh = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scaffold', 'generated_handlers', 'testscalar.py')
        try:
            os.remove(fh)
        except Exception:
            pass

    def test_get_set_flow(self):
        # ensure initial is None
        v = pysnmp_agent.handle_get('1.2.3.4')
        self.assertIsNone(v)
        # set a value
        pysnmp_agent.handle_set('1.2.3.4', 'hello')
        v = pysnmp_agent.handle_get('1.2.3.4')
        self.assertEqual(v, 'hello')


if __name__ == '__main__':
    unittest.main()
