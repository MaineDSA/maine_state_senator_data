import csv
import logging
import re
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urlunparse

import urllib3
from bs4 import BeautifulSoup, Tag
from tqdm import tqdm
from urllib3.util.retry import Retry

from .legislature_urls import SenateURL

logging.basicConfig(level=logging.INFO, format="%(levelname)s:maine_state_senator_data:%(name)s:%(message)s")
logger = logging.getLogger(__name__)

# Rate limiting configuration
REQUEST_DELAY = 5  # seconds between requests


def extract_senator_from_string(text: str) -> tuple[str, str, str, str]:
    """
    Extract senator information from paragraph text.

    Format: "Town - Senate District X - Name (Party-County)"
    Returns: (district, town, member, party)
    """
    if "Senate District" not in text:
        return "", "", "", ""

    formatted_text = re.sub(r"[\r\n]", " ", text)
    formatted_text = re.sub(r"\s+", " ", formatted_text)
    logger.debug("Extracting data from municipality string: %s", formatted_text)

    # Extract town, district, member name, and party from the formatted string
    # Pattern: Town - Senate District X - Name (Party-County)
    match = re.match(r"([\W\w\s()-]+)\s*-\s*Senate District\s+(\d+)\s*-\s*(.+?)\s*\((.+?)-", formatted_text)
    if not match:
        logger.error("Regex match not found, can't extract senator district data")
        return "", "", "", ""

    town = match.group(1).strip()
    district = match.group(2).strip()
    member = match.group(3).strip()
    party = match.group(4).strip()

    return district, town, member, party


def extract_email_from_content(content_div: Tag, member: str) -> str:
    """Extract email address from senator profile content."""
    email_pattern = re.compile(r"Email", re.IGNORECASE)
    email_regex = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"

    for p_tag in content_div.find_all("p"):
        if email_pattern.search(p_tag.get_text()):
            # First try to find email in a mailto link (allow optional space after mailto:)
            email_link = p_tag.find("a", href=re.compile(r"^mailto:\s*"))
            if email_link and isinstance(email_link, Tag):
                email_text = email_link.get_text().strip()
                # Validate it's actually an email address
                if re.match(email_regex, email_text):
                    return email_text
                # If link text isn't email, try extracting from href
                href = email_link.get("href", "")
                if isinstance(href, str):
                    # Remove 'mailto:' prefix and any whitespace
                    email_from_href = re.sub(r"^mailto:\s*", "", href).strip()
                    if re.match(email_regex, email_from_href):
                        return email_from_href

            # If no link, find email in plain text with regex
            text = p_tag.get_text()
            email_match = re.search(email_regex, text)
            if email_match:
                return email_match.group().strip()

    logger.warning("Email not found for %s", member)
    return ""


def extract_phones_from_content(content_div: Tag, member: str) -> tuple[str, str]:
    """
    Extract phone numbers from senator profile content.

    Returns: (home_phone, state_house_phone) as comma-separated strings
    """
    home_phones = []
    cell_phones = []
    state_house_phones = []

    home_pattern = re.compile(r"Home", re.IGNORECASE)
    cell_pattern = re.compile(r"Cell", re.IGNORECASE)
    state_house_pattern = re.compile(r"State House", re.IGNORECASE)
    phone_regex = r"\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}"

    for p_tag in content_div.find_all("p"):
        text = p_tag.get_text()

        if home_pattern.search(text):
            home_phones.extend(re.findall(phone_regex, text))
        if cell_pattern.search(text):
            cell_phones.extend(re.findall(phone_regex, text))
        if state_house_pattern.search(text):
            state_house_phones.extend(re.findall(phone_regex, text))

    personal_phones = home_phones + cell_phones
    home_phone = ", ".join(personal_phones) if personal_phones else ""
    state_house_phone = ", ".join(state_house_phones) if state_house_phones else ""

    if not home_phone and not state_house_phone:
        logger.warning("Phone not found for %s", member)

    return home_phone, state_house_phone


def extract_committees_from_content(content_div: Tag) -> str:
    """Extract committee assignments from senator profile content."""
    committee_assignments_pattern = re.compile(r"Committee Assignments", re.IGNORECASE)
    found_committee_section = False
    committee_list = []

    for p_tag in content_div.find_all("p"):
        if committee_assignments_pattern.search(p_tag.get_text()):
            found_committee_section = True
            continue

        if found_committee_section:
            text = p_tag.get_text().strip()
            if not text or p_tag.find("strong"):
                break
            committee_list.append(text)

    return "; ".join(committee_list)


def scrape_detailed_senator_info(http: urllib3.PoolManager, url: str, path: str, member: str) -> tuple[str, str, str, str]:
    """
    Scrape detailed information from a senator's profile page.

    Returns: (email, home_phone, state_house_phone, committees)
    """
    time.sleep(REQUEST_DELAY)  # Rate limiting

    url = urlunparse(("https", url, path, "", "", ""))
    logger.debug("Getting senator data from URL: %s", url)
    response = http.request("GET", url)
    soup = BeautifulSoup(response.data, "html.parser")

    content_div = soup.find("div", id="content")
    if not content_div or not isinstance(content_div, Tag):
        return "", "", "", ""

    # Check if this is the 404 page
    h1_tag = content_div.find("h1")
    if h1_tag and "Page Not Found" in h1_tag.get_text():
        logger.warning("404 Page Not Found encountered for %s at URL: %s", member, url)
        return "", "", "", ""

    email = extract_email_from_content(content_div, member)
    home_phone, state_house_phone = extract_phones_from_content(content_div, member)
    committees = extract_committees_from_content(content_div)

    return email, home_phone, state_house_phone, committees


def collect_municipalities_with_senators(http: urllib3.PoolManager) -> list[tuple[str, str, str, str, str]]:
    """
    Collect all municipalities with their senator info and profile links.

    Returns list of tuples: (district, town, member, party, profile_link)
    """
    page_url = urlunparse(("https", SenateURL.StateLegislatureNetloc, SenateURL.MunicipalityListPath, "", "", ""))
    response = http.request("GET", page_url)
    soup = BeautifulSoup(response.data, "html.parser")

    content_div = soup.find("div", id="content")
    if not content_div or not isinstance(content_div, Tag):
        return []

    municipalities = []

    # Find all paragraph tags containing senator information
    for p_tag in content_div.find_all("p"):
        text = p_tag.get_text()

        if "Senate District" not in text:
            logger.debug("Senate District not found in string: %s", text)
            continue

        district, town, member, party = extract_senator_from_string(text)

        if not district or not member:
            logger.debug("district and member name not found in string: %s", text)
            continue

        senator_link = p_tag.find("a", href=True)
        profile_link = senator_link["href"] if senator_link and isinstance(senator_link, Tag) else ""

        municipalities.append((district, town, member, party, profile_link))

    return municipalities


def get_unique_senators_with_links(municipalities: list[tuple[str, str, str, str, str]]) -> dict[str, str]:
    """
    Get unique senators with their most common profile link.

    Returns dict mapping senator name to profile link
    """
    senator_links: dict[str, list[str]] = {}

    for _district, _town, member, _party, profile_link in municipalities:
        if member not in senator_links:
            senator_links[member] = []
        if profile_link:
            senator_links[member].append(profile_link)

    # For each senator, choose the most common link as there are typos sometimes
    unique_senators = {}
    for member, links in senator_links.items():
        if links:
            most_common_link = Counter(links).most_common(1)[0][0]
            unique_senators[member] = most_common_link
        else:
            unique_senators[member] = ""

    return unique_senators


def scrape_all_unique_senators(http: urllib3.PoolManager, unique_senators: dict[str, str]) -> dict[str, tuple[str, str, str, str]]:
    """
    Scrape detailed info for all unique senators.

    Returns dict mapping senator name to (email, home_phone, state_house_phone, committees)
    """
    senator_details = {}

    logger.info("Scraping %d unique senator profiles...", len(unique_senators))
    for member, profile_link in tqdm(unique_senators.items(), unit="senator"):
        if not profile_link:
            logger.warning("No profile link for %s", member)
            senator_details[member] = ("", "", "", "")
            continue

        email, home_phone, state_house_phone, committees = scrape_detailed_senator_info(http, SenateURL.StateLegislatureNetloc, profile_link, member)
        senator_details[member] = (email, home_phone, state_house_phone, committees)

    return senator_details


def parse_senators_page(http: urllib3.PoolManager) -> list[tuple[str, str, str, str, str, str, str, str]]:
    """
    Load and parse the single-page State Senate listing of all municipalities.

    Returns list of tuples: (district, town, member, party, email, home_phone, state_house_phone, committees)
    """
    logger.info("Scraping Senate municipality data...")
    municipalities = collect_municipalities_with_senators(http)
    unique_senators = get_unique_senators_with_links(municipalities)

    if not unique_senators:
        err_msg = "0 results found."
        raise Exception(err_msg)

    logger.info("Found %d unique senators across %d municipalities", len(unique_senators), len(municipalities))
    logger.info("Scraping Senator profiles data...")
    senator_details = scrape_all_unique_senators(http, unique_senators)

    senators = []
    for district, town, member, party, _profile_link in municipalities:
        details = senator_details.get(member, ("", "", "", ""))
        email, home_phone, state_house_phone, committees = details
        senators.append((district, town, member, party, email, home_phone, state_house_phone, committees))

    return senators


def main() -> None:
    retry_strategy = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504], respect_retry_after_header=True)
    http = urllib3.PoolManager(retries=retry_strategy)
    senators = parse_senators_page(http)

    with Path("senate_municipality_data.csv").open(mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerows([("District", "Town", "Member", "Party", "Email", "Home Phone", "State House Phone", "Committees")])
        writer.writerows(senators)

    logger.info("CSV file 'senate_municipality_data.csv' has been created with %s municipalities.", len(senators))


if __name__ == "__main__":
    main()
