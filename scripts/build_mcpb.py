"""Build a self-contained macOS MCPB from an allowlist, never the working tree."""
from __future__ import annotations

import hashlib
import json
import platform
import shutil
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    if sys.platform != "darwin" or platform.machine() not in {"arm64", "x86_64"}:
        raise SystemExit("Build on a native arm64 or x86_64 Mac")
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    architecture = platform.machine()
    work = ROOT / "build" / f"mcpb-{architecture}"
    stage = work / "bundle"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    subprocess.run([
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile",
        "--name", "flin-meta-ads-mcp", "--paths", str(ROOT / "src"),
        "--copy-metadata", "flin-meta-ads-mcp", "--copy-metadata", "mcp",
        "--distpath", str(stage / "server"), "--workpath", str(work / "pyinstaller"),
        "--specpath", str(work), str(ROOT / "packaging" / "entrypoint.py"),
    ], check=True, cwd=ROOT)
    manifest = json.loads((ROOT / "packaging/manifest.json").read_text())
    if manifest["version"] != version:
        raise SystemExit("Manifest version differs from project version")
    manifest["display_name"] += f" — macOS {architecture}"
    (stage / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    for name in ("LICENSE", "README.md", "SECURITY.md"):
        shutil.copy2(ROOT / name, stage / name)
    shutil.copy2(ROOT / "packaging/requirements.txt", stage / "requirements.txt")
    # Dependencies' license texts are distributed alongside the frozen binary.
    from importlib.metadata import distributions
    for distribution in distributions():
        for file in distribution.files or []:
            if any(part.lower().startswith(("license", "copying", "notice")) for part in file.parts):
                source = Path(distribution.locate_file(file))
                if source.is_file():
                    target = stage / "licenses" / distribution.metadata["Name"] / Path(*file.parts[1:])
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
    output = ROOT / "dist" / f"flin-meta-ads-mcp-{version}-macos-{architecture}.mcpb"
    output.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(stage.rglob("*")):
            if path.is_file():
                if path.is_symlink():
                    raise SystemExit(f"Unexpected symlink: {path}")
                archive.write(path, path.relative_to(stage))
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(".mcpb.sha256").write_text(f"{digest}  {output.name}\n")
    print(output)


if __name__ == "__main__":
    main()
