import pytest
import urllib3
from pytest_urllib3 import Urllib3Mock

from src.main import SenatorScraperError, collect_municipalities_with_senators


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
                    <p>Abbot - Senate District 4 - Stacey K. Guerin [R-Penobscot]</p>
                    <p>Abbot - Senate District 8 - <a href="/District8">Kevin S. Guerin</a> (R-Brewer)</p>
                </div>
                """,
                (
                    SenatorScraperError,
                    "Regex match not found, can't extract senator district data from ",
                ),
            ),
            (
                """
                <div id="invalid_content">
                    <h1>Find your State Senator</h1>
                </div>
                """,
                (SenatorScraperError, "Content div not found"),
            ),
        ],
        ids=("multiple_municipalities", "skips_non_senator_paragraphs", "invalid_senator_format", "invalid_content"),
    )
    def test_municipality_collection(self, urllib3_mock: Urllib3Mock, html_content: str, expected_results: list | tuple[Exception, str]) -> None:
        """Test collection of municipalities with senator data."""
        urllib3_mock.add_response(method="GET", content=html_content.encode("utf-8"))
        http = urllib3.PoolManager()

        if isinstance(expected_results, tuple):
            expected_exception = expected_results[0]
            expected_err_msg = expected_results[1]
            with pytest.raises(expected_exception, match=expected_err_msg):  # type: ignore[ty:invalid-argument-type]
                collect_municipalities_with_senators(http)

        else:
            result = collect_municipalities_with_senators(http)

            assert len(result) == len(expected_results)
            for i, expected in enumerate(expected_results):
                assert result[i] == expected
