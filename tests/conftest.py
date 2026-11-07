import re
from collections.abc import Callable
from pathlib import Path

import pytest
import urllib3
from bs4 import BeautifulSoup, Tag
from pytest_urllib3 import Urllib3Mock

from src.legislature_urls import SenateURL


@pytest.fixture
def parse_html_content() -> Callable[[str], Tag]:
    """Parse HTML and extract content div."""

    def _parse(html: str) -> Tag:
        soup = BeautifulSoup(html, "html.parser")
        content_div = soup.find("div", id="content")
        if not isinstance(content_div, Tag):
            pytest.fail("content_div is not of class bs4.Tag")
        return content_div

    return _parse


@pytest.fixture
def examples_dir() -> Path:
    """Provide Path object of example pages folder."""
    tests_folder = Path(__file__).parent

    return tests_folder / "page_examples"


@pytest.fixture
def muni_page(examples_dir: Path) -> str:
    """Provide example find your senator page content."""
    sample_muni_page = examples_dir / "find-your-senator.html"

    return sample_muni_page.read_text()


@pytest.fixture
def detail_examples_dir(examples_dir: Path) -> Path:
    """Provide Path object of example districts folder."""
    return examples_dir / "districts"


@pytest.fixture
def detail_examples(detail_examples_dir: Path) -> dict[int, str]:
    """Provide dictionary of example district detail page content keyed to district numbers."""
    all_districts = {}
    for page in detail_examples_dir.glob("*.html"):
        district_number = int(page.name.removeprefix("district").removesuffix(".html"))
        all_districts[district_number] = page.read_text()

    return all_districts


@pytest.fixture
def mocked_poolmanager(urllib3_mock: Urllib3Mock, muni_page: str, detail_examples: dict[int, str]) -> urllib3.PoolManager:
    """Provide a urllib3 PoolManager with all mocked GET requests."""
    urllib3_mock.add_response(
        method="GET", url=f"https://{SenateURL.StateLegislatureNetloc}/{SenateURL.MunicipalityListPath}", content=muni_page.encode("utf-8")
    )
    for district_no, district_content in detail_examples.items():
        request_url = f"https://{SenateURL.StateLegislatureNetloc}/district{district_no}"
        urllib3_mock.add_response(method="GET", url=re.compile(request_url), content=district_content.encode("utf-8"), is_reusable=True)

    return urllib3.PoolManager()
