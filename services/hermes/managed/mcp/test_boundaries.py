import os
import unittest
from unittest.mock import patch

import mealie_feedback_server as mealie
import signal_share_server as signal


class SignalBoundaryTests(unittest.TestCase):
    def test_rejects_wildcard_allowlists(self) -> None:
        for raw in ("*", "all", "ANY", "+15551230000,*"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                signal.parse_allowlist(raw)

    def test_rejects_unlisted_target(self) -> None:
        with self.assertRaises(PermissionError):
            signal.validate_share(
                "user",
                "+15551230000",
                "Dinner is ready",
                allowed_users=frozenset({"+15551239999"}),
                allowed_groups=frozenset(),
            )

    def test_accepts_explicit_user_target(self) -> None:
        self.assertEqual(
            signal.validate_share(
                "user",
                " +15551230000 ",
                " Dinner is ready ",
                allowed_users=frozenset({"+15551230000"}),
                allowed_groups=frozenset(),
            ),
            ("user", "+15551230000", "Dinner is ready"),
        )

    def test_rejects_non_sidecar_signal_url(self) -> None:
        for raw in ("https://signal-cli:8080", "http://example.com:8080", "http://signal-cli:8080/other"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                signal.signal_rpc_url(raw)

    def test_group_send_uses_group_id(self) -> None:
        env = {
            "SIGNAL_HTTP_URL": "http://signal-cli:8080",
            "SIGNAL_ACCOUNT": "+15551230000",
            "HERMES_SIGNAL_SHARE_USERS": "",
            "HERMES_SIGNAL_SHARE_GROUPS": "group-id",
        }
        with patch.dict(os.environ, env, clear=True), patch.object(
            signal,
            "call_signal_rpc",
            return_value={"jsonrpc": "2.0", "result": {"timestamp": 123}, "id": "test"},
        ) as rpc:
            result = signal.share_signal_message("group", "group-id", "Dinner is ready")

        params = rpc.call_args.args[1]["params"]
        self.assertEqual(params["groupId"], "group-id")
        self.assertNotIn("recipient", params)
        self.assertEqual(result["timestamp"], 123)


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
