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


class TestExtractSenatorFromString:
    """Tests for extract_senator_from_string function."""

    def test_basic_extraction(self) -> None:
        """Test basic senator data extraction."""
        test_cases = {
            "Bailey Island - Senate District 23 - Matthea E.L. Daughtry (D-Cumberland)": ("23", "Bailey Island", "Matthea E.L. Daughtry", "D"),
            "Bingham - Senate District 5 - Russell J. Black (R-Franklin)": ("5", "Bingham", "Russell J. Black", "R"),
            "Cornish - Senate District 22 - James D. Libby (R-Cumberland)": ("22", "Cornish", "James D. Libby", "R"),
        }

        for input_str, expected in test_cases.items():
            result = extract_senator_from_string(input_str)
            assert result == expected

    def test_plantation_extraction(self) -> None:
        """Test extraction with plantation names."""
        input_str = "Cary Plantation - Senate District 2 - Trey L. Stewart (R-Aroostook)"
        expected = ("2", "Cary Plantation", "Trey L. Stewart", "R")
        assert extract_senator_from_string(input_str) == expected

    def test_long_municipality_name(self) -> None:
        """Test extraction with long municipality names."""
        input_str = "Central Aroostook Unorganized Territory - Senate District 2 - Trey L. Stewart (R-Aroostook)"
        expected = ("2", "Central Aroostook Unorganized Territory", "Trey L. Stewart", "R")
        assert extract_senator_from_string(input_str) == expected

    def test_township_with_trailing_dash(self) -> None:
        """Test extraction with township names that have trailing dashes."""
        input_str = "West Central Franklin Township- Senate District 5 - Russell J. Black (R-Franklin)"
        expected = ("5", "West Central Franklin Township", "Russell J. Black", "R")
        assert extract_senator_from_string(input_str) == expected

    def test_independent_party(self) -> None:
        """Test extraction with Independent party affiliation."""
        input_str = "Bridgton - Senate District 18 - Richard A. Bennett (I-Oxford)"
        expected = ("18", "Bridgton", "Richard A. Bennett", "I")
        assert extract_senator_from_string(input_str) == expected

    def test_whitespace_normalization(self) -> None:
        """Test that multiple spaces and newlines are normalized."""
        input_str = "Harpswell  -  Senate District  23  -  Matthea E.L. Daughtry  (D-Cumberland)"
        expected = ("23", "Harpswell", "Matthea E.L. Daughtry", "D")
        assert extract_senator_from_string(input_str) == expected

    def test_no_senate_district(self) -> None:
        """Test that empty tuple is returned when 'Senate District' is missing."""
        input_str = "Random text without senate district info"
        expected = ("", "", "", "")
        assert extract_senator_from_string(input_str) == expected

    def test_malformed_input(self) -> None:
        """Test that empty tuple is returned for malformed input."""
        input_str = "Senate District 5 - incomplete data"
        expected = ("", "", "", "")
        assert extract_senator_from_string(input_str) == expected


class TestExtractEmailFromContent:
    """Tests for extract_email_from_content function."""

    def test_email_in_mailto_link(self) -> None:
        """Test extraction of email from mailto link."""
        html = """
        <div id="content">
            <p><strong>Email</strong>: <a href="mailto:Chip.Curry@legislature.maine.gov">Chip.Curry@legislature.maine.gov</a></p>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        content_div = soup.find("div", id="content")
        if not isinstance(content_div, Tag):
            pytest.fail("content_div is not of class bs4.Tag")

        email = extract_email_from_content(content_div, "Chip Curry")
        assert email == "Chip.Curry@legislature.maine.gov"

    def test_email_with_space_in_mailto(self) -> None:
        """Test extraction when mailto has a space."""
        html = """
        <div id="content">
            <p><strong>Email</strong>: <a href="mailto: senator@legislature.maine.gov">senator@legislature.maine.gov</a></p>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        content_div = soup.find("div", id="content")
        if not isinstance(content_div, Tag):
            pytest.fail("content_div is not of class bs4.Tag")

        email = extract_email_from_content(content_div, "Test Senator")
        assert email == "senator@legislature.maine.gov"

    def test_email_in_plain_text(self) -> None:
        """Test extraction of email from plain text."""
        html = """
        <div id="content">
            <p><strong>Email</strong>: test.senator@legislature.maine.gov</p>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        content_div = soup.find("div", id="content")
        if not isinstance(content_div, Tag):
            pytest.fail("content_div is not of class bs4.Tag")

        email = extract_email_from_content(content_div, "Test Senator")
        assert email == "test.senator@legislature.maine.gov"

    def test_email_case_insensitive(self) -> None:
        """Test that 'email' keyword is case insensitive."""
        html = """
        <div id="content">
            <p><strong>EMAIL</strong>: <a href="mailto:senator@legislature.maine.gov">senator@legislature.maine.gov</a></p>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        content_div = soup.find("div", id="content")
        if not isinstance(content_div, Tag):
            pytest.fail("content_div is not of class bs4.Tag")

        email = extract_email_from_content(content_div, "Test Senator")
        assert email == "senator@legislature.maine.gov"

    def test_no_email_found(self) -> None:
        """Test that empty string is returned when no email is found."""
        html = """
        <div id="content">
            <p><strong>Phone</strong>: (207) 123-4567</p>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        content_div = soup.find("div", id="content")
        if not isinstance(content_div, Tag):
            pytest.fail("content_div is not of class bs4.Tag")

        email = extract_email_from_content(content_div, "Test Senator")
        assert email == ""


class TestExtractPhonesFromContent:
    """Tests for extract_phones_from_content function."""

    def test_home_and_state_house_phones(self) -> None:
        """Test extraction of both home and state house phones."""
        html = """
        <div id="content">
            <p><b>Home</b>: (207) 323-9976</p>
            <p><strong>State House</strong>: (207) 287-1515</p>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        content_div = soup.find("div", id="content")
        if not isinstance(content_div, Tag):
            pytest.fail("content_div is not of class bs4.Tag")

        home, state_house = extract_phones_from_content(content_div, "Test Senator")
        assert home == "(207) 323-9976"
        assert state_house == "(207) 287-1515"

    def test_cell_phone_grouped_with_home(self) -> None:
        """Test that cell phones are grouped with home phones."""
        html = """
        <div id="content">
            <p><b>Home</b>: (207) 323-9976</p>
            <p><b>Cell</b>: (207) 555-1234</p>
            <p><strong>State House</strong>: (207) 287-1515</p>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        content_div = soup.find("div", id="content")
        if not isinstance(content_div, Tag):
            pytest.fail("content_div is not of class bs4.Tag")

        home, state_house = extract_phones_from_content(content_div, "Test Senator")
        assert home == "(207) 323-9976, (207) 555-1234"
        assert state_house == "(207) 287-1515"

    def test_phone_formats(self) -> None:
        """Test various phone number formats."""
        html = """
        <div id="content">
            <p><b>Home</b>: 207-323-9976</p>
            <p><strong>State House</strong>: 207.287.1515</p>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        content_div = soup.find("div", id="content")
        if not isinstance(content_div, Tag):
            pytest.fail("content_div is not of class bs4.Tag")

        home, state_house = extract_phones_from_content(content_div, "Test Senator")
        assert "207-323-9976" in home
        assert "207.287.1515" in state_house

    def test_no_phones_found(self) -> None:
        """Test that empty strings are returned when no phones are found."""
        html = """
        <div id="content">
            <p><strong>Email</strong>: senator@legislature.maine.gov</p>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        content_div = soup.find("div", id="content")
        if not isinstance(content_div, Tag):
            pytest.fail("content_div is not of class bs4.Tag")

        home, state_house = extract_phones_from_content(content_div, "Test Senator")
        assert home == ""
        assert state_house == ""


class TestExtractCommitteesFromContent:
    """Tests for extract_committees_from_content function."""

    def test_committee_extraction(self) -> None:
        """Test extraction of committee assignments."""
        html = """
        <div id="content">
            <p><strong>Committee Assignments</strong>:</p>
            <p>Housing and Economic Development (Chair)</p>
            <p>Criminal Justice and Public Safety</p>
            <p>Engrossed Bills</p>
            <p>Senatorial Vote</p>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        content_div = soup.find("div", id="content")
        if not isinstance(content_div, Tag):
            pytest.fail("content_div is not of class bs4.Tag")

        committees = extract_committees_from_content(content_div)
        expected = "Housing and Economic Development (Chair); Criminal Justice and Public Safety; Engrossed Bills; Senatorial Vote"
        assert committees == expected

    def test_committee_extraction_stops_at_next_section(self) -> None:
        """Test that committee extraction stops at the next section with <strong> tag."""
        html = """
        <div id="content">
            <p><strong>Committee Assignments</strong>:</p>
            <p>Labor and Housing (Chair)</p>
            <p>Appropriations and Financial Affairs</p>
            <p><strong>Legislative Service</strong>: House 126-128</p>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        content_div = soup.find("div", id="content")
        if not isinstance(content_div, Tag):
            pytest.fail("content_div is not of class bs4.Tag")

        committees = extract_committees_from_content(content_div)
        expected = "Labor and Housing (Chair); Appropriations and Financial Affairs"
        assert committees == expected

    def test_no_committees_found(self) -> None:
        """Test that empty string is returned when no committees are found."""
        html = """
        <div id="content">
            <p><strong>Email</strong>: senator@legislature.maine.gov</p>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        content_div = soup.find("div", id="content")
        if not isinstance(content_div, Tag):
            pytest.fail("content_div is not of class bs4.Tag")

        committees = extract_committees_from_content(content_div)
        assert committees == ""

    def test_committee_case_insensitive(self) -> None:
        """Test that 'Committee Assignments' is case insensitive."""
        html = """
        <div id="content">
            <p><strong>COMMITTEE ASSIGNMENTS</strong>:</p>
            <p>Test Committee</p>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        content_div = soup.find("div", id="content")
        if not isinstance(content_div, Tag):
            pytest.fail("content_div is not of class bs4.Tag")

        committees = extract_committees_from_content(content_div)
        assert committees == "Test Committee"


class TestScrapeDetailedSenatorInfo:
    """Tests for scrape_detailed_senator_info function."""

    @patch("src.main.time.sleep")
    def test_404_page_handling(self, mock_sleep: Mock) -> None:  #  noqa ARG002
        """Test that 404 pages are handled gracefully."""
        html = """
        <div id="content">
            <h1>Page Not Found</h1>
            <p>The page you are looking for does not exist.</p>
            </div>
        """

        mock_http = Mock(spec=urllib3.PoolManager)
        mock_response = Mock()
        mock_response.data = html.encode("utf-8")
        mock_http.request.return_value = mock_response

        result = scrape_detailed_senator_info(mock_http, "legislature.maine.gov", "/district1", "Test Senator")
        assert result == ("", "", "", "")

    @patch("src.main.time.sleep")
    def test_successful_scrape(self, mock_sleep: Mock) -> None:  #  noqa ARG002
        """Test successful scraping of senator details."""
        html = """
        <div id="content">
            <h1>Sen. Chip Curry (D-Waldo)</h1>
            <p><strong>Email</strong>: <a href="mailto:Chip.Curry@legislature.maine.gov">Chip.Curry@legislature.maine.gov</a></p>
            <p><b>Home</b>: (207) 323-9976</p>
            <p><strong>State House</strong>: (207) 287-1515</p>
            <p><strong>Committee Assignments</strong>:</p>
            <p>Housing and Economic Development (Chair)</p>
            </div>
        """

        mock_http = Mock(spec=urllib3.PoolManager)
        mock_response = Mock()
        mock_response.data = html.encode("utf-8")
        mock_http.request.return_value = mock_response

        email, home, state_house, committees = scrape_detailed_senator_info(mock_http, "legislature.maine.gov", "/district11", "Chip Curry")

        assert email == "Chip.Curry@legislature.maine.gov"
        assert home == "(207) 323-9976"
        assert state_house == "(207) 287-1515"
        assert "Housing and Economic Development (Chair)" in committees


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
        municipalities = [
            ("5", "Town1", "Russell J. Black", "R", ""),
        ]

        result = get_unique_senators_with_links(municipalities)

        assert result["Russell J. Black"] == ""


class TestCollectMunicipalitiesWithSenators:
    """Tests for collect_municipalities_with_senators function."""

    def test_municipality_collection(self) -> None:
        """Test collection of municipalities with senator data."""
        html_content = """
        <div id="content">
            <p>Abbot - Senate District 4 - <a href="/District4">Stacey K. Guerin</a> (R-Penobscot)</p>
            <p>Acton - Senate District 22 - <a href="/district22">James D. Libby</a> (R-York)</p>
            <p><strong>-B-</strong></p>
            <p><a href="#A">top of page</a></p>
            <p>Bangor - Senate District 9 - <a href="/district9">Joseph M. Baldacci</a> (D-Penobscot)</p>
        </div>
        """

        mock_http = Mock(spec=urllib3.PoolManager)
        mock_response = Mock()
        mock_response.data = html_content.encode("utf-8")
        mock_http.request.return_value = mock_response

        with patch("src.main.SenateURL.StateLegislatureNetloc", "legislature.maine.gov") and patch("src.main.SenateURL.MunicipalityListPath", "/find-senator"):
            result = collect_municipalities_with_senators(mock_http)

        assert len(result) == 3  #  noqa: PLR2004
        assert result[0] == ("4", "Abbot", "Stacey K. Guerin", "R", "/District4")
        assert result[1] == ("22", "Acton", "James D. Libby", "R", "/district22")
        assert result[2] == ("9", "Bangor", "Joseph M. Baldacci", "D", "/district9")

    def test_skips_non_senator_paragraphs(self) -> None:
        """Test that non-senator paragraphs are skipped."""
        html_content = """
        <div id="content">
            <h1>Find your State Senator</h1>
            <p>Click on the first letter of your town.</p>
            <p>Abbot - Senate District 4 - <a href="/District4">Stacey K. Guerin</a> (R-Penobscot)</p>
        </div>
        """

        mock_http = Mock(spec=urllib3.PoolManager)
        mock_response = Mock()
        mock_response.data = html_content.encode("utf-8")
        mock_http.request.return_value = mock_response

        with patch("src.main.SenateURL.StateLegislatureNetloc", "legislature.maine.gov") and patch("src.main.SenateURL.MunicipalityListPath", "/find-senator"):
            result = collect_municipalities_with_senators(mock_http)

        assert len(result) == 1
        assert result[0][1] == "Abbot"  # Only the valid senator entry
