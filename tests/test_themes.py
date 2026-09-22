"""Themes: what inheriting from the terminal means, checked; and the theme
table itself, which may restyle the design language's roles and nothing else.
"""

import io
import unittest
from unittest import mock

from andymod import andy

needs_curses = unittest.skipIf(andy.curses is None, "this Python has no curses")


class FakeCurses:
    """Record what a theme asks the terminal for, on a 256-colour terminal."""

    def __init__(self, colours=256):
        self.colours = colours
        self.pairs = {}

    def __enter__(self):
        curses = andy.curses
        self.patches = [
            mock.patch.object(curses, "start_color", lambda: None),
            mock.patch.object(curses, "use_default_colors", lambda: None),
            mock.patch.object(curses, "init_pair", self.init_pair),
            mock.patch.object(curses, "color_pair", lambda n: n << 8),
            mock.patch.object(curses, "COLORS", self.colours, create=True),
        ]
        for p in self.patches:
            p.start()
        return self

    def __exit__(self, *exc):
        for p in self.patches:
            p.stop()

    def init_pair(self, pair, fg, bg):
        self.pairs[pair] = (fg, bg)


def styled(theme_name="terminal", custom=None, colours=256):
    table, problems = andy.resolve_theme(theme_name, custom)
    screen = type("S", (), {"getmaxyx": lambda self: (24, 80)})()
    with FakeCurses(colours) as fake:
        tui = andy.Tui(screen, andy.Model(), None, use_mouse=False, theme=table)
        tui.styles()
    return tui, fake, problems


@needs_curses
class InheritsFromTheTerminal(unittest.TestCase):
    """cairn 0043. The default theme borrows the window it runs in: the
    terminal's own foreground and background, and the sixteen ANSI colours a
    Ghostty, herdr, kitty or iTerm theme redefines. Nothing absolute."""

    def test_every_colour_is_one_the_terminal_theme_defines(self):
        _, fake, _ = styled("terminal")
        self.assertTrue(fake.pairs, "no colours were asked for at all")
        for pair, (fg, bg) in fake.pairs.items():
            self.assertTrue(fg == -1 or 0 <= fg < 16,
                            f"pair {pair} asks for colour {fg}, which no terminal "
                            f"theme defines, so it will not follow the user's")

    def test_no_background_is_ever_painted(self):
        _, fake, _ = styled("terminal")
        for pair, (fg, bg) in fake.pairs.items():
            self.assertEqual(bg, -1, f"pair {pair} paints a background")

    def test_the_map_is_not_shaded_with_a_fixed_palette(self):
        tui, fake, _ = styled("terminal")
        self.assertEqual(tui.map_pairs, [],
                         "the default map fills cells with colours andy chose")

    def test_the_theme_table_itself_names_only_ansi_colours(self):
        for role in andy.ROLE_NAMES:
            colour, _, problems = andy.parse_style(andy.THEMES["terminal"][role])
            self.assertEqual(problems, [])
            self.assertTrue(colour is None or colour < 16, role)

    def test_classic_is_allowed_its_greys_and_is_not_the_default(self):
        tui, fake, _ = styled("classic")
        self.assertTrue(tui.map_pairs, "classic lost its shaded map")
        self.assertNotEqual(andy.DEFAULT_THEME, "classic")

    def test_a_terminal_without_256_colours_never_gets_the_shade(self):
        tui, _, _ = styled("classic", colours=16)
        self.assertEqual(tui.map_pairs, [])


@needs_curses
class Mono(unittest.TestCase):
    def test_asks_for_no_colour_at_all(self):
        _, fake, _ = styled("mono")
        self.assertEqual(fake.pairs, {})

    def test_every_rating_is_still_a_character(self):
        for rating, mark in andy.MARK.items():
            node = andy.Node(label="x", path="/x", measured=1, safety=rating)
            self.assertEqual(andy.Tui.safety_text(node), mark)

    def test_look_first_keeps_its_weight(self):
        tui, _, _ = styled("mono")
        self.assertNotEqual(tui.consequence(andy.REVIEW), tui.content())


class ParseStyle(unittest.TestCase):
    def test_ansi_names(self):
        self.assertEqual(andy.parse_style("red")[0], 1)
        self.assertEqual(andy.parse_style("cyan")[0], 6)

    def test_bright(self):
        self.assertEqual(andy.parse_style("bright-red")[0], 9)
        self.assertEqual(andy.parse_style("bright-white")[0], 15)

    def test_an_xterm_index(self):
        self.assertEqual(andy.parse_style("color108")[0], 108)

    def test_default_is_the_terminal_foreground(self):
        self.assertIsNone(andy.parse_style("default bold")[0])

    def test_attributes_in_any_order(self):
        colour, attrs, problems = andy.parse_style("bold cyan underline")
        self.assertEqual((colour, attrs, problems),
                         (6, frozenset({"bold", "underline"}), []))

    def test_nonsense_is_named_not_raised(self):
        _, _, problems = andy.parse_style("chartreuse color999")
        self.assertEqual(len(problems), 2)

    def test_an_empty_style_is_plain(self):
        self.assertEqual(andy.parse_style(""), (None, frozenset(), []))


class ResolveTheme(unittest.TestCase):
    def test_a_builtin_is_complete(self):
        table, problems = andy.resolve_theme("terminal")
        self.assertEqual(problems, [])
        for role in andy.ROLE_NAMES:
            self.assertIn(role, table)

    def test_a_custom_theme_overrides_one_role_and_inherits_the_rest(self):
        table, problems = andy.resolve_theme(
            "mine", {"mine": {"inherit": "terminal", "interactive": "magenta"}})
        self.assertEqual(problems, [])
        self.assertEqual(table["interactive"], "magenta")
        self.assertEqual(table[andy.REVIEW], andy.THEMES["terminal"][andy.REVIEW])

    def test_inheritance_defaults_to_the_terminal_theme(self):
        table, _ = andy.resolve_theme("mine", {"mine": {"safe": "blue"}})
        self.assertEqual(table["map"], "outline")

    def test_a_chain_of_custom_themes(self):
        table, problems = andy.resolve_theme("b", {
            "a": {"inherit": "classic", "safe": "blue"},
            "b": {"inherit": "a", "review": "magenta"}})
        self.assertEqual(problems, [])
        self.assertEqual((table["safe"], table["review"], table["map"]),
                         ("blue", "magenta", "shade"))

    def test_a_loop_is_reported_not_followed_forever(self):
        _, problems = andy.resolve_theme("a", {"a": {"inherit": "b"},
                                               "b": {"inherit": "a"}})
        self.assertTrue(any("inherits from itself" in p for p in problems))

    def test_an_unknown_theme_falls_back_and_says_so(self):
        table, problems = andy.resolve_theme("nope")
        self.assertEqual(table, andy.THEMES["terminal"])
        self.assertTrue(any("no theme called 'nope'" in p for p in problems))

    def test_a_theme_can_only_restyle_roles(self):
        """No theme can colour a size by magnitude, because there is no
        magnitude role to colour."""
        table, problems = andy.resolve_theme(
            "mine", {"mine": {"magnitude": "red"}})
        self.assertNotIn("magnitude", table)
        self.assertTrue(any("not a role" in p for p in problems))

    def test_reverse_is_kept_for_the_cursor(self):
        table, problems = andy.resolve_theme(
            "mine", {"mine": {"heading": "reverse bold"}})
        self.assertNotIn("reverse", table["heading"])
        self.assertIn("bold", table["heading"])
        self.assertTrue(any("reserved for the cursor" in p for p in problems))

    def test_a_bad_map_style_is_corrected(self):
        table, problems = andy.resolve_theme("mine", {"mine": {"map": "sparkles"}})
        self.assertEqual(table["map"], "outline")
        self.assertTrue(problems)


class OneThemeDrivesBothHalves(unittest.TestCase):
    """The plain-text reports and the browser read the same table, so
    `andy --commands` cannot disagree with `andy -i` about a colour."""

    def test_sgr(self):
        self.assertEqual(andy.sgr("red"), "31")
        self.assertEqual(andy.sgr("bright-red"), "91")
        self.assertEqual(andy.sgr("color108"), "38;5;108")
        self.assertEqual(andy.sgr("bold cyan"), "1;36")
        self.assertEqual(andy.sgr(""), "")

    def test_ink_follows_a_custom_theme(self):
        table, _ = andy.resolve_theme("mine", {"mine": {"review": "magenta"}})
        self.assertEqual(andy.Ink(True, table).review("x"), "\033[35mx\033[0m")

    def test_a_plain_role_adds_no_escape_codes(self):
        table, _ = andy.resolve_theme("mono")
        self.assertEqual(andy.Ink(True, table).safe("x"), "x")

    @needs_curses
    def test_the_browser_follows_the_same_theme(self):
        custom = {"mine": {"interactive": "magenta"}}
        tui, fake, _ = styled("mine", custom)
        interactive = andy.ROLE_NAMES.index("interactive") + 1
        self.assertEqual(fake.pairs[interactive][0], 5)

    @needs_curses
    def test_a_colour_the_terminal_cannot_show_degrades_to_emphasis(self):
        """cyan on a terminal with no colours: the key hints fall back to
        what mono does there rather than vanishing into plain text."""
        tui, _, _ = styled("terminal", colours=0)
        self.assertNotEqual(tui.interactive(), tui.content())


if __name__ == "__main__":
    unittest.main()
