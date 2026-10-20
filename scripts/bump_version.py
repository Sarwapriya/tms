#!/usr/bin/env python3
"""
Martech TMS - Automatic Version Updater & Git Hook
--------------------------------------------------
Automatically bumps the patch version in version.txt on git commits,
or provides CLI commands to manually inspect and increment versions.

Usage:
    python scripts/bump_version.py --hook          # Run by git pre-commit hook
    python scripts/bump_version.py --current       # Display current version
    python scripts/bump_version.py --patch         # Bump patch: 3.0.6 -> 3.0.7
    python scripts/bump_version.py --minor         # Bump minor: 3.0.6 -> 3.1.0
    python scripts/bump_version.py --major         # Bump major: 3.0.6 -> 4.0.0
    python scripts/bump_version.py --set "3.1.0 (Python)"  # Set specific version
    python scripts/bump_version.py --install-hook # Configure git core.hooksPath
"""

import argparse
import os
import re
import shutil
import subprocess
import sys


def get_repo_root() -> str:
    """Finds the root directory of the repository."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True
        )
        root = res.stdout.strip()
        if root and os.path.isdir(root):
            return os.path.abspath(root)
    except Exception:
        pass
    # Fallback to parent directory of scripts/
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def parse_version(raw_content: str):
    """
    Parses a version string such as '3.0.6 (Python)', 'v1.2.3', or '3.0'.
    Returns: (prefix, major, minor, patch, suffix)
    """
    cleaned = raw_content.strip()
    pattern = re.compile(
        r'^(?P<prefix>\s*v?)'
        r'(?P<major>\d+)'
        r'(?:\.(?P<minor>\d+))?'
        r'(?:\.(?P<patch>\d+))?'
        r'(?P<suffix>.*)$',
        re.IGNORECASE | re.DOTALL
    )
    match = pattern.match(cleaned)
    if not match:
        return "", 3, 0, 0, " (Python)"

    prefix = match.group("prefix") or ""
    major = int(match.group("major"))
    minor = int(match.group("minor")) if match.group("minor") is not None else 0
    patch = int(match.group("patch")) if match.group("patch") is not None else 0
    suffix = match.group("suffix") or ""
    return prefix, major, minor, patch, suffix


def bump_version_string(raw_content: str, bump_type: str = "patch") -> tuple[str, str]:
    """
    Computes bumped version string.
    Returns: (old_version, new_version)
    """
    prefix, major, minor, patch, suffix = parse_version(raw_content)
    old_version = f"{prefix}{major}.{minor}.{patch}{suffix}".strip()

    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump_type == "minor":
        minor += 1
        patch = 0
    elif bump_type == "patch":
        patch += 1
    else:
        raise ValueError(f"Unknown bump type: {bump_type}")

    new_version = f"{prefix}{major}.{minor}.{patch}{suffix}".strip()
    return old_version, new_version


def read_version_file(repo_root: str) -> tuple[str, str, str]:
    """
    Reads version.txt and determines newline type.
    Returns: (raw_content, newline, file_path)
    """
    version_file = os.path.join(repo_root, "version.txt")
    if os.path.exists(version_file):
        with open(version_file, "rb") as f:
            raw_bytes = f.read()
        newline = "\r\n" if b"\r\n" in raw_bytes else "\n"
        raw_content = raw_bytes.decode("utf-8", errors="replace")
    else:
        raw_content = "3.0.0 (Python)"
        newline = "\r\n" if os.name == "nt" else "\n"
    return raw_content, newline, version_file


def write_version_file(version_file: str, version_text: str, newline: str) -> None:
    """Writes updated version string to version.txt with appropriate newline."""
    clean_text = version_text.strip()
    with open(version_file, "w", encoding="utf-8", newline=newline) as f:
        f.write(clean_text + newline)


def get_staged_files(repo_root: str) -> list[str]:
    """Returns list of staged files in Git index."""
    try:
        res = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=repo_root,
            capture_output=True,
            text=True
        )
        if res.returncode == 0:
            return [line.strip().replace("\\", "/") for line in res.stdout.splitlines() if line.strip()]
    except Exception:
        pass
    return []


def has_staged_version_changes(repo_root: str) -> bool:
    """Checks whether version.txt already has staged differences against HEAD."""
    try:
        # Check if HEAD exists
        rev_check = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=repo_root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        if rev_check.returncode != 0:
            # First commit; if version.txt is in staged files, it's manually staged
            return "version.txt" in get_staged_files(repo_root)

        res = subprocess.run(
            ["git", "diff", "--cached", "--quiet", "--", "version.txt"],
            cwd=repo_root
        )
        # returncode 1 means diff exists
        return res.returncode == 1
    except Exception:
        return False


def is_in_rebase_or_merge(repo_root: str) -> bool:
    """Detects if git is in middle of rebase, cherry-pick, or merge."""
    git_dir = os.path.join(repo_root, ".git")
    if os.path.isfile(git_dir):
        try:
            with open(git_dir, "r", encoding="utf-8") as f:
                line = f.read().strip()
                if line.startswith("gitdir:"):
                    git_dir = os.path.abspath(os.path.join(repo_root, line[7:].strip()))
        except Exception:
            pass

    if not os.path.isdir(git_dir):
        return False

    # Skip during rebase or cherry-pick sequence to prevent conflict cascades
    rebase_merge = os.path.exists(os.path.join(git_dir, "rebase-merge"))
    rebase_apply = os.path.exists(os.path.join(git_dir, "rebase-apply"))
    cherry_pick = os.path.exists(os.path.join(git_dir, "CHERRY_PICK_HEAD"))

    return rebase_merge or rebase_apply or cherry_pick


def run_pre_commit_hook(repo_root: str) -> int:
    """
    Pre-commit hook handler:
    1. Skips during rebase or cherry-pick.
    2. Checks if any files are staged; if none, does nothing.
    3. If version.txt has explicit manual staged changes, keeps them.
    4. Otherwise, auto-increments patch version, updates version.txt, and stages it.
    """
    if is_in_rebase_or_merge(repo_root):
        return 0

    staged_files = get_staged_files(repo_root)
    if not staged_files:
        return 0

    if "version.txt" in staged_files and has_staged_version_changes(repo_root):
        print("[version-hook] Notice: version.txt has manual staged changes. Preserving current edit.")
        return 0

    raw_content, newline, version_file = read_version_file(repo_root)
    old_ver, new_ver = bump_version_string(raw_content, "patch")

    write_version_file(version_file, new_ver, newline)

    # Stage the updated version.txt
    add_res = subprocess.run(
        ["git", "add", "version.txt"],
        cwd=repo_root,
        capture_output=True,
        text=True
    )
    if add_res.returncode != 0:
        print(f"[version-hook] Warning: Failed to stage version.txt: {add_res.stderr.strip()}", file=sys.stderr)
        return 0

    print(f"[version-hook] Auto-bumped version.txt: {old_ver} -> {new_ver}")
    return 0


def install_git_hooks(repo_root: str) -> None:
    """Configures git to use .githooks and installs the pre-commit hook."""
    githooks_dir = os.path.join(repo_root, ".githooks")
    os.makedirs(githooks_dir, exist_ok=True)

    hook_file = os.path.join(githooks_dir, "pre-commit")
    hook_content = (
        "#!/bin/sh\n"
        "# Git pre-commit hook to automatically bump version in version.txt\n"
        "\n"
        "if command -v python >/dev/null 2>&1; then\n"
        "    python scripts/bump_version.py --hook\n"
        "elif command -v python3 >/dev/null 2>&1; then\n"
        "    python3 scripts/bump_version.py --hook\n"
        "elif command -v py >/dev/null 2>&1; then\n"
        "    py -3 scripts/bump_version.py --hook\n"
        "else\n"
        "    echo \"[version-hook] Warning: Python not found in PATH. Skipping version bump.\"\n"
        "fi\n"
        "exit $?\n"
    )

    with open(hook_file, "w", encoding="utf-8", newline="\n") as f:
        f.write(hook_content)

    # Set git core.hooksPath .githooks
    try:
        subprocess.run(["git", "config", "core.hooksPath", ".githooks"], cwd=repo_root, check=True)
        print("[version-hook] Configured: git config core.hooksPath .githooks")
    except Exception as e:
        print(f"[version-hook] Warning: Could not configure core.hooksPath: {e}")

    # Also copy to .git/hooks/pre-commit as fallback
    git_hooks_dir = os.path.join(repo_root, ".git", "hooks")
    if os.path.isdir(git_hooks_dir):
        fallback_hook = os.path.join(git_hooks_dir, "pre-commit")
        try:
            shutil.copyfile(hook_file, fallback_hook)
            print("[version-hook] Installed fallback hook to .git/hooks/pre-commit")
        except Exception:
            pass

    print("[version-hook] Git hook installation complete.")


def main():
    parser = argparse.ArgumentParser(description="Martech TMS Version Manager")
    parser.add_argument("--hook", action="store_true", help="Execute as git pre-commit hook")
    parser.add_argument("--current", action="store_true", help="Display current version")
    parser.add_argument("--patch", action="store_true", help="Bump patch version (e.g. 3.0.6 -> 3.0.7)")
    parser.add_argument("--minor", action="store_true", help="Bump minor version (e.g. 3.0.6 -> 3.1.0)")
    parser.add_argument("--major", action="store_true", help="Bump major version (e.g. 3.0.6 -> 4.0.0)")
    parser.add_argument("--set", dest="set_version", type=str, help="Set explicit version string")
    parser.add_argument("--install-hook", action="store_true", help="Install git pre-commit hook")

    args = parser.parse_args()
    repo_root = get_repo_root()

    if args.install_hook:
        install_git_hooks(repo_root)
        return 0

    if args.hook:
        return run_pre_commit_hook(repo_root)

    raw_content, newline, version_file = read_version_file(repo_root)

    if args.current:
        print(raw_content.strip())
        return 0

    if args.set_version:
        new_ver = args.set_version.strip()
        write_version_file(version_file, new_ver, newline)
        print(f"Version set to: {new_ver}")
        return 0

    if args.major:
        old_ver, new_ver = bump_version_string(raw_content, "major")
        write_version_file(version_file, new_ver, newline)
        print(f"Bumped major version: {old_ver} -> {new_ver}")
        return 0

    if args.minor:
        old_ver, new_ver = bump_version_string(raw_content, "minor")
        write_version_file(version_file, new_ver, newline)
        print(f"Bumped minor version: {old_ver} -> {new_ver}")
        return 0

    if args.patch:
        old_ver, new_ver = bump_version_string(raw_content, "patch")
        write_version_file(version_file, new_ver, newline)
        print(f"Bumped patch version: {old_ver} -> {new_ver}")
        return 0

    # Default action if no argument provided
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
