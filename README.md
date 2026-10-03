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
| It catches real drift | It runs in the CI of 12 repositories by the same author: [helm4-ready](https://github.com/cosmichackerx/helm4-ready), [node24-ready](https://github.com/cosmichackerx/node24-ready), [kotlin24-ready](https://github.com/cosmichackerx/kotlin24-ready), [agp9-ready](https://github.com/cosmichackerx/agp9-ready), [gradle10-ready](https://github.com/cosmichackerx/gradle10-ready), [android-target-ready](https://github.com/cosmichackerx/android-target-ready), [dependabot-gaps](https://github.com/cosmichackerx/dependabot-gaps), [gradle-version-catalog-lint](https://github.com/cosmichackerx/gradle-version-catalog-lint), [sha256-ready](https://github.com/cosmichackerx/sha256-ready), [agent-context-diff](https://github.com/cosmichackerx/agent-context-diff), [android-target-lint](https://github.com/cosmichackerx/android-target-lint), [kafka4-ready](https://github.com/cosmichackerx/kafka4-ready) | 12 repositories. Each also has a pre-release gate and a weekly latest-tag check, as thin callers of this repo's reusable workflows since v0.3.0 | First runs found **5 stale README statements in 5 repositories**: node24-ready said "53 tests" twice (109 real), dependabot-gaps said 41 tests (53 real), gradle10-ready said "about 100 cases" (148 tests), kotlin24-ready pinned `@v0.1.3` (0.1.5 current), android-target-lint named a `0.1.0` jar in a build comment (0.2.2 current). They also found 1 bug in this tool (an alternation regex crashed, fixed in 0.1.1) and 1 wrong config of mine (a test-count regex that only matched the Node 20 reporter) | Same author, so "stale" means stale against the author's own definition of the count; the 7 other repositories had nothing stale. No external users yet |

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
  * `latest_tag`: a repository URL (or path); the real value is the **highest** `v1.2.3`-style tag there (numeric order, `prefix` changes the `v`). Use it for a weekly "the README pins the newest release" job.
  * `env`: the value of an environment variable, optionally cut with `regex` (group 1). Use it for a **pre-release gate**: `{"env": "GITHUB_REF_NAME", "regex": "^v([0-9.]+)$"}` makes the README pin and the package version equal the tag being released.
* `match`: `exact` (default), `at-least` (claimed <= real, for "100+"), `at-most`. `max_gap` makes `at-least` fail when the claim is too far below the real value (a stale "100+" when there are 400).
* `optional: true`: no match in the file is not an error. `ignore_case`.

## GitHub Action

```yaml
- uses: actions/checkout@v7
- run: pip install -e . pytest      # whatever your commands need
- uses: cosmichackerx/claims-check@v0.3.0
  with:
    config: .claims.json
```

Inputs: `config`, `root`, `summary`. The action runs the checker from its own checkout with the runner's Python and installs nothing.

## Reusable workflows (release gate and weekly pin check)

Instead of copying a pre-release gate into every repository, call the two reusable workflows of this repository. Add `.claims-release.json` (pins and version against the tag, `expect.env`) and `.claims-latest.json` (`expect.latest_tag`) as described above, then:

```yaml
# .github/workflows/release-gate.yml
name: Release gate
on:
  workflow_dispatch:
    inputs:
      tag: {description: "Tag you are about to create, for example v1.2.3", required: true}
  push:
    tags: ["v*"]
permissions:
  contents: read
jobs:
  gate:
    uses: cosmichackerx/claims-check/.github/workflows/reusable-release-gate.yml@v0.3.0
    with:
      tag: ${{ inputs.tag || github.ref_name }}
      python-version: "3.13"            # optional: Python / Node for the commands in .claims.json
      setup: python -m pip install pytest .   # optional: any setup command
```

```yaml
# .github/workflows/claims-latest.yml
name: README pins vs newest tag
on:
  schedule: [{cron: "17 5 * * 1"}]
  workflow_dispatch:
permissions:
  contents: read
jobs:
  pins:
    uses: cosmichackerx/claims-check/.github/workflows/reusable-latest-tag.yml@v0.3.0
```

Inputs of the gate: `tag` (required), `python-version`, `node-version`, `setup`, `config` (default `.claims.json`), `release-config` (default `.claims-release.json`), `claims-check-ref` (the ref of this repository whose action runs the checks, default the release the workflow file belongs to). The workflows check out your repository and a second copy of this one into `.claims-check/`, so no action reference has to be edited per repository. Pin the workflow by tag (`@v0.3.0`) or by commit SHA. A caller needs only `contents: read`.

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
