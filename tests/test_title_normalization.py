import unittest

from app.normalize.titles import normalize_title, tokenize_title


class TitleNormalizationTests(unittest.TestCase):
    def test_tokenize_title_removes_amazon_marketplace_noise_and_asin(self) -> None:
        title = (
            "Amazon Basics Prime Sponsored Standing Desk 140cm Electric Height Adjustable "
            "Black ASIN B0XYZ12345 Packof2"
        )

        normalized = normalize_title(title)
        tokens = tokenize_title(title)

        self.assertIn("amazonbasics", normalized)
        self.assertIn("standingdesk", tokens)
        self.assertIn("electric", tokens)
        self.assertIn("adjustable", tokens)
        self.assertNotIn("amazonbasics", tokens)
        self.assertNotIn("prime", tokens)
        self.assertNotIn("sponsored", tokens)
        self.assertNotIn("asin", tokens)
        self.assertFalse(any(token.startswith("b0") for token in tokens))
        self.assertNotIn("packof2", tokens)


if __name__ == "__main__":
    unittest.main()
