# skill-github-summary

A Claude Code skill that summarizes GitHub activity.

## Structure

- `skill.md` — Skill definition (loaded as the prompt)
- `fetch_activity.sh` — Shell script to fetch GitHub activity via `gh` CLI

## Requirements

- `gh` — [GitHub CLI](https://cli.github.com/), authenticated via `gh auth login`
- `jq` — [Command-line JSON processor](https://jqlang.github.io/jq/)

## Two modes

### 1. `user-commits` — Summarize a user's commits across repos
```bash
bash fetch_activity.sh user-commits --since 2026-03-01 --until 2026-03-31 --repos owner/repo1
```

### 2. `repo-activity` — Summarize a specific repo's commits, PRs, and issues
```bash
bash fetch_activity.sh repo-activity owner/repo --since 2026-03-01 --until 2026-03-31 --author username --types commits pulls issues
```
