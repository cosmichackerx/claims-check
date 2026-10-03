# Contributing

    python -m venv .venv && . .venv/bin/activate
    pip install -e . pytest
    pytest -q

Keep it dependency-free (standard library only) and compatible with Python 3.9. A new source of "real values" needs a test with a positive and a negative case, and a line in the README.
