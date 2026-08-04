# MCP v2 Compatibility Design

## Problem

`flin-meta-ads-mcp` uses the MCP Python SDK 1.x low-level server decorators, including
`Server.list_tools()` and `Server.call_tool()`. The package currently declares `mcp>=1.0.0`,
so fresh `uvx` installations resolve MCP 2.x. MCP 2.x removed those decorators, causing the
server to exit during initialization with `AttributeError: 'Server' object has no attribute
'list_tools'`.

## Decision

Constrain the runtime dependency to `mcp>=1.28,<2` and publish patch release `0.1.10`.
This keeps the existing server implementation on the latest maintained MCP 1.x line and
restores fresh `uvx` installations without introducing a broader SDK migration into an
emergency compatibility release.

## Alternatives considered

- Add only `mcp<2`: smallest metadata change, but it preserves an unnecessarily broad and
  unverified lower bound.
- Migrate immediately to MCP 2.x: removes the cap, but requires rewriting handler registration
  and result construction and carries more release risk.

## Verification

- Add a packaging regression test that requires the exact supported MCP range.
- Run the complete unit test, lint, and type-check suites.
- Build the distributions and inspect their dependency metadata.
- Launch the built package with `uvx` and complete an MCP initialization handshake.

## Release

Bump the project version and README release example to `0.1.10`. Push the verified commit to
`main`, create tag `v0.1.10`, push it, and monitor the tag-triggered Release workflow through
publication.
