# Security

## Reporting a vulnerability

**Do not file a public GitHub issue for security bugs.**

Email `security@hermes-agent.dev` (or open a private advisory via
[GitHub Security Advisories](https://github.com/AbdeeBuilds/github-mcp/security/advisories/new))
with:
- Description of the vulnerability and impact
- Reproduction steps
- Affected versions

We aim to acknowledge within 48 hours and patch within 7 days for critical issues.

## Token handling

- Tokens are read from the `GITHUB_TOKEN` environment variable or passed explicitly.
- Tokens are never logged. HTTP headers containing the token are constructed once
  in `GitHubClient._get_client()` and used for the life of the process.
- Error messages strip response bodies to 500 characters to avoid log flooding.
- The server runs over stdio — there is no network listener that an attacker
  could reach without spawning the process with the same MCP client.

## Dependencies

- `httpx` for HTTP — keep up to date.
- `mcp` for the protocol — keep up to date.
- `pydantic` for validation — keep up to date.

We use `pip-audit` (or equivalent) in CI to surface known vulnerabilities.

## Threat model

**In scope:**
- Reading repos you have access to via the GitHub API.
- Writing issues to repos you have write access to.
- Surfacing error messages that may include limited repository content.

**Out of scope:**
- Attacking the user's GitHub account beyond what the token's scope allows.
- Lateral movement to other services — this server only talks to `api.github.com`.

## Scope of a leaked token

If you suspect your `GITHUB_TOKEN` was leaked:
1. **Revoke it immediately** at https://github.com/settings/tokens
2. Generate a new fine-grained token with the minimum scopes needed
3. Check your audit log at https://github.com/settings/security-log
