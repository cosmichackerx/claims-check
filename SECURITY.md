# Security

claims-check reads the claims file and the files it names, and **runs the shell commands written in that claims file** (`expect.command`) in the repository root. Treat `.claims.json` like a CI script: review changes to it, and do not run claims-check on a claims file from a pull request you do not trust with secrets in the environment (the GitHub Action reads it from the checked-out ref, as any workflow step would). It makes no network request except `git ls-remote` for `expect.git_tag`.

Found a vulnerability? Please use GitHub's private vulnerability reporting for this repository ("Security" tab, "Report a vulnerability") instead of a public issue.
