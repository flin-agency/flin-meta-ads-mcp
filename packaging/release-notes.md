## flin Meta Ads

The extension now has the simpler display name **flin Meta Ads**, without platform or architecture suffixes.

New description: “Analysiere deine Meta-Werbekonten, Kampagnen und Anzeigen direkt in Claude. Nur Lesezugriff, mit automatischen Updates.”

The name and description belong to Claude's installed extension metadata. Install this MCPB once to see the updated wording. Existing v0.1.15 installations continue receiving automatic PyPI server updates without reinstallation; those updates do not replace Claude's extension metadata.

## Claude Desktop — Apple Silicon (M1 and newer)

Install the attached `.mcpb` via Claude Desktop → Settings → Extensions → Advanced settings → Install Extension.
No separate Python, uv or Homebrew installation is needed. Intel packages are no longer produced.

### Automatic server updates

The extension checks the official PyPI project in the background at each start. New stable releases are installed in a private environment and checked with a real MCP handshake. Successful updates become active at the next normal extension/Claude start; running conversations are not interrupted. Offline, the last prepared version or bundled fallback remains available.

**One-time migration:** replace the old v0.1.14 extension with this package. Afterwards, server updates do not require downloading/reinstalling MCPB files. The extension settings can still show the original bundle version while the MCP server reports its current PyPI version.

### Release process

Every `v*` tag runs tests and creates the M1 package, publishes to PyPI, tests an actual PyPI update through the packaged launcher, and then publishes the GitHub download and SHA-256 checksum. A failing step prevents subsequent steps from being marked successful.

App Secrets and tokens belong only in the sensitive extension settings, never in chat. The updater does not receive Meta credentials. The ad APIs remain read-only. Executables are not Apple Developer ID signed/notarized.

[Setup](https://github.com/flin-agency/flin-meta-ads-mcp#claude-desktop-on-macos--installable-package) · [Security and update details](https://github.com/flin-agency/flin-meta-ads-mcp/blob/main/SECURITY.md)
