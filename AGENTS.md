# Release requirements

- Claude Desktop packages support Apple Silicon (M1 and newer) only. Do not add Intel builds.
- Every version release must publish both PyPI and a new Claude Desktop MCPB.
- Keep `pyproject.toml` and `packaging/manifest.json` versions equal; use a matching `vX.Y.Z` tag.
- Preserve the single Release workflow's ordering: tests and bundle → PyPI → real PyPI updater smoke test → GitHub MCPB/checksum.
- Never work around a failed release by publishing only the MCPB. Check the completed workflow and both destinations before declaring success.
- Preserve the desktop launcher's automatic PyPI update path, credential isolation, atomic activation, and offline fallback. Server updates must not require manual MCPB reinstallation.
- Explain that prepared updates activate on the next extension start; do not promise live replacement during a running conversation.
