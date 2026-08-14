import unittest
import sys
import types

from scaffold import pysnmp_agent

class FakeConfig:
    def __init__(self):
        # provide constants used by mapping
        self.usmNoAuthProtocol = object()
        self.usmHMACMD5AuthProtocol = object()
        self.usmHMACSHAAuthProtocol = object()
        self.usmNoPrivProtocol = object()
        self.usmDESPrivProtocol = object()
        self.usmAesCfb128Protocol = object()
        self.add_calls = []
    def addV3User(self, snmpEngine, username, authProtocol=None, authKey=None, privProtocol=None, privKey=None):
        # record call
        self.add_calls.append((snmpEngine, username, authProtocol, authKey, privProtocol, privKey))

class TestUsmRegistration(unittest.TestCase):
    def setUp(self):
        # ensure clean users
        pysnmp_agent._USM_USERS.clear()

    def test_register_with_pysnmp_mock(self):
        # prepare fake pysnmp.entity.config
        fake_config = FakeConfig()
        fake_entity = types.SimpleNamespace(config=fake_config)
        fake_pysnmp = types.SimpleNamespace(entity=fake_entity)
        sys.modules['pysnmp'] = types.ModuleType('pysnmp')
        sys.modules['pysnmp.entity'] = types.ModuleType('pysnmp.entity')
        sys.modules['pysnmp.entity.config'] = fake_config

        try:
            pysnmp_agent.register_usm_user('alice', auth_protocol='SHA', auth_key='a1', priv_protocol='AES', priv_key='p1')
            registered = pysnmp_agent.register_usm_with_pysnmp(snmpEngine='engine1')
            self.assertIn('alice', registered)
            # verify addV3User was called
            self.assertEqual(len(fake_config.add_calls), 1)
            call = fake_config.add_calls[0]
            self.assertEqual(call[1], 'alice')
        finally:
            # cleanup
            for k in ('pysnmp.entity.config', 'pysnmp.entity', 'pysnmp'):
                try:
                    del sys.modules[k]
                except KeyError:
                    pass

if __name__ == '__main__':
    unittest.main()
