"""The pure formatting helpers. Every one of these is drawn into a fixed-width
terminal cell, so the length of what comes back matters as much as its text."""

import unittest

from andymod import andy


class Human(unittest.TestCase):
    def test_nothing_is_a_dash(self):
        self.assertEqual(andy.human(0), "-")
        self.assertEqual(andy.human(-1), "-")
        self.assertEqual(andy.human(0, pad=True), "    -")

    def test_units(self):
        self.assertEqual(andy.human(512), "512B")
        self.assertEqual(andy.human(2 ** 10), "1.0K")
        self.assertEqual(andy.human(2 ** 20), "1.0M")
        self.assertEqual(andy.human(2 ** 30), "1.0G")
        self.assertEqual(andy.human(2 ** 40), "1.0T")

    def test_drops_the_decimal_at_three_digits(self):
        self.assertEqual(andy.human(99 * 2 ** 20), "99.0M")
        self.assertEqual(andy.human(100 * 2 ** 20), "100M")

    def test_padding_is_always_the_same_width(self):
        for n in (0, 1, 999, 2 ** 20, 100 * 2 ** 30, 3 * 2 ** 40):
            self.assertEqual(len(andy.human(n, pad=True)), 5, n)


class ParseSize(unittest.TestCase):
    def test_suffixes(self):
        self.assertEqual(andy.parse_size("10M"), 10 * 2 ** 20)
        self.assertEqual(andy.parse_size("1G"), 2 ** 30)
        self.assertEqual(andy.parse_size("2T"), 2 * 2 ** 40)
        self.assertEqual(andy.parse_size("512K"), 512 * 2 ** 10)

    def test_case_and_a_trailing_b_are_ignored(self):
        self.assertEqual(andy.parse_size("10m"), 10 * 2 ** 20)
        self.assertEqual(andy.parse_size("10MB"), 10 * 2 ** 20)
        self.assertEqual(andy.parse_size(" 10mb "), 10 * 2 ** 20)

    def test_bare_numbers_are_bytes(self):
        self.assertEqual(andy.parse_size("4096"), 4096)
        self.assertEqual(andy.parse_size("1.5G"), int(1.5 * 2 ** 30))

    def test_nonsense_is_zero_rather_than_an_exception(self):
        # -m is a display filter; a typo should show everything, not crash.
        self.assertEqual(andy.parse_size("abc"), 0)
        self.assertEqual(andy.parse_size(""), 0)


class Trimming(unittest.TestCase):
    def test_short_enough_is_left_alone(self):
        self.assertEqual(andy.shorten("abc", 10), "abc")
        self.assertEqual(andy.clip_end("abc", 10), "abc")

    def test_result_never_exceeds_the_width(self):
        text = "~/Code/some/deeply/nested/project/node_modules"
        for width in range(0, len(text) + 4):
            self.assertLessEqual(len(andy.shorten(text, width)), max(width, 0), width)
            self.assertLessEqual(len(andy.clip_end(text, width)), max(width, 0), width)

    def test_shorten_keeps_both_ends_of_a_path(self):
        out = andy.shorten("~/Code/project/node_modules", 20)
        self.assertEqual(len(out), 20)
        self.assertIn("…", out)
        self.assertTrue(out.startswith("~/Co"))
        self.assertTrue(out.endswith("modules"))

    def test_clip_end_keeps_the_front(self):
        # A treemap cell is identified by its leading words, so the tail goes.
        self.assertEqual(andy.clip_end("project artifacts", 8), "project…")

    def test_zero_width(self):
        self.assertEqual(andy.shorten("abc", 0), "")
        self.assertEqual(andy.clip_end("abc", 0), "")


class Bar(unittest.TestCase):
    def test_always_fills_its_width(self):
        for fraction in (0.0, 0.01, 0.5, 0.999, 1.0):
            self.assertEqual(len(andy.bar(fraction, 12)), 12, fraction)

    def test_ends(self):
        self.assertEqual(andy.bar(0.0, 5), " " * 5)
        self.assertEqual(andy.bar(1.0, 5), "█" * 5)

    def test_out_of_range_is_clamped(self):
        self.assertEqual(andy.bar(-3.0, 4), " " * 4)
        self.assertEqual(andy.bar(9.0, 4), "█" * 4)

    def test_eighth_precision(self):
        # a single eighth is visible rather than rounded away
        self.assertNotEqual(andy.bar(1 / 64, 8).strip(), "")

    def test_zero_width(self):
        self.assertEqual(andy.bar(0.5, 0), "")


class Tilde(unittest.TestCase):
    def test_home_itself(self):
        self.assertEqual(andy.tilde(andy.HOME), "~")

    def test_under_home(self):
        self.assertEqual(andy.tilde(andy.HOME + "/Code"), "~/Code")

    def test_a_sibling_of_home_is_not_rewritten(self):
        # ~/Code vs /Users/someone-else: the prefix matches as bytes but not as
        # a path, and the separator check is what tells them apart.
        self.assertEqual(andy.tilde(andy.HOME + "-backup"), andy.HOME + "-backup")


class Ink(unittest.TestCase):
    def test_disabled_ink_is_the_identity(self):
        ink = andy.Ink(False)
        self.assertEqual(ink.red("x"), "x")
        self.assertEqual(ink.magnitude(2 ** 40, "x"), "x")

    def test_enabled_ink_wraps_and_resets(self):
        ink = andy.Ink(True)
        self.assertTrue(ink.red("x").startswith("\033["))
        self.assertTrue(ink.red("x").endswith("\033[0m"))


if __name__ == "__main__":
    unittest.main()
