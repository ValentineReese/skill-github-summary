#!/usr/bin/env python3
"""Fetch GitHub activity (commits, PRs, issues) via the GitHub REST API."""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta


API_BASE = "https://api.github.com"


def get_token():
    """Return the token or None (unauthenticated access for public repos)."""
    return os.environ.get("GITHUB_PAT", "").strip() or None


def api_request(url, token):
    req = urllib.request.Request(url)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            link_header = resp.headers.get("Link", "")
            next_url = None
            if link_header:
                for part in link_header.split(","):
                    if 'rel="next"' in part:
                        next_url = part.split(";")[0].strip().strip("<>")
            return data, next_url
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"HTTP {e.code}: {body}", file=sys.stderr)
        sys.exit(1)


def get_username(token):
    data, _ = api_request(f"{API_BASE}/user", token)
    return data["login"]


def paginate_all(url, token, max_pages=20):
    """Fetch all pages from a paginated GitHub API endpoint."""
    results = []
    current_url = url
    page_count = 0
    while current_url and page_count < max_pages:
        data, next_url = api_request(current_url, token)
        if isinstance(data, list):
            results.extend(data)
        elif isinstance(data, dict) and "items" in data:
            results.extend(data["items"])
            if not data["items"]:
                break
        else:
            break
        current_url = next_url
        page_count += 1
    return results


# ---------------------------------------------------------------------------
# Mode 1: User commits (original functionality)
# ---------------------------------------------------------------------------

def search_user_commits(token, username, since, until, repos):
    """Search commits authored by the user across repos.

    When specific repos are provided, uses the Repo Commits API (/repos/{repo}/commits)
    which works for both public and private repos the token has access to.
    When no repos are specified, uses the Search API to discover commits across all repos.
    """
    all_commits = []

    if repos:
        # Use Repo Commits API for each specified repo (works with private repos)
        for repo in repos:
            commits = fetch_repo_commits(token, repo, since, until, author=username)
            for c in commits:
                c["repo"] = repo
            all_commits.extend(commits)
    else:
        # Use Search API to discover commits across all repos
        query_parts = [f"author:{username}", f"author-date:{since}..{until}"]
        query = "+".join(query_parts)
        url = f"{API_BASE}/search/commits?q={query}&sort=author-date&order=asc&per_page=100"
        items = paginate_all(url, token)

        for item in items:
            commit_data = item.get("commit", {})
            author_date = commit_data.get("author", {}).get("date", "")
            repo_name = item.get("repository", {}).get("full_name", "")
            sha = item.get("sha", "")
            message = commit_data.get("message", "")
            html_url = item.get("html_url", "")

            all_commits.append({
                "repo": repo_name,
                "sha": sha[:7],
                "date": author_date,
                "message": message,
                "url": html_url,
            })

    return all_commits


# ---------------------------------------------------------------------------
# Mode 2: Repo activity (commits + PRs + issues for a specific repo)
# ---------------------------------------------------------------------------

def fetch_repo_commits(token, repo, since, until, author=None):
    """Fetch commits for a repo, optionally filtered by author."""
    params = {
        "since": f"{since}T00:00:00Z",
        "until": f"{until}T23:59:59Z",
        "per_page": "100",
    }
    if author:
        params["author"] = author
    url = f"{API_BASE}/repos/{repo}/commits?{urllib.parse.urlencode(params)}"
    items = paginate_all(url, token)

    commits = []
    for item in items:
        commit_data = item.get("commit", {})
        author_info = commit_data.get("author", {})
        commits.append({
            "sha": item.get("sha", "")[:7],
            "date": author_info.get("date", ""),
            "author": item.get("author", {}).get("login", author_info.get("name", "unknown")),
            "message": commit_data.get("message", ""),
            "url": item.get("html_url", ""),
        })
    return commits


def fetch_repo_pulls(token, repo, since, until, author=None):
    """Fetch PRs for a repo within the date range, optionally filtered by author."""
    # Fetch both open and closed PRs
    all_prs = []
    for state in ("open", "closed"):
        params = {
            "state": state,
            "sort": "updated",
            "direction": "desc",
            "per_page": "100",
        }
        url = f"{API_BASE}/repos/{repo}/pulls?{urllib.parse.urlencode(params)}"
        items = paginate_all(url, token)

        for item in items:
            created = item.get("created_at", "")[:10]
            updated = item.get("updated_at", "")[:10]
            # Include PR if its created or updated date falls in range
            if updated < since:
                # PRs are sorted by updated desc, so we can break early
                break
            if created > until and updated > until:
                continue
            if author and item.get("user", {}).get("login", "") != author:
                continue

            merged_at = item.get("merged_at")
            if item.get("state") == "closed" and merged_at:
                pr_state = "merged"
            else:
                pr_state = item.get("state")

            all_prs.append({
                "number": item.get("number"),
                "title": item.get("title", ""),
                "state": pr_state,
                "author": item.get("user", {}).get("login", ""),
                "created_at": item.get("created_at", ""),
                "updated_at": item.get("updated_at", ""),
                "merged_at": merged_at,
                "url": item.get("html_url", ""),
                "labels": [l.get("name") for l in item.get("labels", [])],
            })

    return all_prs


def fetch_repo_issues(token, repo, since, until, author=None):
    """Fetch issues (not PRs) for a repo within the date range, optionally filtered by author."""
    all_issues = []
    for state in ("open", "closed"):
        params = {
            "state": state,
            "sort": "updated",
            "direction": "desc",
            "per_page": "100",
            "since": f"{since}T00:00:00Z",
        }
        if author:
            params["creator"] = author
        url = f"{API_BASE}/repos/{repo}/issues?{urllib.parse.urlencode(params)}"
        items = paginate_all(url, token)

        for item in items:
            # Skip pull requests (GitHub API returns PRs as issues too)
            if "pull_request" in item:
                continue
            created = item.get("created_at", "")[:10]
            if created > until:
                continue

            all_issues.append({
                "number": item.get("number"),
                "title": item.get("title", ""),
                "state": item.get("state"),
                "author": item.get("user", {}).get("login", ""),
                "created_at": item.get("created_at", ""),
                "updated_at": item.get("updated_at", ""),
                "closed_at": item.get("closed_at"),
                "url": item.get("html_url", ""),
                "labels": [l.get("name") for l in item.get("labels", [])],
                "comments": item.get("comments", 0),
            })

    return all_issues


def cmd_user_commits(args, token):
    """Handle user-commits mode. Requires token to identify the user."""
    if not token:
        print("Error: user-commits mode requires GITHUB_PAT to identify the authenticated user.", file=sys.stderr)
        sys.exit(1)

    today = datetime.now().date()
    since = args.since or (today - timedelta(days=7)).isoformat()
    until = args.until or today.isoformat()
    repos = args.repos or []

    username = get_username(token)
    commits = search_user_commits(token, username, since, until, repos)

    result = {
        "mode": "user-commits",
        "username": username,
        "since": since,
        "until": until,
        "repos_filter": repos if repos else "all",
        "total_commits": len(commits),
        "commits": commits,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_repo_activity(args, token):
    """Handle repo-activity mode."""
    today = datetime.now().date()
    since = args.since or (today - timedelta(days=7)).isoformat()
    until = args.until or today.isoformat()
    repo = args.repo
    author = args.author

    activity_types = args.types or ["commits", "pulls", "issues"]

    result = {
        "mode": "repo-activity",
        "repo": repo,
        "since": since,
        "until": until,
        "author_filter": author or "all",
        "activity_types": activity_types,
    }

    if "commits" in activity_types:
        commits = fetch_repo_commits(token, repo, since, until, author)
        result["total_commits"] = len(commits)
        result["commits"] = commits

    if "pulls" in activity_types:
        pulls = fetch_repo_pulls(token, repo, since, until, author)
        result["total_pulls"] = len(pulls)
        result["pulls"] = pulls

    if "issues" in activity_types:
        issues = fetch_repo_issues(token, repo, since, until, author)
        result["total_issues"] = len(issues)
        result["issues"] = issues

    print(json.dumps(result, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Fetch GitHub activity.")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Subcommand: user-commits
    p_user = subparsers.add_parser("user-commits", help="Fetch commits by the authenticated user.")
    p_user.add_argument("--since", help="Start date (YYYY-MM-DD). Default: 7 days ago.")
    p_user.add_argument("--until", help="End date (YYYY-MM-DD). Default: today.")
    p_user.add_argument("--repos", nargs="*", help="Repository filter (owner/repo). Default: all repos.")

    # Subcommand: repo-activity
    p_repo = subparsers.add_parser("repo-activity", help="Fetch activity for a specific public repo.")
    p_repo.add_argument("repo", help="Repository (owner/repo).")
    p_repo.add_argument("--since", help="Start date (YYYY-MM-DD). Default: 7 days ago.")
    p_repo.add_argument("--until", help="End date (YYYY-MM-DD). Default: today.")
    p_repo.add_argument("--author", help="Filter by GitHub username. Default: all contributors.")
    p_repo.add_argument("--types", nargs="*", choices=["commits", "pulls", "issues"],
                        help="Activity types to fetch. Default: all three.")

    args = parser.parse_args()

    token = get_token()

    if args.command == "user-commits":
        cmd_user_commits(args, token)
    elif args.command == "repo-activity":
        cmd_repo_activity(args, token)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
