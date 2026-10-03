# Changelog

## 0.3.0 - 2026-10-03

* **Added** two reusable workflows, `reusable-release-gate.yml` and `reusable-latest-tag.yml`, so a repository calls them with a few lines instead of copying the gate (inputs: `tag`, `python-version`, `node-version`, `setup`, `config`, `release-config`, `claims-check-ref`). This repository's CI runs both against the checkout under test, and `.claims.json` checks that the workflows and the CI test pin the current version.
* README: "11 repositories" (was 10).

## 0.2.0 - 2026-10-03

* **Added** `expect.latest_tag`: the real value is the highest `v1.2.3`-style tag of a repository (numeric order). For a weekly job that checks the README pins against the newest release.
* **Added** `expect.env`: the real value is an environment variable, optionally cut with a regex. For a pre-release gate that makes the README pins and the package version equal the tag being released (`GITHUB_REF_NAME`).

## 0.1.1 - 2026-10-03

* **Fixed** a regex with alternation (`a@v(\d+)|rev: v(\d+)`) crashed with a traceback because group 1 did not take part in the match; the first group that did is now used. Found by the first roll-out to other repositories.

## 0.1.0 - 2026-10-03

First release. Claims in a JSON file; the real value comes from a command, a regex over another file, a literal or the existence of a git tag; `exact`, `at-least` (with `max_gap`) and `at-most` comparison; every match in the file is checked; text, Markdown, JSON and GitHub annotation output; composite GitHub Action.
