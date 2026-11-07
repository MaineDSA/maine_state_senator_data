from collections.abc import Callable

import pytest
from bs4 import Tag

from src.main import SenatorScraperError, extract_email_from_content


@pytest.mark.parametrize(
    ("html", "expected_result"),
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
            SenatorScraperError,
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
def test_email_extraction(parse_html_content: Callable[[str], Tag], html: str, expected_result: str | SenatorScraperError) -> None:
    """Test extraction of email from various HTML formats."""
    test_name = "Test Senator"
    html = f'<div id="content">{html}</div>'
    content_div = parse_html_content(html)

    if isinstance(expected_result, str):
        email = extract_email_from_content(content_div, test_name)
        assert email == expected_result

    else:
        with pytest.raises(expected_result, match=f"Email not found for {test_name}"):  # type: ignore[ty:invalid-argument-type]
            extract_email_from_content(content_div, test_name)


def test_no_email_found(parse_html_content: Callable[[str], Tag]) -> None:
    """Test that empty string is returned when no email is found."""
    test_name = "Test Senator"
    html = '<div id="content"><p><strong>Phone</strong>: (207) 123-4567</p></div>'
    content_div = parse_html_content(html)

    with pytest.raises(SenatorScraperError, match=f"Email not found for {test_name}"):
        extract_email_from_content(content_div, test_name)
