from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .check import ConfigError, check, load_config


def render_text(rep) -> str:
    out = []
    for r in rep.results:
        out.append(f"{'ok  ' if r.ok else 'FAIL'} {r.file}:{r.line}  {r.id}: {r.message}")
    n = len(rep.results)
    out.append(f"{n - len(rep.failed)} of {n} claim check(s) hold." if n else "No claim was checked.")
    return "\n".join(out) + "\n"


def render_markdown(rep) -> str:
    out = ["## claims-check", "", "| | Claim | Where | Detail |", "|---|---|---|---|"]
    for r in rep.results:
        out.append(f"| {'✅' if r.ok else '❌'} | `{r.id}` | `{r.file}:{r.line}` | {r.message.replace('|', chr(92) + '|')} |")
    out += ["", f"{len(rep.results) - len(rep.failed)} of {len(rep.results)} hold."]
    return "\n".join(out) + "\n"


def render_github(rep) -> str:
    def esc(s):
        return s.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    return "".join(f"::error file={r.file},line={max(r.line, 1)},title=claims-check {r.id}::{esc(r.message)}\n" for r in rep.failed)


def render_json(rep) -> str:
    return json.dumps({"tool": "claims-check", "version": __version__, "ok": not rep.failed,
                       "results": [{"id": r.id, "ok": r.ok, "file": r.file, "line": r.line, "claimed": r.claimed, "actual": r.actual, "message": r.message} for r in rep.results]}, indent=2) + "\n"


FORMATS = {"text": render_text, "markdown": render_markdown, "github": render_github, "json": render_json}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="claims-check", description="Fail when numbers and versions written in a README no longer match the repository.")
    p.add_argument("--config", default=".claims.json", help="claims file (default: .claims.json)")
    p.add_argument("--root", default=".", help="repository root (default: .)")
    p.add_argument("-f", "--format", choices=sorted(FORMATS), default="text")
    p.add_argument("--version", action="version", version=f"claims-check {__version__}")
    a = p.parse_args(argv)
    try:
        import os
        claims = load_config(a.config if os.path.isabs(a.config) or os.path.exists(a.config) else os.path.join(a.root, a.config))
    except ConfigError as e:
        print(f"claims-check: {e}", file=sys.stderr)
        return 2
    rep = check(a.root, claims)
    sys.stdout.write(FORMATS[a.format](rep))
    return 1 if rep.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
