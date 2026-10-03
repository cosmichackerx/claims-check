import json
import subprocess
import sys

import pytest

from claims_check.check import ConfigError, check, load_config
from claims_check.cli import main

PY = f'"{sys.executable}"'


def write(tmp_path, readme, claims, extra=None):
    (tmp_path / "README.md").write_text(readme, encoding="utf-8")
    for name, text in (extra or {}).items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    cfg = tmp_path / ".claims.json"
    cfg.write_text(json.dumps({"claims": claims}), encoding="utf-8")
    return cfg


def claim(**kw):
    base = {"id": "tests", "file": "README.md", "regex": r"(\d+) tests", "expect": {"value": 12}}
    base.update(kw)
    return base


def run(tmp_path, readme, claims, extra=None):
    cfg = write(tmp_path, readme, claims, extra)
    return check(str(tmp_path), load_config(str(cfg)))


def test_exact_number_holds_and_fails(tmp_path):
    assert run(tmp_path, "We have 12 tests.", [claim()]).failed == []
    r = run(tmp_path, "We have 11 tests.", [claim()])
    assert len(r.failed) == 1 and "claims 11" in r.failed[0].message and r.failed[0].line == 1


def test_every_match_is_checked_not_only_the_first(tmp_path):
    r = run(tmp_path, "12 tests here\n\nand 9 tests there\n", [claim()])
    assert [x.ok for x in r.results] == [True, False] and r.failed[0].line == 3


def test_at_least_with_a_gap(tmp_path):
    c = claim(match="at-least", regex=r"(\d+)\+ tests", expect={"value": 103}, max_gap=10)
    assert run(tmp_path, "100+ tests", [c]).failed == []
    assert "stale" in run(tmp_path, "50+ tests", [c]).failed[0].message
    assert run(tmp_path, "104+ tests", [c]).failed  # claims more than exist


def test_command_source_uses_the_last_line_or_a_regex(tmp_path):
    cmd = f'{PY} -c "print(\'collected\'); print(7)"'
    assert run(tmp_path, "7 tests", [claim(expect={"command": cmd})]).failed == []
    cmd2 = f'{PY} -c "print(\'tests: 7 passed\')"'
    assert run(tmp_path, "7 tests", [claim(expect={"command": cmd2, "regex": r"tests: (\d+)"})]).failed == []
    assert run(tmp_path, "8 tests", [claim(expect={"command": cmd2, "regex": r"tests: (\d+)"})]).failed


def test_failing_command_is_a_failure_not_a_pass(tmp_path):
    r = run(tmp_path, "7 tests", [claim(expect={"command": f'{PY} -c "import sys; sys.exit(3)"'})])
    assert r.failed and "command failed" in r.failed[0].message


def test_file_source_for_versions(tmp_path):
    c = {"id": "pin", "file": "README.md", "regex": r"tool@v([\d.]+)", "expect": {"file": "pyproject.toml", "regex": r'^version = "([\d.]+)"'}}
    extra = {"pyproject.toml": 'name = "x"\nversion = "0.3.1"\n'}
    assert run(tmp_path, "uses: o/tool@v0.3.1\n", [c], extra).failed == []
    r = run(tmp_path, "uses: o/tool@v0.3.1\nuses: o/tool@v0.2.0\n", [c], extra)
    assert len(r.failed) == 1 and r.failed[0].line == 2


def test_claim_not_found_fails_unless_optional(tmp_path):
    assert "not found" in run(tmp_path, "nothing here", [claim()]).failed[0].message
    assert run(tmp_path, "nothing here", [claim(optional=True)]).failed == []


def test_missing_file_fails(tmp_path):
    (tmp_path / ".claims.json").write_text(json.dumps({"claims": [claim(file="NOPE.md")]}))
    r = check(str(tmp_path), load_config(str(tmp_path / ".claims.json")))
    assert r.failed and "cannot read" in r.failed[0].message


def test_git_tag_source(tmp_path):
    origin = tmp_path / "origin"
    origin.mkdir()
    for args in (["init", "-q", "-b", "main"], ["-c", "user.name=t", "-c", "user.email=t@e.invalid", "commit", "-q", "--allow-empty", "-m", "x"], ["tag", "v1.2.0"]):
        subprocess.run(["git", *args], cwd=origin, check=True, capture_output=True)
    work = tmp_path / "w"
    work.mkdir()
    c = {"id": "tag", "file": "README.md", "regex": r"tool@v([\d.]+)", "expect": {"git_tag": str(origin)}}
    assert run(work, "tool@v1.2.0", [c]).failed == []
    r = run(work, "tool@v1.3.0", [c])
    assert r.failed and "no such tag" in r.failed[0].message


@pytest.mark.parametrize("bad", [
    {"claims": []}, {"nope": 1}, {"claims": [{"id": "a"}]},
    {"claims": [claim(expect={})]}, {"claims": [claim(expect={"value": 1, "command": "x"})]},
    {"claims": [claim(regex="(")]}, {"claims": [claim(match="roughly")]}, {"claims": [claim(), claim()]},
    {"claims": [claim(expect={"file": "x"})]},
])
def test_bad_config_is_rejected(tmp_path, bad):
    p = tmp_path / "c.json"
    p.write_text(json.dumps(bad))
    with pytest.raises(ConfigError):
        load_config(str(p))


def test_cli_exit_codes_and_formats(tmp_path, capsys):
    cfg = write(tmp_path, "We have 11 tests.", [claim()])
    assert main(["--root", str(tmp_path), "--config", str(cfg)]) == 1
    out = capsys.readouterr().out
    assert out.startswith("FAIL README.md:1") and "0 of 1" in out
    assert main(["--root", str(tmp_path), "--config", str(cfg), "-f", "github"]) == 1
    assert capsys.readouterr().out.startswith("::error file=README.md,line=1")
    main(["--root", str(tmp_path), "--config", str(cfg), "-f", "json"])
    assert json.loads(capsys.readouterr().out)["ok"] is False
    main(["--root", str(tmp_path), "--config", str(cfg), "-f", "markdown"])
    assert "❌" in capsys.readouterr().out
    (tmp_path / "README.md").write_text("12 tests")
    assert main(["--root", str(tmp_path), "--config", str(cfg)]) == 0
    assert main(["--root", str(tmp_path), "--config", str(tmp_path / "missing.json")]) == 2
