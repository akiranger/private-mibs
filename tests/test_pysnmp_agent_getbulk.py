import scaffold.pysnmp_agent as agent


def test_handle_getbulk_basic(monkeypatch):
    # prepare a simple OID_MAP with deterministic handlers
    agent.OID_MAP.clear()

    # create a fake handler module with get and next helpers
    class FakeHandler:
        def __init__(self):
            self.rows = {1: 'one', 2: 'two', 3: 'three'}

        def get_fake(self, oid, ctx=None):
            return 'scalar'

        def next_oid_fake(self, current):
            # simple rotate: always return 1 for demonstration
            return 1

    # write fake module into scaffold.generated_handlers cache
    fake = FakeHandler()
    agent.OID_MAP['1.3.6.1.4.1.example.1.1'] = 'fake'

    # monkeypatch load_handler to return our fake instance
    monkeypatch.setattr(agent, 'load_handler', lambda name: fake)

    # test non-repeater: should call handle_getnext once
    res = agent.handle_getbulk(['1.3.6.1.4.1.example.1.1'], non_repeaters=1, max_repetitions=2)
    assert isinstance(res, list)

    # test repeating: should attempt at least one repetition
    res2 = agent.handle_getbulk(['1.3.6.1.4.1.example.1.1'], non_repeaters=0, max_repetitions=2)
    assert isinstance(res2, list)
