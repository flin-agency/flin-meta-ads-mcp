# Security architecture and review record

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

From v0.1.15, MCPB bundles target Apple Silicon only. They contain a working frozen
fallback server and a version-pinned uv executable. Bundled runtime/build dependencies
are hash-pinned and assembly uses an explicit allowlist excluding local credentials,
Git history and development environments. Each package has a SHA-256 checksum.

The desktop launcher checks only `https://pypi.org/pypi/flin-meta-ads-mcp/json`,
without redirects, and installs stable numbered releases in the 0.1 series from the fixed official
PyPI index. A compatible Python runtime may be downloaded by uv from its official
managed runtime source. Ambient pip/uv configuration, proxy/index overrides and
Python injection variables are removed from the updater environment. No Meta
credentials are passed to the updater, installer or test connection.

Starting with launcher 0.1.17, both downloaded and cached servers must be >=0.1.15
and <0.2.0. Pre-releases and yanked wheels are excluded. The launch command, META_*
settings, credentials JSON and existing MCP tool schemas form the compatibility
contract; the probe checks the existing tool inputs and both status responses.
A changed contract needs a reviewed launcher/package import. Launchers 0.1.15–0.1.16
do not have this upper bound and need one replacement to acquire it.

Updates are intentionally not fixed to the bundle dependency lock: they follow the
published PyPI package and its compatible dependencies. This trusts future releases
of this project, PyPI dependencies and uv's managed Python distribution. Only binary
wheels are accepted, avoiding source-build scripts. A credential-free real MCP
handshake must succeed before a new environment is activated via an atomic pointer.
A process lock serializes concurrent updaters. Existing environments are never
modified or removed during updates. Running chats keep their version; the next
extension start picks up the prepared update. Failed/offline checks retain the
previous environment or bundled fallback. The background worker can finish after
Claude closes, with bounded network/subprocess timeouts.

Update environments are owner-private beneath
`~/Library/Application Support/flin-meta-ads-mcp/desktop/`. They are executable local
code, not an OS sandbox. A compromised user account or trusted package publisher is
outside this protection model. Removing the extension does not delete this cache.

Release automation requires successful tests and bundle creation before PyPI
publishing, then verifies the real PyPI update path before publishing the MCPB.
The original v0.1.14 extension requires a one-time replacement to gain auto-updates.

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
local listener lifecycle, credential permissions and image download limits. The historical v0.1.14 workflow supported Apple Silicon and Intel builds. For v0.1.14,
the Apple Silicon executable passed GitHub macOS 15 checks; the Intel executable
passed checks under Rosetta on macOS 26.6.2 with Intel Python 3.12.13. The GitHub
Intel runner remained queued, so native Intel hardware is not claimed as tested.
Dependency audit: 29 runtime and 11 build dependencies, no known vulnerabilities
reported by pip-audit on the review date. Gitleaks 8.30.1 found no secrets in the
24 existing commits or the scanned working files.
No live Meta account or ad data is used in these checks. This is an engineering
review, not an independent penetration test or a guarantee that no vulnerabilities exist.

Report suspected vulnerabilities privately to repository maintainers using GitHub's
private vulnerability reporting when available. Do not put credentials in public issues.
