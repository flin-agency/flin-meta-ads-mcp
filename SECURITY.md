# Security and privacy

## Scope

This is a local stdio MCP server. Meta Ads tools only issue GET requests to a fixed
allowlist of Graph endpoints. OAuth token exchange uses POST to Meta's token endpoint.
There are no ad creation, modification, deletion or spending tools. A default ad
account is a convenience setting, not an authorization boundary: the token defines
which accounts the user can access. Prefer Meta's `ads_read` permission.

## Credentials

Never paste access tokens or App Secrets into chat, issues or screenshots.
The Claude Desktop extension marks both fields as sensitive, allowing Claude to
store them using its secure configuration mechanism. Environment variables are
passed to the local process, not on its command line.

Browser login saves the token and App Secret in
`~/.config/flin-meta-ads-mcp/credentials.json` (or `META_AUTH_FILE`). This file is
**not encrypted**. It is atomically created with owner-only permissions (0600);
a newly created directory is 0700. Protect your macOS account and disk. Removing
the extension does not remove this shared login file. Delete it to remove the
saved login, and revoke access in Meta if a token was exposed. For no server-side
credential file, enter an access token in the extension settings instead.

## Network and data

- Graph authentication uses the Authorization header. An App Secret enables HMAC
  appsecret_proof. API redirects are disabled, errors omit upstream text/bodies,
  and unexpected exception tracebacks are not logged.
- Login binds only to 127.0.0.1, checks a random state value, times out, and does
  not log callback URLs. Meta's app configuration must allow the exact redirect.
- Image downloads use a separate unauthenticated client, HTTPS Meta CDN subdomains,
  per-hop URL validation, a 5 MiB streaming limit and basic format checks. Encoded
  transfers are rejected to prevent decompression bypassing the size limit.
- Embedded ad previews are restricted to the HTTPS Facebook preview endpoint,
  use iframe sandboxing, a restrictive content security policy and no referrer.
- Ad content and previews are untrusted external data, not instructions. Data
  returned to Claude is subject to the user's Claude account/workspace policies.
- Normal system proxy and certificate settings remain applicable. This does not
  defend against a compromised user account, OS, trusted proxy or Meta service.

## macOS packages

Release MCPB bundles include a Python runtime and dependencies: no installer script,
root access or runtime package download is required. Runtime and packaging dependencies
are version-pinned with SHA-256 hashes. Bundle assembly uses an explicit staging
allowlist, excluding local credentials, Git history and development environments.
Each bundle has a SHA-256 file and is tested via a real stdio MCP connection.

Executables have PyInstaller's ad-hoc signature; they are **not Apple Developer ID
signed or notarized**. Enterprise extension policy or macOS security settings may
block installation. No security setting should be disabled to install this package.

## Review record — 2026-11-06

The v0.1.14 review covered all application modules, OAuth and credential storage,
input validation, HTTP destinations/methods, image handling, HTML previews, dependencies,
repository secrets and CI/release packaging. Fixes address upstream error disclosure,
exception logging, unsafe preview embedding, missing transport-level read-only guards,
unbounded configuration values and compressed-image resource exhaustion.

Regression tests include malicious paths/method overrides, redirects, error leaks,
preview URLs and invalid timeout/retry values. Existing tests cover OAuth state,
local listener lifecycle, credential permissions and image download limits. Release
jobs test the frozen executable independently on Apple Silicon and Intel runners.
Dependency audit: 29 runtime and 11 build dependencies, no known vulnerabilities
reported by pip-audit on the review date. Gitleaks 8.30.1 found no secrets in the
24 existing commits or the scanned working files.
No live Meta account or ad data is used in these checks. This is an engineering
review, not an independent penetration test or a guarantee that no vulnerabilities exist.

Report suspected vulnerabilities privately to repository maintainers using GitHub's
private vulnerability reporting when available. Do not put credentials in public issues.
