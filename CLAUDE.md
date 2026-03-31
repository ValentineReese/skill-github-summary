# skill-github-summary

A Claude Code skill that summarizes GitHub activity.

## Structure

- `skill.md` — Skill definition (loaded as the prompt)
- `fetch_commits.py` — Python script to fetch GitHub activity via REST API

## Requirements

- Environment variable `GITHUB_PAT` must be set to a GitHub Personal Access Token with `repo` scope
- Python 3.6+ (uses only stdlib: `urllib`, `json`, `argparse`)

## Two modes

### 1. `user-commits` — Summarize a user's commits across repos
```bash
python3 fetch_commits.py user-commits --since 2026-03-01 --until 2026-03-31 --repos owner/repo1
```

### 2. `repo-activity` — Summarize a specific repo's commits, PRs, and issues
```bash
python3 fetch_commits.py repo-activity owner/repo --since 2026-03-01 --until 2026-03-31 --author username --types commits pulls issues
```
