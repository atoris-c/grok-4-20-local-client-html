#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path


PATTERNS = {
    "xai/openai style API key": re.compile(r"\b(?:xai|sk)-(?:proj-)?[A-Za-z0-9_-]{16,}\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "Private key block": re.compile(r"-----BEGIN (?:[A-Z ]+)?PRIVATE KEY-----"),
    "Likely hardcoded secret assignment": re.compile(
        r"""(?ix)
        \b(?:api[_-]?key|token|secret|password)\b
        \s*[:=]\s*
        ["']
        ([^"'\\]{12,})
        ["']
        """
    ),
    "Potential SSN": re.compile(r"\b(?!000|666|9\d\d)\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b"),
}

IGNORED_SECRET_VALUES = {
    "xai-...",
    "xai-your_key_here",
    "sk-your_key_here",
    "your_api_key_here",
    "api_key_here",
    "changemechangeme",
}

TEXT_SUFFIX_ALLOWLIST = {
    ".py",
    ".html",
    ".js",
    ".css",
    ".json",
    ".md",
    ".txt",
    ".yml",
    ".yaml",
    ".toml",
    ".ini",
    ".env",
    ".bat",
    ".sh",
}


def get_repo_files(repo_root: Path) -> list[Path]:
    try:
        output = subprocess.check_output(
            ["git", "ls-files"],
            cwd=repo_root,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []

    files = []
    for rel in output.splitlines():
        path = repo_root / rel
        if not path.is_file():
            continue

        suffix = path.suffix.lower()
        if suffix in TEXT_SUFFIX_ALLOWLIST:
            files.append(path)
            continue

        if not suffix and is_probably_text_file(path):
            files.append(path)
    return files


def should_skip_generic_secret(match_text: str) -> bool:
    lowered = match_text.lower()
    if lowered in IGNORED_SECRET_VALUES:
        return True
    return bool(re.fullmatch(r"\{[^{}]+\}", match_text.strip()))


def is_probably_text_file(path: Path) -> bool:
    try:
        head = path.read_bytes()[:1024]
    except OSError:
        return False
    return b"\x00" not in head


def scan_file(path: Path) -> list[tuple[int, str, str]]:
    findings: list[tuple[int, str, str]] = []
    try:
        content = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return findings

    for line_no, line in enumerate(content.splitlines(), start=1):
        for name, pattern in PATTERNS.items():
            for match in pattern.finditer(line):
                if name == "Likely hardcoded secret assignment":
                    secret_value = match.group(1)
                    if should_skip_generic_secret(secret_value):
                        continue
                findings.append((line_no, name, match.group(0).strip()))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan repository files for likely hardcoded secrets and personal data leaks."
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root to scan (default: current directory).",
    )
    args = parser.parse_args()

    repo_root = Path(args.root).resolve()
    files = get_repo_files(repo_root)
    if not files:
        print("No tracked files found to scan.")
        return 0

    total_findings = 0
    for file_path in files:
        findings = scan_file(file_path)
        for line_no, finding_type, snippet in findings:
            total_findings += 1
            print(f"[{finding_type}] {file_path.relative_to(repo_root)}:{line_no} -> {snippet}")

    if total_findings:
        print(f"\nSecurity check failed: found {total_findings} potential leak(s).")
        return 1

    print("Security check passed: no obvious hardcoded secrets or personal data leaks found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
