# claims-check

**Fail CI when the numbers and versions written in your README no longer match the repository.** "103 unit tests", "49 oracle cases", `uses: owner/tool@v0.3.1`, "tested on 15 releases": prose
like this is correct on the day it is written and stale a week later. claims-check keeps a list of such sentences in `.claims.json`, finds each one with a regular expression, computes the
real value (from a command, from another file, or from the existence of a git tag) and fails the build on any difference. Zero dependencies (Python 3.9+), a GitHub Action, text / Markdown / JSON / annotation output.

[![CI](https://github.com/cosmichackerx/claims-check/actions/workflows/ci.yml/badge.svg)](https://github.com/cosmichackerx/claims-check/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/cosmichackerx/claims-check?sort=semver)](https://github.com/cosmichackerx/claims-check/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

It is not a link checker and not a spell checker, and it does not understand your prose: it checks exactly the sentences you list. If you rewrite a sentence so that its regex no longer
matches, the check fails ("the claim was not found") instead of silently passing.

## At a glance

|  | Lite (try it in a minute) | Full (keep it in CI) |
|---|---|---|
| How | `pipx install git+https://github.com/cosmichackerx/claims-check`, write a `.claims.json`, run `claims-check` | the [GitHub Action](#github-action) with a job summary table, run after the tests so the commands can reuse build output |

## Validation / results

| What is claimed | Checked against | Size | Result | Not proven |
|---|---|---|---|---|
| Each comparison and source works and fails when it should | Unit tests with a positive and a negative case for each (exact, at-least with gap, command, regex over a file, git tag, missing claim, bad config) | 15+ unit tests | green on Ubuntu, Windows and macOS with Python 3.9, 3.11, 3.13 | Shell commands in claims are written for bash; a Windows-only runner needs `python -c` style commands |
| It catches real drift | It runs in the CI of 10 repositories by the same author: [helm4-ready](https://github.com/cosmichackerx/helm4-ready), [node24-ready](https://github.com/cosmichackerx/node24-ready), [kotlin24-ready](https://github.com/cosmichackerx/kotlin24-ready), [agp9-ready](https://github.com/cosmichackerx/agp9-ready), [gradle10-ready](https://github.com/cosmichackerx/gradle10-ready), [android-target-ready](https://github.com/cosmichackerx/android-target-ready), [dependabot-gaps](https://github.com/cosmichackerx/dependabot-gaps), [gradle-version-catalog-lint](https://github.com/cosmichackerx/gradle-version-catalog-lint), [sha256-ready](https://github.com/cosmichackerx/sha256-ready), [agent-context-diff](https://github.com/cosmichackerx/agent-context-diff) | 10 repositories (android-target-lint has no numeric claims) | First runs found **4 stale README statements in 4 repositories**: node24-ready said "53 tests" twice (109 real), dependabot-gaps said 41 tests (53 real), gradle10-ready said "about 100 cases" (148 tests), kotlin24-ready pinned `@v0.1.3` (0.1.5 current). They also found 1 bug in this tool (an alternation regex crashed, fixed in 0.1.1) and 1 wrong config of mine (a test-count regex that only matched the Node 20 reporter) | Same author, so "stale" means stale against the author's own definition of the count; the 6 other repositories had nothing stale. No external users yet |

## Install and run

```
pipx install git+https://github.com/cosmichackerx/claims-check      # or pip install git+https://github.com/cosmichackerx/claims-check
claims-check                       # reads .claims.json in the current directory
claims-check --config ci/claims.json --root . -f markdown
```

Exit code 0: every claim holds. 1: a claim failed. 2: usage or config error. Formats: `text`, `markdown`, `json`, `github` (annotations).

## The claims file

```json
{
  "claims": [
    {
      "id": "unit tests",
      "file": "README.md",
      "regex": "(\\d+)\\+ unit tests",
      "match": "at-least",
      "max_gap": 15,
      "expect": { "command": "python -m pytest --collect-only -q", "regex": "^(\\d+) tests? collected" }
    },
    {
      "id": "version pin in the README",
      "file": "README.md",
      "regex": "claims-check@v([0-9.]+)",
      "expect": { "file": "pyproject.toml", "regex": "^version = \"([0-9.]+)\"" }
    }
  ]
}
```

* `file` + `regex`: where the claim is written; group 1 is the claimed value. **Every** match is checked (a stale pin in a second code block fails too).
* `expect` (exactly one source of the real value):
  * `command`: run in the root with the shell; the last line of stdout is the value, or group 1 of `regex` (last match). A failing command fails the claim.
  * `file` + `regex`: group 1 of the first match in another file (for example the version in `pyproject.toml` or `package.json`).
  * `value`: a literal.
  * `git_tag`: a repository URL (or path); the claimed value `1.2.0` must exist there as the tag `v1.2.0` (`prefix` changes the `v`). Uses `git ls-remote`.
* `match`: `exact` (default), `at-least` (claimed <= real, for "100+"), `at-most`. `max_gap` makes `at-least` fail when the claim is too far below the real value (a stale "100+" when there are 400).
* `optional: true`: no match in the file is not an error. `ignore_case`.

## GitHub Action

```yaml
- uses: actions/checkout@v7
- run: pip install -e . pytest      # whatever your commands need
- uses: cosmichackerx/claims-check@v0.1.1
  with:
    config: .claims.json
```

Inputs: `config`, `root`, `summary`. The action runs the checker from its own checkout with the runner's Python and installs nothing.

## Limitations (read these)

* It checks only the sentences you list; it does not find claims for you.
* A claim is a regular expression. A rewritten sentence fails with "not found", which is the point, but it means every wording change needs a matching edit of the regex.
* Commands in `.claims.json` run with the shell; see [SECURITY.md](SECURITY.md).
* Numbers only compare as integers (thousands separators `,` and `_` are removed); versions compare as text.

## Related tools

Small, independent tools by the same author for CI hygiene and migrations with a deadline:

* [helm4-ready](https://github.com/cosmichackerx/helm4-ready): Helm 3 to Helm 4 readiness for CI, scripts and Makefiles, tested on real Helm releases.
* [node24-ready](https://github.com/cosmichackerx/node24-ready): GitHub Actions still on the removed Node 20 runtime, and dated runner deadlines.
* [dependabot-gaps](https://github.com/cosmichackerx/dependabot-gaps): manifests your `dependabot.yml` does not cover.
* [sha256-ready](https://github.com/cosmichackerx/sha256-ready), [agent-context-diff](https://github.com/cosmichackerx/agent-context-diff), [kotlin24-ready](https://github.com/cosmichackerx/kotlin24-ready), [agp9-ready](https://github.com/cosmichackerx/agp9-ready), [gradle10-ready](https://github.com/cosmichackerx/gradle10-ready).

## License

MIT, see [LICENSE](LICENSE).
