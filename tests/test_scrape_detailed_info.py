import re

import pytest
import urllib3
from pytest_mock import MockerFixture
from pytest_urllib3 import Urllib3Mock

from src.legislature_urls import SenateURL
from src.main import SenatorScraperError, scrape_detailed_senator_info


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
                (SenatorScraperError, "404 Page Not Found"),
            ),
            (
                """
                <div id="invalid_content">
                    <h1>Page Not Found</h1>
                    <p>The page you are looking for does not exist.</p>
                </div>
                """,
                (SenatorScraperError, "Content div not found"),
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
                [
                    "Chip.Curry@legislature.maine.gov",
                    "(207) 323-9976",
                    "(207) 287-1515",
                    "Housing and Economic Development (Chair)",
                ],
            ),
        ],
        ids=["404_page", "404_page_invalid_content", "successful_scrape"],
    )
    def test_scrape_senator_info(self, mocker: MockerFixture, urllib3_mock: Urllib3Mock, html: str, expected: list[str] | tuple[Exception, str]) -> None:
        """Test scraping of senator details from various page types."""
        mocker.patch("src.main.time.sleep")
        request_url = f"https://{SenateURL.StateLegislatureNetloc}/district1"
        urllib3_mock.add_response(method="GET", url=re.compile(request_url), content=html.encode("utf-8"), is_reusable=True)
        http = urllib3.PoolManager()

        if isinstance(expected, tuple):
            expected_exception = expected[0]
            expected_err_msg = expected[1]
            with pytest.raises(expected_exception, match=expected_err_msg):  # type: ignore[ty:invalid-argument-type]
                scrape_detailed_senator_info(http, "legislature.maine.gov", "/district1", "Test Senator")

        else:
            result = scrape_detailed_senator_info(http, "legislature.maine.gov", "/district1", "Test Senator")
            email, home, state_house, committees = result

            assert email == expected[0]
            assert home == expected[1]
            assert state_house == expected[2]
            assert expected[3] in committees
