from collections.abc import Callable

import pytest
from bs4 import Tag

from src.main import extract_phones_from_content


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
def test_phone_extraction(parse_html_content: Callable[[str], Tag], html: str, expected_home: str, expected_state_house: str) -> None:
    """Test extraction of phone numbers from various HTML formats."""
    html = f'<div id="content">{html}</div>'
    content_div = parse_html_content(html)

    home, state_house = extract_phones_from_content(content_div, "Test Senator")

    assert home == expected_home
    assert state_house == expected_state_house


def test_no_phones_found(parse_html_content: Callable[[str], Tag], detail_examples: dict[int, str]) -> None:
    """Test that empty strings are returned when no phones are found."""
    html_without_phone = detail_examples[18].replace("<p><strong>State House</strong>:&nbsp;(207) 287-1540</p>", "")
    content_div = parse_html_content(html_without_phone)

    home, state_house = extract_phones_from_content(content_div, "Test Senator")

    assert home == ""
    assert state_house == ""
