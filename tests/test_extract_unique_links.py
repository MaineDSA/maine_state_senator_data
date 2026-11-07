import pytest

from src.main import get_unique_senators_with_links


@pytest.fixture
def scraped_munis() -> list[tuple[str, str, str, str, str]]:
    """Tuples with municipality data to use when testing processing of unique entries."""
    return [
        ("23", "Bailey Island", "Matthea E.L. Daughtry", "D", "/district23"),
        ("23", "Brunswick", "Matthea E.L. Daughtry", "D", "/district23"),
        ("5", "Bingham", "Russell J. Black", "R", "/district5"),
        ("5", "Athens", "Russell J. Black", "R", "/district5"),
        ("5", "Anson", "Russell J. Black", "R", "/distric5"),  # typo with majority
        ("7", "Atlantic", "Nicole C. Grohoski", "D", ""),
        ("7", "Bar Harbor", "Nicole C. Grohoski", "D", ""),  # all links missing
        ("8", "Alton", "Michael Tipping", "D", "/district8"),
        ("8", "Argyle Township", "Michael Tipping", "D", "/distric8"),  # typo without majority
        ("4", "Abbot", "Stacey K. Guerin", "R", "/district8"),
        ("4", "Argyle Township", "Stacey K. Guerin", "R", ""),  # some links missing
    ]


def test_extract_unique_senator_links(scraped_munis: list[tuple[str, str, str, str, str]]) -> None:
    """Test extraction of unique senators with their links."""
    result = get_unique_senators_with_links(scraped_munis)

    assert len(result) == 5
    assert result["Matthea E.L. Daughtry"] == "/district23"
    assert result["Russell J. Black"] == "/district5"
    assert result["Nicole C. Grohoski"] == ""


def test_most_common_link_chosen(scraped_munis: list[tuple[str, str, str, str, str]]) -> None:
    """Test that the most common link is chosen when there are typos."""
    result = get_unique_senators_with_links(scraped_munis)

    assert result["Russell J. Black"] == "/district5"
