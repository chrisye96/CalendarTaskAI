"""Detect Chinese characters across the repo.

What this is for
----------------
CalendarTaskAI is built for users who type tasks in Chinese OR English,
so the parser modules legitimately contain Chinese regex patterns and
the test suite has Chinese fixture strings. Everything else (file names,
comments, docstrings, log messages, README prose, error messages) should
be English.

This script scans the working tree, classifies every match by where it
appears (filename / comment / string-literal / markdown-prose), and
prints a report grouped by file. Files where Chinese is *expected* sit
on an explicit allowlist; matches in those files are noted but not
counted toward the failure tally.

Usage
-----
    python scripts/check_chinese.py            # report + exit non-zero on un-allowlisted hits
    python scripts/check_chinese.py --json     # machine-readable for CI
    python scripts/check_chinese.py --include-allowed  # show allowlisted hits too

Exit codes
----------
    0 - no un-allowlisted Chinese found
    1 - one or more un-allowlisted Chinese matches found
    2 - bad invocation
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

# CJK ranges that should trip the detector:
#   U+3000-303F  CJK symbols & punctuation (e.g. 、 。 「 」)
#   U+4E00-9FFF  CJK Unified Ideographs (the main Chinese block)
#   U+FF00-FFEF  Halfwidth & Fullwidth forms (fullwidth ASCII like ：，)
# We deliberately exclude the bopomofo / hiragana / katakana ranges -
# the detector is for Chinese specifically.
CJK_RE = re.compile(r"[　-〿一-鿿＀-￯]")
# Run-length match used to trim context: a contiguous run of CJK + adjacent ASCII
RUN_RE = re.compile(r"[　-〿一-鿿＀-￯]+")

# Files where Chinese is part of the public contract (parser regex
# patterns matching Chinese input, fixture data exercising those
# parsers). Glob-style; matched against the path relative to repo root.
ALLOWLIST: dict[str, str] = {
    "task_parser.py":     "Chinese date regex patterns",
    "time_parser.py":     "Chinese time regex patterns",
    "recurring.py":       "Chinese recurring rule patterns",
    "tests/test_*.py":    "fixture strings exercising Chinese parsing",
}

# Binary file extensions we never want to scan.
BINARY_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",
    ".pyc", ".pyo", ".pyd", ".dll", ".exe", ".so",
    ".zip", ".tar", ".gz", ".7z", ".rar",
    ".pdf", ".db", ".sqlite",
    ".woff", ".woff2", ".ttf", ".otf",
}

# Directories we never enter.
SKIP_DIRS = {".git", "__pycache__", "build", "dist", ".venv", "venv", ".pytest_cache"}


@dataclass
class Hit:
    path: str           # repo-relative path
    line: int           # 1-indexed line number; 0 means "in the filename itself"
    column: int         # 1-indexed column of first matching character
    kind: str           # "filename" | "comment" | "docstring" | "string" | "markdown-prose" | "markdown-code" | "other"
    snippet: str        # small slice of context with the matching run
    runs: list[str] = field(default_factory=list)  # the actual Chinese runs
    allowlisted: bool = False
    allowlist_reason: str = ""


def list_tracked_files(repo_root: Path) -> list[Path]:
    """Use `git ls-files -z` so .gitignore'd cruft isn't scanned and
    non-ASCII filenames (e.g. `启动CalendarTaskAI.bat`) come through
    unquoted. The default `git ls-files` would emit them as octal
    escapes like `"\\345\\220\\257..."`, which we'd then fail to find
    on disk and silently skip from the report."""
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )
    # -z separator is NUL; decode the raw bytes ourselves so a path
    # containing CJK round-trips correctly regardless of the system
    # locale.
    names = result.stdout.decode("utf-8").split("\x00")
    return [repo_root / name for name in names if name]


def is_binary_path(p: Path) -> bool:
    if p.suffix.lower() in BINARY_EXTS:
        return True
    # Some files have no extension; do a small read and see if it's
    # mostly binary (cheap heuristic: any NUL byte in first 8 KB).
    try:
        with p.open("rb") as f:
            chunk = f.read(8192)
        return b"\x00" in chunk
    except OSError:
        return True


def matches_allowlist(rel: Path) -> tuple[bool, str]:
    """Match a relative path against ALLOWLIST glob patterns."""
    rel_posix = rel.as_posix()
    for pattern, reason in ALLOWLIST.items():
        # Simple glob: match against full path AND just the basename, so
        # "task_parser.py" works whether the file is at root or in a subdir.
        if rel.match(pattern) or Path(rel.name).match(pattern):
            return True, reason
    return False, ""


def classify_line(path: Path, line: str, line_no: int) -> str:
    """Best-effort classify what kind of source location the line is.

    This is heuristic, not an AST walk - good enough for triage.
    """
    suffix = path.suffix.lower()
    stripped = line.lstrip()
    if suffix in {".py"}:
        if stripped.startswith("#"):
            return "comment"
        if stripped.startswith(('"""', "'''", '"', "'")):
            # Could be a docstring or a string assignment; cheaper to lump.
            return "docstring" if stripped.startswith(('"""', "'''")) else "string"
        # Fall back to "string" if the match is inside quotes; a lazy
        # regex-based string detector misclassifies edge cases but is
        # correct for the common case of `foo = "中文"` and `f"前缀{x}"`.
        if '"' in line or "'" in line:
            return "string"
        return "other"
    if suffix in {".md", ".markdown"}:
        if stripped.startswith("```") or line.startswith("    "):
            return "markdown-code"
        return "markdown-prose"
    if suffix in {".bat", ".cmd"}:
        # @REM and `REM ` are batch-file comments.
        if stripped.upper().startswith(("REM ", "@REM ", "::")):
            return "comment"
        return "other"
    if suffix == ".vbs":
        if stripped.startswith("'"):
            return "comment"
        return "other"
    return "other"


def extract_snippet(line: str, match_start: int, match_end: int, width: int = 60) -> str:
    """Return ~width chars of context around the match, clipped at line ends."""
    pad = max(0, (width - (match_end - match_start)) // 2)
    start = max(0, match_start - pad)
    end = min(len(line), match_end + pad)
    snippet = line[start:end].rstrip("\n")
    if start > 0:
        snippet = "…" + snippet
    if end < len(line):
        snippet = snippet + "…"
    return snippet


def scan_file(path: Path, repo_root: Path) -> list[Hit]:
    """Scan one file and return all Chinese hits in it (filename + content)."""
    hits: list[Hit] = []
    rel = path.relative_to(repo_root)

    # 1. The filename itself.
    if CJK_RE.search(path.name):
        runs = RUN_RE.findall(path.name)
        is_allow, reason = matches_allowlist(rel)
        hits.append(Hit(
            path=str(rel),
            line=0,
            column=0,
            kind="filename",
            snippet=path.name,
            runs=runs,
            allowlisted=is_allow,
            allowlist_reason=reason,
        ))

    # 2. The contents.
    if is_binary_path(path):
        return hits
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return hits

    is_allow, reason = matches_allowlist(rel)
    for i, line in enumerate(text.splitlines(), start=1):
        for m in RUN_RE.finditer(line):
            hits.append(Hit(
                path=str(rel),
                line=i,
                column=m.start() + 1,
                kind=classify_line(path, line, i),
                snippet=extract_snippet(line, m.start(), m.end()),
                runs=[m.group()],
                allowlisted=is_allow,
                allowlist_reason=reason,
            ))
    return hits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true",
                        help="emit machine-readable JSON instead of human report")
    parser.add_argument("--include-allowed", action="store_true",
                        help="show hits inside allowlisted files too")
    parser.add_argument("--root", type=Path, default=None,
                        help="repo root (default: parent of this script)")
    args = parser.parse_args(argv)

    repo_root = args.root or Path(__file__).resolve().parents[1]
    files = list_tracked_files(repo_root)

    all_hits: list[Hit] = []
    for path in files:
        if not path.exists():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        all_hits.extend(scan_file(path, repo_root))

    # Drop allowlisted hits unless the caller wants them in the output.
    if not args.include_allowed:
        reported = [h for h in all_hits if not h.allowlisted]
    else:
        reported = all_hits

    if args.json:
        print(json.dumps({"hits": [asdict(h) for h in reported]}, ensure_ascii=False, indent=2))
    else:
        _print_human_report(reported, all_hits, repo_root)

    # Exit code is driven by un-allowlisted hits only, regardless of --include-allowed.
    failing = [h for h in all_hits if not h.allowlisted]
    return 1 if failing else 0


def _print_human_report(reported: list[Hit], all_hits: list[Hit], repo_root: Path) -> None:
    if not reported:
        print(f"clean: no Chinese found in tracked files (scanned {repo_root})")
        skipped = sum(1 for h in all_hits if h.allowlisted)
        if skipped:
            print(f"  (skipped {skipped} allowlisted hits in parser/fixture files)")
        return

    by_path: dict[str, list[Hit]] = {}
    for h in reported:
        by_path.setdefault(h.path, []).append(h)

    print(f"{len(reported)} Chinese match(es) across {len(by_path)} file(s):\n")
    for path in sorted(by_path):
        hits = by_path[path]
        kinds = {}
        for h in hits:
            kinds[h.kind] = kinds.get(h.kind, 0) + 1
        kind_summary = ", ".join(f"{n} {k}" for k, n in sorted(kinds.items()))
        print(f"  {path}  ({kind_summary})")
        for h in hits[:5]:  # cap per-file detail to keep terminal readable
            loc = "filename" if h.line == 0 else f"L{h.line}:{h.column}"
            print(f"    {loc:<14} [{h.kind:<14}] {h.snippet}")
        if len(hits) > 5:
            print(f"    …and {len(hits) - 5} more in this file")
        print()

    failing = [h for h in all_hits if not h.allowlisted]
    skipped = [h for h in all_hits if h.allowlisted]
    print(f"summary: {len(failing)} failing, {len(skipped)} allowlisted")
    if skipped and not any(h is skipped[0] for h in reported):
        print("  (allowlisted hits hidden; pass --include-allowed to show them)")


if __name__ == "__main__":
    sys.exit(main())
