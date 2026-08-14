import scaffold.pysnmp_agent as agent

class FakeHandler:
    def __init__(self):
        self._max = 3
    def get_fake(self, oid, ctx=None):
        return f"value_for_{oid}"
    def next_oid_fake(self, current):
        if current is None:
            return 1
        try:
            cur = int(current)
        except Exception:
            return None
        if cur >= self._max:
            return None
        return cur + 1

# Prepare map and monkeypatch load_handler
agent.OID_MAP.clear()
agent.OID_MAP['1.3.6.1.4.1.999.1.1'] = 'fake'
agent.load_handler = lambda name: FakeHandler()

print('Running smoke test for handle_getbulk...')
res = agent.handle_getbulk(['1.3.6.1.4.1.example.1.1'], non_repeaters=0, max_repetitions=5)
print('Result len:', len(res))
for oid, val in res:
    print(oid, '->', val)
