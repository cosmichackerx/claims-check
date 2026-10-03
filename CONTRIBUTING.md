# Contributing

    python -m venv .venv && . .venv/bin/activate
    pip install -e . pytest
    pytest -q

Keep it dependency-free (standard library only) and compatible with Python 3.9. A new source of "real values" needs a test with a positive and a negative case, and a line in the README.
* Releasing: bump the version and the README pins in a PR, merge when green, then run **Actions > Release gate** with the new tag (for example `v1.2.3`) *before* you create the tag. The same check runs again on the tag, and a weekly job (`claims-latest.yml`) fails when the README pins an older release than the newest tag.
