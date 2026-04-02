#!/usr/bin/env bash
set -euo pipefail

# ─── fetch_activity.sh ──────────────────────────────────────────────────
# Fetch GitHub activity via gh CLI.  Outputs JSON to stdout.
# Requires: gh (authenticated), jq

for cmd in gh jq; do
    command -v "$cmd" >/dev/null 2>&1 || {
        echo "Error: '$cmd' is required but not found." >&2
        exit 1
    }
done

# ── Helpers ──────────────────────────────────────────────────────────────

default_since() {
    date -v-7d +%Y-%m-%d 2>/dev/null || date -d '7 days ago' +%Y-%m-%d
}

default_until() {
    date +%Y-%m-%d
}

usage() {
    cat <<'EOF'
Usage:
  fetch_activity.sh user-commits [--since DATE] [--until DATE] [--repos REPO ...]
  fetch_activity.sh repo-activity REPO [--since DATE] [--until DATE] [--author USER] [--types TYPE ...]

Dates: YYYY-MM-DD (default: last 7 days)
Types: commits, pulls, issues (default: all)
EOF
    exit 1
}

# ─── Mode 1: user-commits ───────────────────────────────────────────────

cmd_user_commits() {
    local since="" until_date=""
    local -a repos=()

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --since) since="$2"; shift 2 ;;
            --until) until_date="$2"; shift 2 ;;
            --repos)
                shift
                while [[ $# -gt 0 && "$1" != --* ]]; do repos+=("$1"); shift; done
                ;;
            *) echo "Unknown option: $1" >&2; usage ;;
        esac
    done

    : "${since:=$(default_since)}"
    : "${until_date:=$(default_until)}"

    local username
    username=$(gh api /user --jq '.login')

    local commits
    if [[ ${#repos[@]} -gt 0 ]]; then
        commits="[]"
        for repo in "${repos[@]}"; do
            local rc
            rc=$(gh api "repos/${repo}/commits?since=${since}T00:00:00Z&until=${until_date}T23:59:59Z&per_page=100&author=${username}" \
                --paginate \
                --jq '.[] | {sha: .sha[0:7], date: .commit.author.date, author: (.author.login // .commit.author.name), message: .commit.message, url: .html_url}' \
                | jq -s --arg repo "$repo" '[.[] + {repo: $repo}]')
            commits=$(echo "$commits"$'\n'"$rc" | jq -s 'add')
        done
    else
        commits=$(gh search commits \
            --author="$username" \
            --author-date="${since}..${until_date}" \
            --limit 200 \
            --json repository,sha,commit,url \
            | jq '[.[] | {
                repo: (.repository.nameWithOwner // .repository.fullName),
                sha: .sha[0:7],
                date: .commit.author.date,
                message: .commit.message,
                url: .url
            }]')
    fi

    local repos_json
    if [[ ${#repos[@]} -gt 0 ]]; then
        repos_json=$(printf '%s\n' "${repos[@]}" | jq -R . | jq -s .)
    else
        repos_json='"all"'
    fi

    jq -n \
        --arg mode "user-commits" \
        --arg username "$username" \
        --arg since "$since" \
        --arg until "$until_date" \
        --argjson repos_filter "$repos_json" \
        --argjson commits "$commits" \
        '{
            mode: $mode,
            username: $username,
            since: $since,
            until: $until,
            repos_filter: $repos_filter,
            total_commits: ($commits | length),
            commits: $commits
        }'
}

# ─── Mode 2: repo-activity ──────────────────────────────────────────────

cmd_repo_activity() {
    [[ $# -lt 1 ]] && { echo "Error: repo argument required." >&2; usage; }
    local repo="$1"; shift
    local since="" until_date="" author=""
    local -a types=()

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --since) since="$2"; shift 2 ;;
            --until) until_date="$2"; shift 2 ;;
            --author) author="$2"; shift 2 ;;
            --types)
                shift
                while [[ $# -gt 0 && "$1" != --* ]]; do types+=("$1"); shift; done
                ;;
            *) echo "Unknown option: $1" >&2; usage ;;
        esac
    done

    : "${since:=$(default_since)}"
    : "${until_date:=$(default_until)}"
    [[ ${#types[@]} -eq 0 ]] && types=(commits pulls issues)

    local types_json
    types_json=$(printf '%s\n' "${types[@]}" | jq -R . | jq -s .)

    local result
    result=$(jq -n \
        --arg mode "repo-activity" \
        --arg repo "$repo" \
        --arg since "$since" \
        --arg until "$until_date" \
        --arg author "${author:-all}" \
        --argjson types "$types_json" \
        '{mode: $mode, repo: $repo, since: $since, until: $until, author_filter: $author, activity_types: $types}')

    # ── Commits ──
    if printf '%s\n' "${types[@]}" | grep -qx commits; then
        local api_url="repos/${repo}/commits?since=${since}T00:00:00Z&until=${until_date}T23:59:59Z&per_page=100"
        [[ -n "$author" ]] && api_url+="&author=${author}"

        local commits
        commits=$(gh api "$api_url" --paginate \
            --jq '.[] | {sha: .sha[0:7], date: .commit.author.date, author: (.author.login // .commit.author.name), message: .commit.message, url: .html_url}' \
            | jq -s .)

        result=$(echo "$result" | jq --argjson c "$commits" '. + {total_commits: ($c | length), commits: $c}')
    fi

    # ── Pull Requests ──
    if printf '%s\n' "${types[@]}" | grep -qx pulls; then
        local search="updated:>=${since}"
        [[ -n "$author" ]] && search+=" author:${author}"

        local pulls
        pulls=$(gh pr list -R "$repo" --state all \
            --search "$search" \
            --json number,title,state,author,createdAt,updatedAt,mergedAt,url,labels \
            --limit 200 \
            | jq --arg until "${until_date}T23:59:59Z" '
                [.[] | select(.createdAt <= $until) | {
                    number,
                    title,
                    state: (if .mergedAt then "merged" else .state end),
                    author: .author.login,
                    created_at: .createdAt,
                    updated_at: .updatedAt,
                    merged_at: .mergedAt,
                    url,
                    labels: [.labels[].name]
                }]')

        result=$(echo "$result" | jq --argjson p "$pulls" '. + {total_pulls: ($p | length), pulls: $p}')
    fi

    # ── Issues ──
    if printf '%s\n' "${types[@]}" | grep -qx issues; then
        local search="updated:>=${since}"
        [[ -n "$author" ]] && search+=" author:${author}"

        local issues
        issues=$(gh issue list -R "$repo" --state all \
            --search "$search" \
            --json number,title,state,author,createdAt,updatedAt,closedAt,url,labels,comments \
            --limit 200 \
            | jq --arg until "${until_date}T23:59:59Z" '
                [.[] | select(.createdAt <= $until) | {
                    number,
                    title,
                    state,
                    author: .author.login,
                    created_at: .createdAt,
                    updated_at: .updatedAt,
                    closed_at: .closedAt,
                    url,
                    labels: [.labels[].name],
                    comments: (.comments | length)
                }]')

        result=$(echo "$result" | jq --argjson i "$issues" '. + {total_issues: ($i | length), issues: $i}')
    fi

    echo "$result"
}

# ─── Main ────────────────────────────────────────────────────────────────

[[ $# -lt 1 ]] && usage

case "$1" in
    user-commits)  shift; cmd_user_commits "$@" ;;
    repo-activity) shift; cmd_repo_activity "$@" ;;
    -h|--help)     usage ;;
    *)             echo "Unknown command: $1" >&2; usage ;;
esac
