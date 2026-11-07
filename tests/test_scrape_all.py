import urllib3
from pytest_mock import MockerFixture

from src.main import scrape_all


def test_scrape_all_scrapes_all(mocker: MockerFixture, mocked_poolmanager: urllib3.PoolManager) -> None:
    """Test that `scrape_all` finds the right number of entries and makes requests of all endpoints (end-to-end test)."""
    mocker.patch("src.main.time.sleep")

    senators = scrape_all(mocked_poolmanager)

    assert len(senators) == 145
    assert all(len(senator_data) == 8 for senator_data in senators)
