---
name: github-summary
description: Summarize GitHub activity — user commits across repos, or a specific repo's commits/PRs/issues with author and date filtering.
---

# GitHub Activity Summary Skill

You are tasked with fetching and summarizing GitHub activity. There are two modes:

1. **User commits** — summarize the authenticated user's commits across repos
2. **Repo activity** — summarize a specific public repo's commits, PRs, and issues

## Setup

- If `GITHUB_PTA` environment variable is set, all features are available (including private repos and user-commits mode).
- If `GITHUB_PTA` is **not set**, only **repo-activity** mode for **public repositories** is available (unauthenticated access). Note: GitHub unauthenticated API has a lower rate limit (60 requests/hour).
- **user-commits** mode always requires `GITHUB_PTA` because it needs to identify the authenticated user.

---

## Mode 1: User Commits

Summarize the authenticated user's commit history across repositories.

### Parse the request

- **Date range**: `--since` and `--until` (YYYY-MM-DD). Defaults: last 7 days.
- **Repo scope**: `--repos owner/repo1 owner/repo2 ...`. Default: all repos.
- **Summary granularity**: daily, weekly, or monthly. Default: daily.

### Fetch data

```bash
python3 /Users/bobong/Codes/AI/skills/skill-github-summary/fetch_commits.py user-commits --since <YYYY-MM-DD> --until <YYYY-MM-DD> [--repos owner/repo1 owner/repo2 ...]
```

### Output format

```
## GitHub Commit Summary for @{username}
**Period**: {since} ~ {until}
**Total commits**: {count}

### {period label} (e.g., 2026-03-25 / Week 13 / March 2026)

**{repo_name}** ({commit_count} commits)
- {concise summary of changes based on commit messages}
```

---

## Mode 2: Repo Activity

Summarize a specific public repository's activity including commits, PRs, and issues.

### Parse the request

- **Repo** (required): `owner/repo`
- **Date range**: `--since` and `--until` (YYYY-MM-DD). Defaults: last 7 days.
- **Author filter**: `--author username`. Default: all contributors.
- **Activity types**: `--types commits pulls issues`. Default: all three.
- **Summary granularity**: daily, weekly, or monthly. Default: daily.

### Fetch data

```bash
python3 /Users/bobong/Codes/AI/skills/skill-github-summary/fetch_commits.py repo-activity owner/repo --since <YYYY-MM-DD> --until <YYYY-MM-DD> [--author username] [--types commits pulls issues]
```

### Output format

```
## Repo Activity Summary for {owner/repo}
**Period**: {since} ~ {until}
**Author filter**: {author or "all"}

### Commits ({count})
| Date | Author | Summary |
|------|--------|---------|
| ... | ... | ... |

Or grouped by period:

#### {period label}
- **@{author}**: {concise summary of commits}

### Pull Requests ({count})
| # | Title | Author | State | Created | Labels |
|---|-------|--------|-------|---------|--------|
| ... | ... | ... | ... | ... | ... |

**Summary**: {high-level overview: how many opened, merged, closed; key PRs}

### Issues ({count})
| # | Title | Author | State | Created | Comments | Labels |
|---|-------|--------|-------|---------|----------|--------|
| ... | ... | ... | ... | ... | ... | ... |

**Summary**: {high-level overview: how many opened, closed; hot topics}
```

---

## Guidelines

- Merge related commit messages into concise descriptions rather than listing every commit verbatim.
- Highlight notable work: new features, bug fixes, refactors, dependency updates.
- If many small commits exist (e.g., "fix typo"), group them as "minor fixes and updates".
- For PRs, highlight merged PRs as the most impactful; note any long-open PRs.
- For issues, highlight active discussions (high comment count) and recently closed issues.
- Use the user's language for the summary (match the language of their request).
- When the user asks about a "repo's activity/changes" without specifying mode, use **repo-activity**.
- When the user asks about "my commits" without a specific repo focus, use **user-commits**.

## Example invocations

### User commits mode
- "总结我过去一周的提交" → user-commits, daily, last 7 days, all repos
- "summarize my commits for March 2026 by week" → user-commits, weekly, 2026-03-01 to 2026-03-31
- "总结我在 owner/repo 这个月的提交，按天" → user-commits, daily, current month, specific repo

### Repo activity mode
- "总结 facebook/react 这个月的改动" → repo-activity, all types, all authors, current month
- "看看 vercel/next.js 最近一周有哪些 PR 和 issue" → repo-activity, types=pulls+issues, last 7 days
- "总结 @torvalds 在 torvalds/linux 上个月的活动" → repo-activity, all types, author=torvalds, last month
- "列出 anthropics/claude-code 这周的提交，按 @alice 筛选" → repo-activity, types=commits, author=alice, this week
