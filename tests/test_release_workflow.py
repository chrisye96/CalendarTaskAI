"""Tests for the regex extractor embedded in `.github/workflows/release.yml`.

The release step pulls the topmost `## v...` section out of CHANGELOG.md
and writes it to `release-body.md` so the GitHub Release body shows
exactly that section. If the regex ever silently stops matching (CHANGELOG
heading style drift, encoding hiccup, etc.) the workflow exits non-zero
in CI, but it's nicer to catch it here first.

The extraction logic is duplicated literally from the workflow YAML; if
you change one, change the other. They're 5 lines and we're explicit
about that being intentional.
"""
from __future__ import annotations

import re
import textwrap


def _extract_latest_section(changelog: str) -> str:
    """Mirror of `.github/workflows/release.yml` Extract step."""
    match = re.search(r"^## .+?(?=^## |\Z)", changelog, flags=re.MULTILINE | re.DOTALL)
    if not match:
        raise SystemExit("No `## ...` section found in CHANGELOG.md")
    body = re.sub(r"^## .+?\n", "", match.group(0), count=1)
    return body.strip() + "\n"


class TestChangelogExtractor:
    def test_single_section_pulls_body_only(self):
        text = textwrap.dedent("""\
            # Changelog

            ## v1.0.0 (2026-05-06)

            First release.

            ### Highlights

            - Thing one.
            - Thing two.
            """)
        body = _extract_latest_section(text)
        assert body.startswith("First release.")
        # Heading line must be stripped (GitHub Release UI shows the title).
        assert "## v1.0.0" not in body
        # Top-of-file `# Changelog` boilerplate must be stripped too.
        assert "# Changelog" not in body
        assert body.endswith("- Thing two.\n")

    def test_multiple_sections_pulls_only_topmost(self):
        # Simulates a future CHANGELOG with v1.1 above v1.0.
        text = textwrap.dedent("""\
            # Changelog

            ## v1.1.0 (2026-06-01)

            New stuff.

            ## v1.0.0 (2026-05-06)

            Old stuff.
            """)
        body = _extract_latest_section(text)
        assert body.startswith("New stuff.")
        assert "Old stuff." not in body
        assert "## v1.0.0" not in body

    def test_real_changelog_extracts_v1_section(self):
        # Sanity check against the live file so a future edit that breaks
        # the heading shape (e.g. switching to `# v1.0.0`) trips this test.
        from pathlib import Path
        changelog = Path(__file__).resolve().parents[1] / "CHANGELOG.md"
        body = _extract_latest_section(changelog.read_text(encoding="utf-8"))
        assert "Highlights" in body
        assert "Acknowledgements" in body
        # No leftover top-of-file boilerplate.
        assert not body.startswith("# Changelog")

    def test_empty_or_malformed_aborts(self):
        # No `## ` section at all should fail loudly; a silently empty
        # release body is worse than a build failure.
        import pytest
        with pytest.raises(SystemExit):
            _extract_latest_section("# Changelog\n\nNothing yet.\n")
