import unittest
from unittest.mock import patch

import mealie_feedback_server as mealie


class MealieBoundaryTests(unittest.TestCase):
    def test_rejects_non_sidecar_mealie_url(self) -> None:
        for raw in ("https://mealie:9000", "http://example.com:9000", "http://mealie:9000/api"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                mealie.mealie_base_url(raw)

    def test_validates_rating_bounds_before_network_access(self) -> None:
        with patch.object(mealie, "request_mealie") as request:
            for rating in (-0.1, 5.1, float("inf"), float("nan")):
                with self.subTest(rating=rating), self.assertRaises(ValueError):
                    mealie.set_recipe_rating("dinner", rating)
            request.assert_not_called()

    def test_rejects_empty_and_oversized_comments(self) -> None:
        for text in ("", "   ", "x" * (mealie.MAX_COMMENT_LENGTH + 1)):
            with self.subTest(length=len(text)), self.assertRaises(ValueError):
                mealie.normalize_comment(text)

    def test_normalizes_uuid(self) -> None:
        value = "E50BC670-675D-4D4C-BC7B-7160EA942800"
        self.assertEqual(mealie.normalize_uuid(value, "id"), value.casefold())


if __name__ == "__main__":
    unittest.main()
