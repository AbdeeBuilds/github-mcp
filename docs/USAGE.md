# Usage

After [installing](../README.md#install) and [authenticating](AUTH.md), the following tools are available to your LLM.

All tools return raw JSON from the GitHub API, pretty-printed. Errors come back as `Error: <message>` with status code, endpoint, and parsed GitHub error message.

## Common arguments

- `owner` (string) — repository owner (user or org). Never contains `/`.
- `repo` (string) — repository name. Never contains `/`.
- `number` (integer, ≥ 1) — issue or PR number.
- `state` (string) — `"open"`, `"closed"`, or `"all"`. Default: `"open"`.
- `limit` (integer, 1–100) — max items to return. Default: `10`.

---

## Issues

### `list_issues(owner, repo, state="open", limit=10, labels=None, since=None)`

List issues in a repo. Pull requests are filtered out.

| Param | Type | Default | Description |
|---|---|---|---|
| `owner` | string | required | Repository owner |
| `repo` | string | required | Repository name |
| `state` | enum | `"open"` | `open` / `closed` / `all` |
| `limit` | int 1–100 | `10` | Max issues to return |
| `labels` | string | `null` | Comma-separated label filter, e.g. `"bug,priority:high"` |
| `since` | string | `null` | ISO 8601 timestamp; only issues updated at or after |

**Returns:** JSON array of issues (without PRs).

**Examples:**

> "Show me the 5 most recent open issues in `cli/cli`."

> "List issues in `cli/cli` labeled `bug,p1` updated since 2026-01-01."

---

### `get_issue(owner, repo, number)`

Get a single issue by number.

| Param | Type | Default | Description |
|---|---|---|---|
| `owner` | string | required | Repository owner |
| `repo` | string | required | Repository name |
| `number` | int ≥ 1 | required | Issue number |

**Example:**

> "Get issue #100 in `cli/cli` and summarize it."

---

### `create_issue(owner, repo, title, body="", labels=None)`

Create a new issue. Requires write access on the target repo.

| Param | Type | Default | Description |
|---|---|---|---|
| `owner` | string | required | Repository owner |
| `repo` | string | required | Repository name |
| `title` | string | required | Issue title (non-empty, whitespace trimmed) |
| `body` | string | `""` | Issue body in markdown |
| `labels` | list of strings | `null` | Label names to apply at creation |

**Example:**

> "Create an issue in `my-org/my-repo` titled `Bug: login fails` with body `Steps to reproduce: 1. Open /login 2. Submit 3. ...` and labels `bug,priority:high`."

---

## Pull requests

### `list_pull_requests(owner, repo, state="open", limit=10)`

| Param | Type | Default | Description |
|---|---|---|---|
| `owner` | string | required | Repository owner |
| `repo` | string | required | Repository name |
| `state` | enum | `"open"` | `open` / `closed` / `all` |
| `limit` | int 1–100 | `10` | Max PRs to return |

**Example:**

> "List the 3 most recent closed PRs in `cli/cli`."

---

### `get_pull_request(owner, repo, number)`

Get a single pull request by number.

| Param | Type | Default | Description |
|---|---|---|---|
| `owner` | string | required | Repository owner |
| `repo` | string | required | Repository name |
| `number` | int ≥ 1 | required | PR number |

**Example:**

> "Show me PR #42 in `cli/cli` and tell me if it has merge conflicts."

---

## Code

### `search_code(query, limit=10)`

Search code across GitHub. Requires a fine-grained token with `Code: Read` scope, or a classic token with `repo` scope.

| Param | Type | Default | Description |
|---|---|---|---|
| `query` | string | required | GitHub code-search query (non-empty) |
| `limit` | int 1–100 | `10` | Max results |

**Query syntax:** use [GitHub's code search syntax](https://docs.github.com/en/search-github/searching-on-github/searching-code). Examples:

- `repo:owner/name function_name` — search within a repo
- `language:python async` — language + term
- `path:src/ TODO` — restrict to path
- `user:myorg` — within an org

**Returns:** the raw GitHub search response (`total_count`, `incomplete_results`, `items`).

**Examples:**

> "Search for `function authenticate` in `cli/cli`."

> "Find all `TODO` comments in `myorg/myrepo` source files."

---

### `get_file_content(owner, repo, path, ref=None)`

Read the contents of a file at a given ref (branch, tag, commit SHA; defaults to default branch).

| Param | Type | Default | Description |
|---|---|---|---|
| `owner` | string | required | Repository owner |
| `repo` | string | required | Repository name |
| `path` | string | required | File path within repo, e.g. `src/main.py` |
| `ref` | string | `null` | Branch / tag / commit SHA |

**Returns:** GitHub's contents API response. **Text files are returned UTF-8-decoded** under `decoded_content` (and `encoding` is set to `"utf-8"`). Binary files keep the base64 payload under `content`.

**Examples:**

> "Show me the contents of `src/main.py` in `cli/cli` on the `main` branch."

> "Get `README.md` from `cli/cli` at tag `v2.0.0`."

---

## Tips

- Use the `limit` parameter to control response size (default 10, max 100).
- The server returns raw GitHub API responses (JSON) — your LLM will parse them.
- If you hit rate limits (5000 req/hr for authenticated users), the server retries automatically with exponential backoff and honors `Retry-After`.
- For large responses, ask the LLM to summarize rather than read the full output.
- Token scopes — fine-grained token with `Public Repositories (read-only)` covers 6 of 7 tools; add `Issues: Read and Write` for `create_issue`, and `Code: Read` for `search_code`.

## Error responses

Every tool returns a `TextContent` payload. On error, the text starts with `Error: ` and includes:

- HTTP status code (or `0` for network failures)
- GitHub's parsed error message (e.g. `"Not Found"`)
- The endpoint that was called

Example:

```
Error: GitHub API error 404: Not Found [endpoint: /repos/cli/cli/issues/9999]
```

Validation errors (e.g. missing `owner`, bad `state`) come back the same way with a `ValueError` message and no traceback.
