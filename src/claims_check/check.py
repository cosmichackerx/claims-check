"""Check claims written in prose (README numbers, version pins) against the repository.

A claim is: a regular expression whose first group is the claimed value, in a file, and where the real value comes from (a command, a regex over another file,
a literal, or the existence of a git tag). Every match in the file is checked, not only the first.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass, field


class ConfigError(Exception):
    pass


@dataclass
class Result:
    id: str
    ok: bool
    file: str
    line: int
    message: str
    claimed: str = ""
    actual: str = ""


@dataclass
class Report:
    results: list = field(default_factory=list)

    @property
    def failed(self):
        return [r for r in self.results if not r.ok]


def _num(s: str):
    t = s.strip().replace(",", "").replace("_", "")
    return int(t) if re.fullmatch(r"\d+", t) else None


def load_config(path: str) -> list:
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except OSError as e:
        raise ConfigError(f"cannot read {path}: {e}")
    except ValueError as e:
        raise ConfigError(f"{path} is not valid JSON: {e}")
    claims = data.get("claims") if isinstance(data, dict) else None
    if not isinstance(claims, list) or not claims:
        raise ConfigError(f'{path}: expected {{"claims": [ ... ]}} with at least one claim')
    seen = set()
    for i, c in enumerate(claims):
        for key in ("id", "file", "regex", "expect"):
            if key not in c:
                raise ConfigError(f"{path}: claim #{i + 1} lacks '{key}'")
        if c["id"] in seen:
            raise ConfigError(f"{path}: duplicate claim id '{c['id']}'")
        seen.add(c["id"])
        kinds = [k for k in ("command", "file", "value", "git_tag") if k in c["expect"]]
        if len(kinds) != 1:
            raise ConfigError(f"{path}: claim '{c['id']}': 'expect' needs exactly one of command, file (+regex), value, git_tag")
        if kinds[0] == "file" and "regex" not in c["expect"]:
            raise ConfigError(f"{path}: claim '{c['id']}': expect.file needs expect.regex")
        try:
            re.compile(c["regex"], re.M)
            if "regex" in c["expect"]:
                re.compile(c["expect"]["regex"], re.M)
        except re.error as e:
            raise ConfigError(f"{path}: claim '{c['id']}': bad regex: {e}")
        if c.get("match", "exact") not in ("exact", "at-least", "at-most"):
            raise ConfigError(f"{path}: claim '{c['id']}': match must be exact, at-least or at-most")
    return claims


def _read(root: str, rel: str) -> str:
    with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as fh:
        return fh.read()


def _actual(claim: dict, root: str, claimed: str):
    """(value, description) of the real value; raises RuntimeError with the reason when it cannot be determined."""
    ex = claim["expect"]
    if "value" in ex:
        return str(ex["value"]), "value in config"
    if "file" in ex:
        text = _read(root, ex["file"])
        m = re.search(ex["regex"], text, re.M)
        if not m:
            raise RuntimeError(f"no match for {ex['regex']!r} in {ex['file']}")
        return (m.group(1) if m.groups() else m.group(0)), f"{ex['file']}"
    if "command" in ex:
        p = subprocess.run(ex["command"], shell=True, cwd=root, capture_output=True, text=True, timeout=int(ex.get("timeout", 600)))
        if p.returncode != 0:
            raise RuntimeError(f"command failed ({p.returncode}): {ex['command']}\n{(p.stderr or p.stdout).strip()[-400:]}")
        out = p.stdout.strip()
        if "regex" in ex:
            ms = re.findall(ex["regex"], out, re.M)
            if not ms:
                raise RuntimeError(f"no match for {ex['regex']!r} in the output of: {ex['command']}")
            last = ms[-1]
            out = last if isinstance(last, str) else last[0]
        elif not out:
            raise RuntimeError(f"no output from: {ex['command']}")
        else:
            out = out.splitlines()[-1].strip()
        return out, f"`{ex['command']}`"
    # git_tag: the claimed value is a version; the tag v<claimed> must exist in the repository at that URL
    tag = ex.get("prefix", "v") + claimed
    p = subprocess.run(["git", "ls-remote", "--tags", ex["git_tag"], f"refs/tags/{tag}"], capture_output=True, text=True, timeout=60)
    if p.returncode != 0:
        raise RuntimeError(f"git ls-remote failed for {ex['git_tag']}: {p.stderr.strip()[-200:]}")
    return (claimed if p.stdout.strip() else "(no such tag)"), f"tag {tag} in {ex['git_tag']}"


def check(root: str, claims: list) -> Report:
    rep = Report()
    for c in claims:
        rel = c["file"]
        try:
            text = _read(root, rel)
        except OSError as e:
            rep.results.append(Result(c["id"], False, rel, 0, f"cannot read {rel}: {e}"))
            continue
        flags = re.M | (re.I if c.get("ignore_case") else 0)
        matches = list(re.finditer(c["regex"], text, flags))
        if not matches:
            if not c.get("optional"):
                rep.results.append(Result(c["id"], False, rel, 0, f"the claim was not found in {rel} (regex {c['regex']!r}); the sentence changed or the config is stale"))
            continue
        cache = {}
        for m in matches:
            claimed = (m.group(1) if m.groups() else m.group(0)).strip()
            line = text.count("\n", 0, m.start()) + 1
            key = claimed if "git_tag" in c["expect"] else ""
            if key not in cache:
                try:
                    cache[key] = _actual(c, root, claimed)
                except (RuntimeError, OSError, subprocess.TimeoutExpired) as e:
                    cache[key] = e
            got = cache[key]
            if isinstance(got, Exception):
                rep.results.append(Result(c["id"], False, rel, line, f"cannot determine the real value: {got}", claimed))
                continue
            actual, source = got
            mode = c.get("match", "exact")
            a, b = _num(claimed), _num(actual)
            if mode == "exact":
                ok = (a == b) if (a is not None and b is not None) else (claimed == actual.strip())
                why = f"claims {claimed}, {source} says {actual}"
            else:
                if a is None or b is None:
                    rep.results.append(Result(c["id"], False, rel, line, f"match '{mode}' needs numbers; got {claimed!r} and {actual!r}", claimed, actual))
                    continue
                ok = a <= b if mode == "at-least" else a >= b
                gap = b - a if mode == "at-least" else a - b
                if ok and "max_gap" in c and gap > c["max_gap"]:
                    ok = False
                    why = f"claims {claimed}+, {source} says {actual}: {gap} apart, more than the allowed {c['max_gap']} (the sentence is stale)"
                else:
                    why = f"claims {claimed} ({mode}), {source} says {actual}"
            rep.results.append(Result(c["id"], ok, rel, line, why, claimed, actual))
    return rep
