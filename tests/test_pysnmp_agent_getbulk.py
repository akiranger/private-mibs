from src.runtime import pysnmp_agent as agent


def test_handle_getbulk_basic(monkeypatch):
    # prepare a simple OID_MAP with deterministic handlers
    agent.OID_MAP.clear()

    # create a fake handler module with get and next helpers
    class FakeHandler:
        def __init__(self):
            # simulate a small table with ids 1..3
            self._max = 3

        def get_fake(self, oid, ctx=None):
            # return a value indicating which concrete OID was requested
            return f"value_for_{oid}"

        def next_oid_fake(self, current):
            # if current is None, return first index
            if current is None:
                return 1
            try:
                cur = int(current)
            except Exception:
                return None
            if cur >= self._max:
                return None
            return cur + 1

    fake = FakeHandler()
    agent.OID_MAP['1.3.6.1.4.1.999.1.1'] = 'fake'

    # monkeypatch load_handler to return our fake instance
    monkeypatch.setattr(agent, 'load_handler', lambda name: fake)

    # non-repeater: should return the first table row as resolved OID
    res = agent.handle_getbulk(['1.3.6.1.4.1.example.1.1'], non_repeaters=1, max_repetitions=2)
    assert isinstance(res, list)
    assert len(res) >= 1
    # first returned resolved oid should contain the base and index .1
    assert any(r[0].startswith('1.3.6.1.4.1.example.1.1') for r in res)

    # repeating: should attempt to return up to max_repetitions rows
    res2 = agent.handle_getbulk(['1.3.6.1.4.1.example.1.1'], non_repeaters=0, max_repetitions=3)
    assert isinstance(res2, list)
    # should have at least one resolved row and values should match fake.get_fake output
    assert len(res2) >= 1
    for oid, val in res2:
        assert val == f"value_for_{oid}"
