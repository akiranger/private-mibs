import os
import pytest

# Automatically create minimal generated handler files needed by tests at runtime.
# This keeps generated artifacts out of the repository while allowing tests to run.

@pytest.fixture(scope="session", autouse=True)
def generate_handlers():
    handlers_dir = os.path.join(os.path.dirname(__file__), '..', 'src', 'deploy', 'generated_handlers')
    os.makedirs(handlers_dir, exist_ok=True)
    myscalar_path = os.path.join(handlers_dir, 'myScalar.py')
    content = '''# Minimal generated handler for tests
_value = None

def set_myScalar(ctx, value):
    global _value
    _value = value


def get_myScalar(ctx=None):
    return _value
'''
    # write the file if it doesn't exist (avoid overwriting local dev files)
    if not os.path.exists(myscalar_path):
        with open(myscalar_path, 'w', encoding='utf-8') as f:
            f.write(content)
    try:
        yield
    finally:
        # cleanup the generated file if it was created by this fixture
        try:
            if os.path.exists(myscalar_path):
                os.remove(myscalar_path)
        except Exception:
            pass
