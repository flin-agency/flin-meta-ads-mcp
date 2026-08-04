# MCP v2 Compatibility Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Prevent fresh `uvx` installs from resolving incompatible MCP SDK 2.x and publish the fix as `v0.1.10`.

**Architecture:** Keep the existing MCP 1.x server implementation and express its compatibility boundary in package metadata. Protect that boundary with a focused metadata regression test, then verify the built wheel and a real stdio initialization handshake before release.

**Tech Stack:** Python 3.11+, Hatchling, pytest, Ruff, mypy, uv/uvx, GitHub Actions

---

### Task 1: Add the dependency regression test

**Files:**
- Create: `tests/test_package_metadata.py`

**Step 1: Write the failing test**

Read `pyproject.toml` with `tomllib` and assert that project dependencies contain
`mcp>=1.28,<2`.

**Step 2: Run the test to verify it fails**

Run: `pytest tests/test_package_metadata.py -q`

Expected: FAIL because the project currently declares `mcp>=1.0.0`.

### Task 2: Apply the compatible dependency range and release version

**Files:**
- Modify: `pyproject.toml`
- Modify: `README.md`

**Step 1: Write the minimal metadata fix**

Change the MCP dependency to `mcp>=1.28,<2`, bump the project version to `0.1.10`, and update
the README release-tag example to `v0.1.10`.

**Step 2: Run the focused test to verify it passes**

Run: `pytest tests/test_package_metadata.py -q`

Expected: PASS.

### Task 3: Verify and release

**Files:**
- Verify all changed files and built distribution metadata.

**Step 1: Run static and unit verification**

Run: `pytest -q`, `ruff check .`, and `mypy src`.

Expected: all commands exit successfully.

**Step 2: Build and smoke-test the package**

Run: `uv build`, inspect the wheel metadata, and start the package under `uvx` with an MCP
initialize request.

Expected: the wheel requires `mcp>=1.28,<2` and the server returns a successful initialize
result.

**Step 3: Commit and push**

Commit the scoped release changes and push `main` to `origin`.

**Step 4: Trigger and monitor release**

Create and push annotated tag `v0.1.10`, then watch the resulting Release workflow until it
completes successfully.
