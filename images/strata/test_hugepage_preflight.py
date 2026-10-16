import contextlib
import io
import random
import unittest
from unittest.mock import patch

from hugepage_preflight import main


def meminfo(free, reserved, size="2048 kB"):
    return (f"HugePages_Total: 46909\nHugePages_Free: {free}\n"
            f"HugePages_Rsvd: {reserved}\nHugepagesize: {size}\n")


class HugepagePreflightTests(unittest.TestCase):
    def test_admission_accounts_for_unfaulted_reservations(self):
        rng = random.Random(46909)
        for _ in range(100):
            required = rng.randint(1, 100000)
            reserved = rng.randint(0, 10000)
            for delta in (-1, 0, 1):
                free = required + reserved + delta
                with self.subTest(required=required, reserved=reserved, delta=delta), \
                        patch.dict("os.environ", {"STRATA_REQUIRED_HUGEPAGES": str(required)}, clear=True), \
                        patch("hugepage_preflight.Path.read_text", return_value=meminfo(free, reserved)), \
                        contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(main(), int(delta < 0))

    def test_observed_shortfall_prevents_start(self):
        with patch.dict("os.environ", {"STRATA_REQUIRED_HUGEPAGES": "46909"}, clear=True), \
                patch("hugepage_preflight.Path.read_text", return_value=meminfo(46899, 62)), \
                contextlib.redirect_stderr(io.StringIO()) as stderr:
            self.assertEqual(main(), 1)
        self.assertIn("have 46837", stderr.getvalue())
        self.assertIn("refusing to start", stderr.getvalue())

    def test_invalid_memory_information_fails_closed(self):
        for data in ("", meminfo(46909, 0, "1048576 kB"),
                     meminfo(-1, 0), meminfo(46909, -1),
                     meminfo("unknown", 0), "HugePages_Free:\n"):
            with self.subTest(data=data), \
                    patch.dict("os.environ", {"STRATA_REQUIRED_HUGEPAGES": "46909"}, clear=True), \
                    patch("hugepage_preflight.Path.read_text", return_value=data), \
                    contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(), 1)

    def test_unreadable_memory_information_fails_closed(self):
        with patch.dict("os.environ", {"STRATA_REQUIRED_HUGEPAGES": "46909"}, clear=True), \
                patch("hugepage_preflight.Path.read_text", side_effect=OSError("unavailable")), \
                contextlib.redirect_stderr(io.StringIO()) as stderr:
            self.assertEqual(main(), 1)
        self.assertIn("unavailable", stderr.getvalue())

    def test_invalid_requirement_fails_closed(self):
        for value in ("", "0", "-1", "auto"):
            with self.subTest(value=value), \
                    patch.dict("os.environ", {"STRATA_REQUIRED_HUGEPAGES": value}, clear=True), \
                    contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(), 1)

    def test_other_lanes_do_not_require_linux_meminfo(self):
        with patch.dict("os.environ", {}, clear=True), \
                patch("hugepage_preflight.Path.read_text", side_effect=OSError("unavailable")):
            self.assertEqual(main(), 0)


if __name__ == "__main__":
    unittest.main()
