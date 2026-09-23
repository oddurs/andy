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
        self.assertIn(andy.ELLIPSIS, out)
        self.assertTrue(out.startswith("~/C"))
        self.assertTrue(out.endswith("modules"))

    def test_clip_end_keeps_the_front(self):
        # A treemap cell is identified by its leading words, so the tail goes.
        keep = 8 - len(andy.ELLIPSIS)
        self.assertEqual(andy.clip_end("project artifacts", 8),
                         "project artifacts"[:keep] + andy.ELLIPSIS)

    def test_zero_width(self):
        self.assertEqual(andy.shorten("abc", 0), "")
        self.assertEqual(andy.clip_end("abc", 0), "")


class Bar(unittest.TestCase):
    def test_always_fills_its_width(self):
        for fraction in (0.0, 0.01, 0.5, 0.999, 1.0):
            self.assertEqual(len(andy.bar(fraction, 12)), 12, fraction)

    def test_ends(self):
        self.assertEqual(andy.bar(0.0, 5), andy.TRACK * 5)
        self.assertEqual(andy.bar(1.0, 5), andy.FULL_CELL * 5)

    def test_out_of_range_is_clamped(self):
        self.assertEqual(andy.bar(-3.0, 4), andy.TRACK * 4)
        self.assertEqual(andy.bar(9.0, 4), andy.FULL_CELL * 4)

    def test_the_bar_and_its_track_fill_the_width_between_them(self):
        for fraction in (0.0, 0.01, 0.37, 0.5, 0.99, 1.0):
            filled, track = andy.bar_parts(fraction, 14)
            self.assertEqual(len(filled) + len(track), 14, fraction)
            self.assertEqual(set(track) - {andy.TRACK}, set())

    def test_a_track_is_not_a_rule(self):
        """An empty bar sits in the same column every row; drawn with the rule
        character it read as a divider running through the list."""
        self.assertNotEqual(andy.TRACK, andy.RULE)

    @unittest.skipUnless(andy.UNICODE, "ASCII has no eighth-cells to draw with")
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
        self.assertEqual(ink.review("x"), "x")
        self.assertEqual(ink.safety(andy.SAFE), andy.SAFE)

    def test_enabled_ink_wraps_and_resets(self):
        ink = andy.Ink(True)
        self.assertTrue(ink.review("x").startswith("\033["))
        self.assertTrue(ink.review("x").endswith("\033[0m"))


if __name__ == "__main__":
    unittest.main()


class ShortPath(unittest.TestCase):
    """cairn 0030. A path is trimmed by dropping whole directories, because
    the middle is what identifies it and the head is shared with its neighbours."""

    def test_short_enough_is_left_alone(self):
        self.assertEqual(andy.short_path("~/Code/rsst/target", 40), "~/Code/rsst/target")

    def test_it_never_exceeds_the_width(self):
        cases = ["~/Library/Group Containers/HUAQ24HBR6.dev.orbstack",
                 "~/.rustup/toolchains/stable-aarch64-apple-darwin",
                 "a/b/c/d/e/f/node_modules", "/one-very-long-single-segment-here",
                 "short", ""]
        for text in cases:
            for width in range(0, 60):
                self.assertLessEqual(len(andy.short_path(text, width)), width,
                                     f"{text!r} at {width}")

    def test_the_identifying_tail_survives(self):
        out = andy.short_path("~/.rustup/toolchains/stable-aarch64-apple-darwin", 30)
        self.assertTrue(out.endswith("stable-aarch64-apple-darwin"), out)

    def test_paths_differing_only_in_the_middle_stay_different(self):
        """The failure this exists for: eight toolchains rendering identically."""
        a = andy.short_path("~/.rustup/toolchains/1.98.1-aarch64-apple-darwin", 30)
        b = andy.short_path("~/.rustup/toolchains/1.93.1-aarch64-apple-darwin", 30)
        self.assertNotEqual(a, b)

    def test_the_tail_is_preferred_over_the_head(self):
        out = andy.short_path(".worktrees/nun/feat/0030-multi-cursor/target", 30)
        self.assertIn("0030-multi-cursor", out,
                      "the branch name is what tells the worktrees apart")

    def test_the_head_is_kept_when_there_is_room(self):
        out = andy.short_path("~/Library/Group Containers/HUAQ24HBR6.dev.orbstack", 30)
        self.assertTrue(out.startswith("~/"), out)

    def test_it_elides_by_segment_not_by_character(self):
        out = andy.short_path("~/a/bbbbbbbbbb/cccccccccc/dddddddddd/target", 24)
        for piece in out.replace(andy.ELLIPSIS, "/").split("/"):
            self.assertIn(piece, ["", "~", "a", "bbbbbbbbbb", "cccccccccc",
                                  "dddddddddd", "target"],
                          f"{piece!r} is half a directory name")

    def test_a_single_segment_keeps_its_end(self):
        out = andy.short_path("/aaaaaaaaaaaaaaaaaaaaaaaaaaaa-tail", 12)
        self.assertTrue(out.endswith("tail"), out)

    def test_home_is_still_abbreviated(self):
        self.assertTrue(andy.short_path(andy.HOME + "/Code", 40).startswith("~/"))
