from collections.abc import Callable
from unittest.mock import Mock, patch

import pytest
import urllib3
from bs4 import BeautifulSoup, Tag

from src.main import (
    collect_municipalities_with_senators,
    extract_committees_from_content,
    extract_email_from_content,
    extract_phones_from_content,
    extract_senator_from_string,
    get_unique_senators_with_links,
    scrape_detailed_senator_info,
)


# Fixtures for reusable components
@pytest.fixture
def parse_html_content() -> Callable:
    """Fixture that returns a function to parse HTML and extract content div."""

    def _parse(html: str) -> Tag:
        soup = BeautifulSoup(html, "html.parser")
        content_div = soup.find("div", id="content")
        if not isinstance(content_div, Tag):
            pytest.fail("content_div is not of class bs4.Tag")
        return content_div

    return _parse


@pytest.fixture
def mock_http_response() -> Callable:
    """Fixture for creating mock HTTP responses."""

    def _create_response(html_content: str) -> Mock:
        mock_http = Mock(spec=urllib3.PoolManager)
        mock_response = Mock()
        mock_response.data = html_content.encode("utf-8")
        mock_http.request.return_value = mock_response
        return mock_http

    return _create_response


class TestExtractSenatorFromString:
    """Tests for extract_senator_from_string function."""

    @pytest.mark.parametrize(
        ("input_str", "expected"),
        [
            (
                "Bailey Island - Senate District 23 - Matthea E.L. Daughtry (D-Cumberland)",
                ("23", "Bailey Island", "Matthea E.L. Daughtry", "D"),
            ),
            (
                "Bingham - Senate District 5 - Russell J. Black (R-Franklin)",
                ("5", "Bingham", "Russell J. Black", "R"),
            ),
            (
                "Cornish - Senate District 22 - James D. Libby (R-Cumberland)",
                ("22", "Cornish", "James D. Libby", "R"),
            ),
            (
                "Cary Plantation - Senate District 2 - Trey L. Stewart (R-Aroostook)",
                ("2", "Cary Plantation", "Trey L. Stewart", "R"),
            ),
            (
                "Central Aroostook Unorganized Territory - Senate District 2 - Trey L. Stewart (R-Aroostook)",
                ("2", "Central Aroostook Unorganized Territory", "Trey L. Stewart", "R"),
            ),
            (
                "West Central Franklin Township- Senate District 5 - Russell J. Black (R-Franklin)",
                ("5", "West Central Franklin Township", "Russell J. Black", "R"),
            ),
            (
                "Bridgton - Senate District 18 - Richard A. Bennett (I-Oxford)",
                ("18", "Bridgton", "Richard A. Bennett", "I"),
            ),
            (
                "Harpswell  -  Senate District  23  -  Matthea E.L. Daughtry  (D-Cumberland)",
                ("23", "Harpswell", "Matthea E.L. Daughtry", "D"),
            ),
        ],
        ids=[
            "basic",
            "basic_2",
            "basic_3",
            "plantation",
            "long_name",
            "trailing_dash",
            "independent_party",
            "whitespace_normalization",
        ],
    )
    def test_valid_extraction(self, input_str: str, expected: tuple) -> None:
        """Test extraction of senator data from valid input strings."""
        result = extract_senator_from_string(input_str)
        assert result == expected

    @pytest.mark.parametrize(
        "input_str",
        [
            "Random text without senate district info",
            "Senate District 5 - incomplete data",
        ],
        ids=["no_senate_district", "malformed_input"],
    )
    def test_invalid_extraction(self, input_str: str) -> None:
        """Test that empty tuple is returned for invalid input."""
        assert extract_senator_from_string(input_str) == ("", "", "", "")


class TestExtractEmailFromContent:
    """Tests for extract_email_from_content function."""

    @pytest.mark.parametrize(
        ("html", "expected_email"),
        [
            (
                '<p><strong>Email</strong>: <a href="mailto:Chip.Curry@legislature.maine.gov">Chip.Curry@legislature.maine.gov</a></p>',
                "Chip.Curry@legislature.maine.gov",
            ),
            (
                '<p><strong>Email</strong>: <a href="mailto: senator@legislature.maine.gov">senator@legislature.maine.gov</a></p>',
                "senator@legislature.maine.gov",
            ),
            (
                '<p><strong>Email</strong>: <a href="mailto:senator@legislature.maine.gov ">senator@legislature.maine.gov</a></p>',
                "senator@legislature.maine.gov",
            ),
            (
                "<p><strong>Email</strong>: test.senator@legislature.maine.gov</p>",
                "test.senator@legislature.maine.gov",
            ),
            (
                "<p><strong>Email</strong>: test.senator [at] legislature.maine.gov</p>",
                "",
            ),
            (
                '<p><strong>Email</strong>: <a href="mailto:senator@legislature.maine.gov ">senator [at] legislature.maine.gov</a></p>',
                "senator@legislature.maine.gov",
            ),
            (
                '<p><strong>EMAIL</strong>: <a href="mailto:senator@legislature.maine.gov">senator@legislature.maine.gov</a></p>',
                "senator@legislature.maine.gov",
            ),
        ],
        ids=[
            "mailto_and_link",
            "mailto_with_leading_space",
            "mailto_with_trailing_space",
            "plain_text",
            "plain_text_invalid_email",
            "mailto_without_text_email",
            "case_insensitive",
        ],
    )
    def test_email_extraction(self, parse_html_content: Callable, html: str, expected_email: str) -> None:
        """Test extraction of email from various HTML formats."""
        content_div = parse_html_content(f'<div id="content">{html}</div>')
        email = extract_email_from_content(content_div, "Test Senator")
        assert email == expected_email

    def test_no_email_found(self, parse_html_content: Callable) -> None:
        """Test that empty string is returned when no email is found."""
        html = '<div id="content"><p><strong>Phone</strong>: (207) 123-4567</p></div>'
        content_div = parse_html_content(html)
        email = extract_email_from_content(content_div, "Test Senator")
        assert email == ""


class TestExtractPhonesFromContent:
    """Tests for extract_phones_from_content function."""

    @pytest.mark.parametrize(
        ("html", "expected_home", "expected_state_house"),
        [
            (
                "<p><b>Home</b>: (207) 323-9976</p><p><strong>State House</strong>: (207) 287-1515</p>",
                "(207) 323-9976",
                "(207) 287-1515",
            ),
            (
                "<p><b>Home</b>: (207) 323-9976</p><p><b>Cell</b>: (207) 555-1234</p><p><strong>State House</strong>: (207) 287-1515</p>",
                "(207) 323-9976, (207) 555-1234",
                "(207) 287-1515",
            ),
            (
                "<p><b>Home</b>: 207-323-9976 or 207-587-9347</p><p><strong>State House</strong>: 207.287.1515</p>",
                "207-323-9976, 207-587-9347",
                "207.287.1515",
            ),
            (
                "<p><b>Home</b>: 207-323-9976</p><p><strong>State House</strong>: 207.287.1515</p>",
                "207-323-9976",
                "207.287.1515",
            ),
        ],
        ids=["basic_phones", "cell_grouped_with_home", "multiple phones of same type", "various_formats"],
    )
    def test_phone_extraction(self, parse_html_content: Callable, html: str, expected_home: str, expected_state_house: str) -> None:
        """Test extraction of phone numbers from various HTML formats."""
        content_div = parse_html_content(f'<div id="content">{html}</div>')
        home, state_house = extract_phones_from_content(content_div, "Test Senator")
        assert home == expected_home
        assert state_house == expected_state_house

    def test_no_phones_found(self, parse_html_content: Callable) -> None:
        """Test that empty strings are returned when no phones are found."""
        html = '<div id="content"><p><strong>Email</strong>: senator@legislature.maine.gov</p></div>'
        content_div = parse_html_content(html)
        home, state_house = extract_phones_from_content(content_div, "Test Senator")
        assert home == ""
        assert state_house == ""


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
    def test_committee_extraction(self, parse_html_content: Callable, html: str, expected: str) -> None:
        """Test extraction of committee assignments."""
        content_div = parse_html_content(f'<div id="content">{html}</div>')
        committees = extract_committees_from_content(content_div)
        assert committees == expected

    def test_no_committees_found(self, parse_html_content: Callable) -> None:
        """Test that empty string is returned when no committees are found."""
        html = '<div id="content"><p><strong>Email</strong>: senator@legislature.maine.gov</p></div>'
        content_div = parse_html_content(html)
        committees = extract_committees_from_content(content_div)
        assert committees == ""


class TestScrapeDetailedSenatorInfo:
    """Tests for scrape_detailed_senator_info function."""

    @pytest.mark.parametrize(
        ("html", "expected"),
        [
            (
                """
                <div id="content">
                    <h1>Page Not Found</h1>
                    <p>The page you are looking for does not exist.</p>
                </div>
                """,
                ("", "", "", ""),
            ),
            (
                """
                <div id="invalid_content">
                    <h1>Page Not Found</h1>
                    <p>The page you are looking for does not exist.</p>
                </div>
                """,
                ("", "", "", ""),
            ),
            (
                """
                <div id="content">
                    <h1>Sen. Chip Curry (D-Waldo)</h1>
                    <p><strong>Email</strong>: <a href="mailto:Chip.Curry@legislature.maine.gov">Chip.Curry@legislature.maine.gov</a></p>
                    <p><b>Home</b>: (207) 323-9976</p>
                    <p><strong>State House</strong>: (207) 287-1515</p>
                    <p><strong>Committee Assignments</strong>:</p>
                    <p>Housing and Economic Development (Chair)</p>
                </div>
                """,
                (
                    "Chip.Curry@legislature.maine.gov",
                    "(207) 323-9976",
                    "(207) 287-1515",
                    "Housing and Economic Development (Chair)",
                ),
            ),
        ],
        ids=["404_page", "404_page_invalid_content", "successful_scrape"],
    )
    @patch("src.main.time.sleep")
    def test_scrape_senator_info(self, mock_sleep: Mock, mock_http_response: Callable, html: str, expected: tuple) -> None:  #  noqa: ARG002
        """Test scraping of senator details from various page types."""
        mock_http = mock_http_response(html)
        result = scrape_detailed_senator_info(mock_http, "legislature.maine.gov", "/district1", "Test Senator")

        if expected == ("", "", "", ""):
            assert result == expected
        else:
            email, home, state_house, committees = result
            assert email == expected[0]
            assert home == expected[1]
            assert state_house == expected[2]
            assert expected[3] in committees


class TestGetUniqueSenatorsWithLinks:
    """Tests for get_unique_senators_with_links function."""

    def test_unique_senators_extraction(self) -> None:
        """Test extraction of unique senators with their links."""
        municipalities = [
            ("23", "Bailey Island", "Matthea E.L. Daughtry", "D", "/district23"),
            ("23", "Brunswick", "Matthea E.L. Daughtry", "D", "/district23"),
            ("5", "Bingham", "Russell J. Black", "R", "/district5"),
        ]

        result = get_unique_senators_with_links(municipalities)

        assert len(result) == 2  #  noqa: PLR2004
        assert result["Matthea E.L. Daughtry"] == "/district23"
        assert result["Russell J. Black"] == "/district5"

    def test_most_common_link_chosen(self) -> None:
        """Test that the most common link is chosen when there are typos."""
        municipalities = [
            ("5", "Town1", "Russell J. Black", "R", "/district5"),
            ("5", "Town2", "Russell J. Black", "R", "/district5"),
            ("5", "Town3", "Russell J. Black", "R", "/distric5"),  # typo
        ]

        result = get_unique_senators_with_links(municipalities)
        assert result["Russell J. Black"] == "/district5"

    def test_senator_with_no_link(self) -> None:
        """Test handling of senator with no profile link."""
        municipalities = [("5", "Town1", "Russell J. Black", "R", "")]
        result = get_unique_senators_with_links(municipalities)
        assert result["Russell J. Black"] == ""


class TestCollectMunicipalitiesWithSenators:
    """Tests for collect_municipalities_with_senators function."""

    @pytest.mark.parametrize(
        ("html_content", "expected_results"),
        [
            (
                """
                <div id="content">
                    <p>Abbot - Senate District 4 - <a href="/District4">Stacey K. Guerin</a> (R-Penobscot)</p>
                    <p>Acton - Senate District 22 - <a href="/district22">James D. Libby</a> (R-York)</p>
                    <p><strong>-B-</strong></p>
                    <p><a href="#A">top of page</a></p>
                    <p>Bangor - Senate District 9 - <a href="/district9">Joseph M. Baldacci</a> (D-Penobscot)</p>
                </div>
                """,
                [
                    ("4", "Abbot", "Stacey K. Guerin", "R", "/District4"),
                    ("22", "Acton", "James D. Libby", "R", "/district22"),
                    ("9", "Bangor", "Joseph M. Baldacci", "D", "/district9"),
                ],
            ),
            (
                """
                <div id="content">
                    <h1>Find your State Senator</h1>
                    <p>Click on the first letter of your town.</p>
                    <p>Abbot - Senate District 4 - <a href="/District4">Stacey K. Guerin</a> (R-Penobscot)</p>
                </div>
                """,
                [("4", "Abbot", "Stacey K. Guerin", "R", "/District4")],
            ),
            (
                """
                <div id="content">
                    <p>Abbot - Senate Area 4 - Stacey K. Guerin [R-Penobscot]</p>
                    <p>Abbot - Senate District 8 - <a href="/District8">Kevin S. Guerin</a> (R-Brewer)</p>
                </div>
                """,
                [("8", "Abbot", "Kevin S. Guerin", "R", "/District8")],
            ),
            (
                """
                <div id="invalid_content">
                    <h1>Find your State Senator</h1>
                </div>
                """,
                [],
            ),
        ],
        ids=("multiple_municipalities", "skips_non_senator_paragraphs", "invalid_senator_format", "invalid_content"),
    )
    def test_municipality_collection(self, mock_http_response: Callable, html_content: str, expected_results: list) -> None:
        """Test collection of municipalities with senator data."""
        mock_http = mock_http_response(html_content)

        with (
            patch("src.main.SenateURL.StateLegislatureNetloc", "legislature.maine.gov"),
            patch("src.main.SenateURL.MunicipalityListPath", "/find-senator"),
        ):
            result = collect_municipalities_with_senators(mock_http)

        assert len(result) == len(expected_results)
        for i, expected in enumerate(expected_results):
            assert result[i] == expected
