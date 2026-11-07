## flin Meta Ads — common connection and installation standard

- Desktop-first setup, privacy/security/support documents and clear running-server diagnostics.
- New `connection_status`: local by default, explicit `check_live=true` for one read-only Meta access check; no secrets or account data returned. Existing tools remain available.
- Automatic PyPI updates stay within stable 0.1.x versions. Pre-releases and yanked wheels are excluded; candidate MCP contracts are checked before activation.
- Both the original versioned Apple Silicon package and identical `flin-meta-ads-mcp.mcpb` alias have SHA-256 checksums. The extension identity is unchanged.

**Import this package once to replace 0.1.16 or older:** the compatibility bound
and runtime-source reporting are part of the launcher. Existing auto-updating
installations can acquire the server tool without a new package, but not these
launcher changes. Routine compatible server updates afterwards need no reimport.
Prepared updates activate on the next extension start; current conversations keep
their running version. Settings and saved logins are retained. Offline, the prepared
server or bundled fallback starts.

Apple Silicon (M1 or newer) only. No separate Python, uv or Homebrew is needed.
App Secrets/tokens belong in sensitive extension settings. Browser-login files are
local and unencrypted with owner-only permissions. No live customer-account test
is implied by the automated release checks. Executables are not Developer ID
signed/notarized.

[Setup](https://github.com/flin-agency/flin-meta-ads-mcp#claude-desktop-on-macos--installable-package) · [Support](https://github.com/flin-agency/flin-meta-ads-mcp/blob/main/SUPPORT.md)
