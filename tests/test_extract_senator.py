import pytest

from src.main import SenatorScraperError, extract_senator_from_string


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
        ("input_str", "exception_msg"),
        [
            ("Random text without senate district info", "'Senate District' not found in"),
            ("Senate District 5 - incomplete data", "Regex match not found, can't extract senator district data from"),
        ],
        ids=["no_senate_district", "malformed_input"],
    )
    def test_invalid_extraction(self, input_str: str, exception_msg: str) -> None:
        """Test that exception is raised for invalid data."""
        with pytest.raises(SenatorScraperError, match=f"{exception_msg} '{input_str}'"):
            extract_senator_from_string(input_str)
