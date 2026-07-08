# Authentication

## 1. Create a GitHub Personal Access Token

**Recommended: Fine-grained token**

1. Go to https://github.com/settings/personal-access-tokens/new
2. Token name: anything memorable (e.g., `github-mcp`)
3. Expiration: your choice (30 / 90 / 365 days, or custom)
4. **Repository access:**
   - "Public Repositories (read-only)" — enough for `list_issues`, `get_issue`, `list_pull_requests`, `get_pull_request`, `search_code`, `get_file_content` on public repos
   - For `create_issue` on private repos, select specific repos and grant **Issues: Read and Write**
5. Click **Generate token**
6. **Copy the token now** — you will not see it again

**Alternative: Classic token (legacy)**

1. Go to https://github.com/settings/tokens/new
2. Select scopes: `repo` (full read), or `public_repo` (public only)
3. Generate and copy

## 2. Set the Token

### macOS / Linux

```bash
export GITHUB_TOKEN="ghp_..."
```

To persist across shells, add to your `~/.zshrc` or `~/.bashrc`:

```bash
echo 'export GITHUB_TOKEN="ghp_..."' >> ~/.zshrc
```

### Windows (PowerShell)

```powershell
$env:GITHUB_TOKEN="ghp_..."
```

To persist: **System Properties → Environment Variables → New (User variable)** with name `GITHUB_TOKEN` and your token as the value.

### Windows (Git Bash)

```bash
export GITHUB_TOKEN="ghp_..."
```

Add to `~/.bashrc` to persist.

## 3. Set in Your MCP Client Config (alternative)

You can pass the token directly in your client's MCP config instead of an env var. This is convenient but the token will be stored in plain text on disk.

### Cursor (`~/.cursor/mcp.json`)

```json
{
  "mcpServers": {
    "github": {
      "command": "github-mcp",
      "env": {
        "GITHUB_TOKEN": "ghp_..."
      }
    }
  }
}
```

### Claude Code

```bash
claude mcp add --transport stdio github -- github-mcp
# Then set GITHUB_TOKEN in your shell environment as above
```

## 4. Verify

After configuring, your LLM should be able to call:

```
list_issues(owner="cli", repo="cli", limit=5)
```

If you get `Error: GITHUB_TOKEN not set`, the env var is not visible to the `github-mcp` process — check how your client launches MCP servers (it may not inherit your shell env).

If you get `GitHub API error 401`, the token is invalid or revoked.

If you get `GitHub API error 403` on `search_code`, your token does not have code search scope.
