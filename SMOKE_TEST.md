# Smoke Test Checklist — github-mcp v0.1.0

**Date:** 2026-07-04
**Purpose:** Verify Day 1 of Sprint 3 (MVP) before advancing to Day 2.
**Rule:** If any step fails, **stop and report**. Do not advance.

---

## Prerequisites

- Windows with Git Bash or PowerShell
- Python 3.10+
- A GitHub account
- A GitHub personal access token (instructions in Step 3)
- One of: Claude Code, Cursor, or Cline (any MCP-compatible client)

---

## Step 0: Pick your test location

You have a working copy at `C:\Users\acer\projects\github-mcp\`.

**Option A — use the existing dir directly** (fastest):
```bash
cd /c/Users/acer/projects/github-mcp
```

**Option B — copy to a fresh dir** (simulates a true fresh clone):
```bash
cp -r /c/Users/acer/projects/github-mcp /c/Users/acer/projects/github-mcp-smoketest
cd /c/Users/acer/projects/github-mcp-smoketest
rm -rf .venv .venv-smoketest .pytest_cache src/*.egg-info build dist
```

---

## Step 1: Fresh virtual environment

Git Bash:
```bash
python -m venv .venv
source .venv/Scripts/activate
```

PowerShell:
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**PASS:** Shell prompt shows `(.venv)`
**FAIL:** "python not found" → install Python 3.10+ from python.org and retry

---

## Step 2: Install package + dev dependencies

```bash
pip install -e ".[dev]"
```

**PASS:** Last line includes `Successfully installed github-mcp-0.1.0`
**FAIL:** Build error → stop, send me the full traceback

---

## Step 3: Create + set GITHUB_TOKEN

**3a. Create the token** (skip if you already have one):
1. Go to https://github.com/settings/personal-access-tokens/new
2. Token name: `github-mcp-smoketest`
3. Expiration: 7 days (easy to clean up)
4. Repository access: **"Public Repositories (read-only)"** — enough for 6 of 7 tools
5. For `create_issue`: select specific repos + grant **"Issues: Read and Write"**
6. Click **Generate token**, copy the value (you won't see it again)

**3b. Export the env var:**

Git Bash:
```bash
export GITHUB_TOKEN="ghp_..."
```

PowerShell:
```powershell
$env:GITHUB_TOKEN = "ghp_..."
```

**3c. Verify it's visible to Python:**

```bash
python -c "import os; t = os.environ.get('GITHUB_TOKEN', ''); print('OK' if t.startswith(('ghp_', 'github_pat_')) else f'MISSING or malformed: {t[:8]}')"
```

**PASS:** Prints `OK`
**FAIL:** Prints `MISSING or malformed: ...` → env var not exported in this shell. Re-export and retry.

---

## Step 4: Verify token hits GitHub API

```bash
python -c "
import asyncio
from github_mcp.client import GitHubClient
c = GitHubClient()
issues = asyncio.run(c.list_issues('cli', 'cli', limit=3))
print(f'Got {len(issues)} issues')
for i in issues:
    print(f'  #{i[\"number\"]}: {i[\"title\"][:60]}')
"
```

**PASS:** Prints `Got 3 issues` with 3 numbered titles
**FAIL 401:** Token invalid or expired → regenerate
**FAIL 403:** Token scope insufficient → check fine-grained access settings
**FAIL other:** Send me the full error + which token type you used

---

## Step 5: MCP server starts

```bash
github-mcp
```

Let it run for 3-5 seconds, then `Ctrl+C`.

**PASS:** Process stays running, logs to stderr, no traceback
**FAIL:** ImportError, ModuleNotFoundError, or any traceback → stop, send me the full error

---

## Step 6: Connect via your LLM client

### Claude Code

```bash
claude mcp add --transport stdio github -- github-mcp
claude mcp list
```

**PASS:** `github` appears in the list, shows 7 tools

### Cursor

Edit `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "github": {
      "command": "github-mcp",
      "env": { "GITHUB_TOKEN": "ghp_..." }
    }
  }
}
```

Restart Cursor. Open Settings → MCP. **PASS:** `github` appears with 7 tools listed

### Cline

Cline panel → MCP Servers → Configure MCP Servers → add:

```json
{
  "mcpServers": {
    "github": {
      "command": "github-mcp",
      "env": { "GITHUB_TOKEN": "ghp_..." },
      "transportType": "stdio"
    }
  }
}
```

**PASS:** `github` appears, status `connected`, 7 tools listed

**FAIL for any client:**
- Server not appearing → run `which github-mcp` (Git Bash) or `Get-Command github-mcp` (PowerShell). It must resolve to a path inside your active venv.
- Env var not visible to client → pass `GITHUB_TOKEN` in the MCP config's `env` block, not just the shell
- Client not seeing tools → fully quit + reopen the client (not just close the panel)

---

## Step 7: Run all 7 tools against a real repo

In your LLM client, send these prompts in order. Verify each response.

| # | Tool | Prompt | Expected |
|---|---|---|---|
| 1 | `list_issues` | "List 3 open issues in cli/cli" | JSON of 3 issues with numbers + titles |
| 2 | `get_issue` | "Get issue #1 in cli/cli" | JSON of that issue |
| 3 | `create_issue` | "Create a test issue in YOUR-USERNAME/YOUR-TEST-REPO titled 'smoke-test: please ignore'" | URL of new issue. **SKIP** if token is read-only. |
| 4 | `list_pull_requests` | "List 3 closed PRs in cli/cli" | JSON of 3 PRs |
| 5 | `get_pull_request` | "Get PR #1 in cli/cli" | JSON of that PR |
| 6 | `search_code` | "Search for 'def main' in cli/cli" | Results. **Acceptable to fail with 403** if token lacks code-search scope — just note it. |
| 7 | `get_file_content` | "Get the contents of README.md in cli/cli" | Base64 content + metadata |

**PASS criteria:** 6 of 7 tools return valid data, OR 7 of 7 if your token has all scopes
**FAIL criteria:** Any tool returns an error other than the noted `search_code` 403

---

## When all 7 pass

Reply exactly: **`SMOKE TEST PASSED`**
→ I continue to Day 2 (git init, package build verification, polish).

## If anything fails

**Do NOT continue to Day 2.** Send me:
- Which step (1-7) and which sub-step (e.g., "Step 6, Claude Code")
- The exact command(s) or prompt(s) you ran
- The full error output (copy from terminal or client logs)
- Your environment: Windows version, shell (Git Bash / PowerShell), client (Claude Code / Cursor / Cline), and Python version (`python --version`)

I will not write any new code until the failure is diagnosed.

---

## After the smoke test passes — clean up

- Delete the test issue you created (Step 7, tool #3) if you ran it
- Revoke the test token at https://github.com/settings/personal-access-tokens
- Deactivate the venv: `deactivate`
- Delete the smoketest copy (Option B) if you used it
- Keep the real project at `C:\Users\acer\projects\github-mcp\` for Day 2
