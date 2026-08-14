# Minimal generated handler for tests
_value = None

def set_myScalar(ctx, value):
    global _value
    _value = value


def get_myScalar(ctx=None):
    return _value
