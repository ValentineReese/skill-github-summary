# skill-github-summary

A Claude Code skill that summarizes GitHub activity — user commits across repos, or a specific repo's commits/PRs/issues.

## Prerequisites

- Python 3.6+ (only uses stdlib: `urllib`, `json`, `argparse`)
- (Optional) Set `GITHUB_PAT` environment variable to a GitHub Personal Access Token

### Token setup

```bash
export GITHUB_PAT=ghp_xxxxxx
```

| Token status | Available features |
|---|---|
| **Classic token** with `repo` scope | All features, including private repos |
| **Fine-grained token** | Depends on configured repo access and permissions (Contents/PRs/Issues read) |
| **No token** | Only `repo-activity` mode for public repos (rate limit: 60 req/hour) |

> `user-commits` mode always requires a token (needs `/user` API to identify the authenticated user).

## Two modes

### Mode 1: `user-commits` — Summarize your commits across repos

Fetches the authenticated user's commits. When specific repos are provided, uses the Repo Commits API (works with private repos); otherwise uses the Search API to discover commits across all repos.

```bash
# All repos, last 7 days (default)
python3 fetch_commits.py user-commits

# Specific date range
python3 fetch_commits.py user-commits --since 2026-02-01 --until 2026-03-31

# Filter by repos (supports private repos)
python3 fetch_commits.py user-commits --since 2026-03-01 --until 2026-03-31 --repos owner/repo1 owner/repo2
```

### Mode 2: `repo-activity` — Summarize a repo's commits, PRs, and issues

Fetches activity for a specific repository. Supports filtering by author and activity type.

```bash
# All activity for a repo, last 7 days
python3 fetch_commits.py repo-activity owner/repo

# Filter by date range and author
python3 fetch_commits.py repo-activity owner/repo --since 2026-03-01 --until 2026-03-31 --author username

# Only fetch specific activity types
python3 fetch_commits.py repo-activity owner/repo --types commits pulls
python3 fetch_commits.py repo-activity owner/repo --types issues
python3 fetch_commits.py repo-activity owner/repo --types commits pulls issues
```

## Usage as a Claude Code skill

When used as a Claude Code skill, you can invoke it with natural language:

```
# Summarize your own commits
总结我过去一周的提交
summarize my commits for March 2026 by week
总结我在 owner/repo 这个月的提交，按天

# Summarize a repo's activity
总结 facebook/react 这个月的改动
看看 vercel/next.js 最近一周有哪些 PR 和 issue
总结 @torvalds 在 torvalds/linux 上个月的活动
```

The skill supports summary granularity by **day**, **week**, or **month**.

## Project structure

```
├── skill.md           # Skill definition (prompt for Claude Code)
├── fetch_commits.py   # Python script to fetch GitHub activity via REST API
├── CLAUDE.md          # Project instructions for Claude Code
└── README.md          # This file
```
