from collections.abc import Callable

import pytest
from bs4 import Tag

from src.main import extract_committees_from_content


class TestExtractCommitteesFromContent:
    """Tests for extract_committees_from_content function."""

    @pytest.mark.parametrize(
        ("html", "expected"),
        [
            (
                """
                <p><strong>Committee Assignments</strong>:</p>
                <p>Housing and Economic Development (Chair)</p>
                <p>Criminal Justice and Public Safety</p>
                <p>Engrossed Bills</p>
                <p>Senatorial Vote</p>
                """,
                "Housing and Economic Development (Chair); Criminal Justice and Public Safety; Engrossed Bills; Senatorial Vote",
            ),
            (
                """
                <p><strong>Committee Assignments</strong>:</p>
                <p>Labor and Housing (Chair)</p>
                <p>Appropriations and Financial Affairs</p>
                <p><strong>Legislative Service</strong>: House 126-128</p>
                """,
                "Labor and Housing (Chair); Appropriations and Financial Affairs",
            ),
            (
                """<p><strong>COMMITTEE ASSIGNMENTS</strong>:</p>
                <p>Test Committee</p>""",
                "Test Committee",
            ),
        ],
        ids=["multiple_committees", "stops_at_next_section", "case_insensitive"],
    )
    def test_committee_extraction(self, parse_html_content: Callable[[str], Tag], html: str, expected: str) -> None:
        """Test extraction of committee assignments."""
        content_div = parse_html_content(f'<div id="content">{html}</div>')
        committees = extract_committees_from_content(content_div)

        assert committees == expected

    def test_no_committees_found(self, parse_html_content: Callable[[str], Tag]) -> None:
        """Test that empty string is returned when no committees are found."""
        html = '<div id="content"><p><strong>Email</strong>: senator@legislature.maine.gov</p></div>'

        content_div = parse_html_content(html)
        committees = extract_committees_from_content(content_div)

        assert committees == ""
