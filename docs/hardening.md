# Hardening checklist (OpenSSF Scorecard)

Where this repo stands against the common [OpenSSF Scorecard](https://securityscorecards.dev)
checks. We **do not** quote a Scorecard score — the live badge in the README is
the source of truth once the public repo has run the workflow.

| Check | Status in repo | Automated? | What you must do in GitHub settings |
|---|---|---|---|
| Pinned-Dependencies | ✅ actions pinned by commit SHA; pip deps pinned in `pyproject.toml` | Yes | — |
| Token-Permissions | ✅ `ci.yml` `contents: read`; `scorecard.yml` `read-all` + minimal job perms | Yes | — |
| Dependency-Update-Tool | ✅ `.github/dependabot.yml` (pip + github-actions) | Yes | — |
| Security-Policy | ✅ `SECURITY.md` with private reporting | Yes | Enable **Private vulnerability reporting** (Settings → Code security) |
| CI-Tests | ✅ `ci.yml` runs pytest on PRs | Yes | — |
| Dangerous-Workflow | ✅ no `pull_request_target`, no script injection | Yes | — |
| Binary-Artifacts | ✅ no committed executables; `docs/img/*.png` are generated and reproducible via `scripts/make_figures.py` | Yes | — |
| License | ✅ `LICENSE` (Apache-2.0) | Yes | — |
| SAST | ⏳ CodeQL is a **Roadmap** item (not in this MVP) | Partial | Add CodeQL workflow when ready |
| Branch-Protection | ⚠️ manual | No | Protect `main`: require PRs, require status checks (CI), no force-push |
| Code-Review | ⚠️ manual | No | Require ≥1 approving review before merge |
| Fuzzing | ❌ not set up | No | Out of scope for this MVP |

## Manual steps to do in GitHub before/at submission

1. **Make the repo public** and let the `scorecard.yml` workflow run once so the
   badge populates.
2. **Protect `main`**: Settings → Branches → add rule → require pull request
   reviews + require the CI status check + block force pushes.
3. **Enable private vulnerability reporting**: Settings → Code security.
4. **Enable Dependabot alerts** (and optionally security updates).
5. Confirm **Actions permissions** are read-only by default (Settings → Actions →
   Workflow permissions).

Status of the manual items: `TBD` until configured (tracked in
[`TODO_RESULTS.md`](TODO_RESULTS.md)).
