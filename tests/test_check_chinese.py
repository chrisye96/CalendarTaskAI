"""Tests for scripts/check_chinese.py.

The detector ships with the repo and tells maintainers when un-allowlisted
Chinese sneaks back in. These tests pin the regex coverage, the per-file-
type classifier, and the allowlist matcher so a future tweak doesn't
silently regress detection.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


# Load scripts/check_chinese.py as a module without polluting sys.path.
# The script lives outside the package tree on purpose (it's a tool, not
# importable runtime code), so we load by file path.
_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check_chinese.py"
_spec = importlib.util.spec_from_file_location("check_chinese", _SCRIPT_PATH)
check_chinese = importlib.util.module_from_spec(_spec)
sys.modules["check_chinese"] = check_chinese
_spec.loader.exec_module(check_chinese)


# ---------------------------------------------------------------------------
# Regex coverage: what the detector should and shouldn't flag
# ---------------------------------------------------------------------------

class TestCJKRegex:
    @pytest.mark.parametrize("text", [
        "明天",                  # CJK Unified Ideographs (U+4E00-9FFF)
        "周报",
        "今晚9点",                # mixed ASCII + CJK
        "Chinese: 你好",
        "、",                    # CJK punctuation (U+3000-303F)
        "「example」",           # fullwidth brackets
        "ＡＢＣ",                # fullwidth ASCII (U+FF00-FFEF)
    ])
    def test_flags_chinese(self, text):
        assert check_chinese.CJK_RE.search(text) is not None

    @pytest.mark.parametrize("text", [
        "today, tomorrow, next monday",
        "no Chinese here",
        "emoji-free ASCII: !@#$%^&*()",
        "",
        "hyphen-compound-words",
        "9:00-10:30",
    ])
    def test_passes_pure_ascii(self, text):
        assert check_chinese.CJK_RE.search(text) is None

    def test_pure_japanese_NOT_flagged(self):
        # The detector targets Chinese specifically. Japanese hiragana /
        # katakana sit outside the configured ranges. If we ever need to
        # widen scope this test pins current behavior so the change is
        # intentional.
        assert check_chinese.CJK_RE.search("ひらがな") is None
        assert check_chinese.CJK_RE.search("カタカナ") is None


# ---------------------------------------------------------------------------
# Classifier: where in a source file does the Chinese live?
# ---------------------------------------------------------------------------

class TestClassifier:
    @pytest.mark.parametrize("line, expected", [
        ("# 中文注释", "comment"),
        ('    # nested 中文', "comment"),
        ('"""docstring 中文"""', "docstring"),
        ("'''alt docstring'''", "docstring"),
        ('msg = "中文字符串"', "string"),
        ("msg = '中文'", "string"),
    ])
    def test_python_classification(self, line, expected):
        kind = check_chinese.classify_line(Path("foo.py"), line, 1)
        assert kind == expected

    @pytest.mark.parametrize("line, expected", [
        ("# 标题", "markdown-prose"),
        ("一段中文段落", "markdown-prose"),
        ("```python", "markdown-code"),
        ("    indented code with 中文", "markdown-code"),
    ])
    def test_markdown_classification(self, line, expected):
        kind = check_chinese.classify_line(Path("README.md"), line, 1)
        assert kind == expected

    def test_bat_comments(self):
        # Both REM and @REM and :: are batch comment forms.
        for prefix in ("REM ", "@REM ", "::"):
            kind = check_chinese.classify_line(
                Path("foo.bat"), prefix + "中文注释", 1)
            assert kind == "comment"

    def test_vbs_comments(self):
        kind = check_chinese.classify_line(Path("foo.vbs"), "' 中文注释", 1)
        assert kind == "comment"


# ---------------------------------------------------------------------------
# Allowlist: parser/fixture files where Chinese is the public contract
# ---------------------------------------------------------------------------

class TestAllowlist:
    @pytest.mark.parametrize("path", [
        "task_parser.py",
        "time_parser.py",
        "recurring.py",
        "tests/test_parser.py",
        "tests/test_recurring.py",
    ])
    def test_allowlisted(self, path):
        ok, reason = check_chinese.matches_allowlist(Path(path))
        assert ok is True
        assert reason

    @pytest.mark.parametrize("path", [
        "ai_client.py",     # caller decided to translate this one
        "templates.py",     # caller decided this is fixture content; not yet allowlisted
        "README.md",
        "main.py",
    ])
    def test_not_allowlisted(self, path):
        # These four are deliberately NOT on the allowlist by default;
        # if a future commit adds them, this test will fail and force
        # the maintainer to confirm intent.
        ok, _ = check_chinese.matches_allowlist(Path(path))
        assert ok is False


# ---------------------------------------------------------------------------
# Snippet extraction: keep terminal output readable
# ---------------------------------------------------------------------------

class TestSnippet:
    def test_clips_to_width(self):
        long_line = "x" * 200 + "中文" + "y" * 200
        snippet = check_chinese.extract_snippet(long_line, 200, 202, width=60)
        assert "中文" in snippet
        # Should be much shorter than the full line.
        assert len(snippet) < 100

    def test_short_line_returns_intact(self):
        snippet = check_chinese.extract_snippet("a 中文 b", 2, 4, width=60)
        # No truncation markers when the whole line fits.
        assert "…" not in snippet
        assert "中文" in snippet


# ---------------------------------------------------------------------------
# Smoke test: run the live scanner against a tmp dir and check exit code
# ---------------------------------------------------------------------------

class TestEndToEnd:
    def test_clean_repo_returns_zero(self, tmp_path, monkeypatch):
        # Create a minimal git repo with one ASCII file; main() should
        # report clean and return 0.
        import subprocess
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        (tmp_path / "ok.py").write_text("print('hello')\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t",
             "commit", "-q", "-m", "init"],
            cwd=tmp_path, check=True,
        )
        rc = check_chinese.main(["--root", str(tmp_path)])
        assert rc == 0

    def test_repo_with_chinese_returns_one(self, tmp_path, capsys):
        import subprocess
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        (tmp_path / "bad.py").write_text("# 中文注释\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t",
             "commit", "-q", "-m", "init"],
            cwd=tmp_path, check=True,
        )
        rc = check_chinese.main(["--root", str(tmp_path)])
        assert rc == 1
        # Output should mention bad.py so the user can find it.
        out = capsys.readouterr().out
        assert "bad.py" in out
