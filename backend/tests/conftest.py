"""Shared fixtures: isolate rate-limiter state between tests.

The analyze/ask/report limiters are module-level in main.py. Without a
reset, fast consecutive test calls trip the 5/min analyze window and
fail with 429s that have nothing to do with the code under test.
Production limiter behavior is untouched.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def reset_rate_limiters():
    import main as app_main

    app_main.analyze_limiter.reset()
    app_main.ask_limiter.reset()
    app_main.report_limiter.reset()
    yield
    app_main.analyze_limiter.reset()
    app_main.ask_limiter.reset()
    app_main.report_limiter.reset()
