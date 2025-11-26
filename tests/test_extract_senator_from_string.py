from src.main import extract_senator_from_string


def test_extract_senator_from_string() -> None:
    test_legislators = {
        "Bailey Island - Senate District 23 - Matthea E.L. Daughtry (D-Cumberland)": ("23", "Bailey Island", "Matthea E.L. Daughtry", "D"),
        "Bingham - Senate District 5 - Russell J. Black (R-Franklin)": ("5", "Bingham", "Russell J. Black", "R"),
        "Cornish - Senate District 22 - James D. Libby (R-Cumberland)": ("22", "Cornish", "James D. Libby", "R"),
        "Cary Plantation - Senate District 2 - Trey L. Stewart (R-Aroostook)": ("2", "Cary Plantation", "Trey L. Stewart", "R"),
        "Central Aroostook Unorganized Territory - Senate District 2 - Trey L. Stewart (R-Aroostook)": (
            "2",
            "Central Aroostook Unorganized Territory",
            "Trey L. Stewart",
            "R",
        ),
        "Harpswell - Senate District 23 - Matthea E.L. Daughtry (D-Cumberland)": ("23", "Harpswell", "Matthea E.L. Daughtry", "D"),
        "West Central Franklin Township- Senate District 5 - Russell J. Black (R-Franklin)": (
            "5",
            "West Central Franklin Township",
            "Russell J. Black",
            "R",
        ),
    }
    for legislator_input, legislator_output in test_legislators.items():
        legislator_data = extract_senator_from_string(legislator_input)
        assert legislator_output == legislator_data
