# Release validation

Run the single tagged Release workflow; preserve this order:

1. Linux unit/regression tests, lint and type checks; validate package/manifest
   version equality and the MCPB manifest schema. Native Apple Silicon build and
   packaged MCP initialize/tool/status checks from a temporary directory outside
   the checkout. Verify sensitive fields and archive allowlist.
2. Publish wheel and source archive to PyPI.
3. Verify the exact stable release on real PyPI. Install it through the desktop
   updater with isolated synthetic saved credentials/settings. Check atomic
   activation, unchanged credentials/settings, and the packaged launcher's use of
   the prepared interpreter on its next offline start. Keep the previous
   environment intact. The test must not access a real Meta account.
4. Publish the versioned MCPB, identical repository-name alias and both checksums.
   Verify the completed workflow, PyPI version, download assets and hashes before
   claiming success. Do not bypass a failed updater check by uploading only MCPB.

A Linux test is not a macOS executable test. A native Apple Silicon subprocess test
is not a Claude UI installation test or a customer-account test. Record each
separately. No Intel builds are supported.

Compatibility: launcher 0.1.17 accepts stable numbered 0.1.x servers (>=0.1.15,
<0.2.0), excludes yanked wheels and probes the CLI/MCP tool inputs/status outputs.
Saved credential JSON and settings preservation are checked by the release smoke
script. Breaking changes to these contracts need a new compatibility boundary and
reviewed package, even if a version number would otherwise fall in range.
