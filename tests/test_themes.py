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


def styled(theme_name="terminal", custom=None, colours=256, terminal=None):
    table, problems = andy.resolve_theme(theme_name, custom)
    screen = type("S", (), {"getmaxyx": lambda self: (24, 80)})()
    with FakeCurses(colours) as fake:
        tui = andy.Tui(screen, andy.Model(), None, use_mouse=False, theme=table,
                       terminal=terminal)
        tui.styles()
    return tui, fake, problems


def hexrgb(value):
    return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))


def palette(bg, fg, p0, p7, p8, p15):
    return {"bg": hexrgb(bg), "fg": hexrgb(fg), 0: hexrgb(p0), 7: hexrgb(p7),
            8: hexrgb(p8), 15: hexrgb(p15)}


# The subway-seat family, as andy's author runs it: six dark, three light.
# Values from the Ghostty theme files, which is also what the terminal answers
# when asked (checked through herdr: rgb:1e1e/2e2e/2626 and so on).
FAMILY = {
    "Paris Guimard":      palette("#1E2E26", "#D9E1DB", "#30463B", "#C2CBC5", "#74857C", "#E9EEEC"),
    "Paris Catacombes":   palette("#121E19", "#D4DDD7", "#24342C", "#BFC8C2", "#708178", "#E7ECEA"),
    "London Deep Level":  palette("#121A2D", "#D4DAE7", "#232F49", "#BEC6D5", "#6F7C97", "#E7EBF3"),
    "London Moquette":    palette("#1E2941", "#D8DEEA", "#303F61", "#C1C9D8", "#73819C", "#E9EDF5"),
    "Subway Seat":        palette("#362619", "#EDDCBC", "#513B27", "#D9C6A3", "#967B5C", "#F8ECD4"),
    "Subway Seat Tunnel": palette("#24180E", "#E9D8B6", "#3D2C1D", "#D6C3A0", "#917759", "#F6EAD1"),
    "Subway Seat Enamel": palette("#F8EFDF", "#3E2C1E", "#54402F", "#BAA380", "#8C7254", "#CBB898"),
    "London Portland":    palette("#E8F0FF", "#293040", "#3C4557", "#93A7CF", "#697794", "#A8BBE2"),
    "Paris Carrelage":    palette("#EEF2F1", "#27342F", "#3B4742", "#99ABA6", "#6C7C76", "#B0BFBB"),
}
GUIMARD = FAMILY["Paris Guimard"]


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

    def test_no_background_is_ever_painted_but_the_cursors(self):
        tui, fake, _ = styled("terminal", terminal=GUIMARD)
        for pair, (fg, bg) in fake.pairs.items():
            if bg == -1:
                continue
            self.assertEqual(bg, tui.band, f"pair {pair} paints a background "
                                           f"that is not the cursor's")
            self.assertTrue(0 <= bg < 16, "the cursor band is not a palette slot")

    def test_with_nothing_known_no_background_at_all(self):
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


class TheCursorBand(unittest.TestCase):
    """The highlight line. Reverse video turned a careful theme into a pale slab
    with every coloured mark on the row a solid block; the band is what the
    theme's own tools draw, on a slot of the user's own palette."""

    def test_every_theme_in_the_family_gets_a_band(self):
        for name, colours in FAMILY.items():
            self.assertIsNotNone(andy.choose_surface(colours), name)

    def test_the_band_is_visible_and_the_text_on_it_readable(self):
        for name, colours in FAMILY.items():
            band, text = andy.choose_surface(colours)
            ink = colours["fg"] if text == "default" else colours[text]
            self.assertGreaterEqual(andy.contrast(colours[band], colours["bg"]),
                                    andy.VISIBLE, name)
            self.assertGreaterEqual(andy.contrast(ink, colours[band]),
                                    andy.READABLE, name)

    def test_dark_themes_lift_onto_ansi_0_with_the_brightest_white(self):
        """Paris Guimard: #30463B, which the author's tmux uses for exactly this,
        with #E9EEEC -- what their Telescope and Pmenu selections use."""
        for name in ("Paris Guimard", "Paris Catacombes", "London Deep Level",
                     "London Moquette", "Subway Seat", "Subway Seat Tunnel"):
            self.assertEqual(andy.choose_surface(FAMILY[name]), (0, 15), name)

    def test_light_themes_do_not_get_a_dark_bar(self):
        """ANSI 0 is a dark brown or slate in a light theme; dark text on it
        would not read, so a light slot is chosen instead."""
        for name in ("Subway Seat Enamel", "London Portland", "Paris Carrelage"):
            band, text = andy.choose_surface(FAMILY[name])
            self.assertEqual((band, text), (15, "default"), name)

    def test_the_gentlest_passing_slot_wins(self):
        band, _ = andy.choose_surface(GUIMARD)
        lifts = {slot: andy.contrast(GUIMARD[slot], GUIMARD["bg"]) for slot in (0, 8)}
        self.assertEqual(band, min(lifts, key=lifts.get))

    def test_a_palette_where_nothing_works_falls_back_to_reverse(self):
        # ANSI 0 identical to the background, the rest too bright to read on
        flat = palette("#282828", "#EBDBB2", "#282828", "#A89984", "#928374", "#EBDBB2")
        self.assertIsNone(andy.choose_surface(flat))

    def test_nothing_known_is_no_band(self):
        self.assertIsNone(andy.choose_surface({}))
        self.assertIsNone(andy.choose_surface({"bg": (0, 0, 0)}))

    @needs_curses
    def test_the_cursor_row_is_drawn_on_the_band(self):
        tui, fake, _ = styled("terminal", terminal=GUIMARD)
        self.assertEqual(tui.band, 0)
        cursor = andy.ROLE_NAMES.index("selected")
        self.assertEqual(fake.pairs[30 + cursor], (15, 0))

    @needs_curses
    def test_a_mark_keeps_its_colour_on_the_band(self):
        """The failure this exists for: `!` turning into a solid red block."""
        tui, fake, _ = styled("terminal", terminal=GUIMARD)
        review = andy.ROLE_NAMES.index(andy.REVIEW)
        self.assertEqual(fake.pairs[30 + review], (1, 0))

    @needs_curses
    def test_the_cursor_text_is_bold(self):
        tui, _, _ = styled("terminal", terminal=GUIMARD)
        self.assertTrue(tui.selected() & andy.curses.A_BOLD)

    @needs_curses
    def test_without_an_answer_it_is_reverse_video_as_before(self):
        tui, fake, _ = styled("terminal", terminal={})
        self.assertIsNone(tui.band)
        self.assertTrue(tui.selected() & andy.curses.A_REVERSE)
        self.assertEqual([bg for fg, bg in fake.pairs.values() if bg != -1], [])

    @needs_curses
    def test_a_theme_can_name_its_own_band(self):
        tui, fake, _ = styled("mine", {"mine": {"selected": "on color236 bold"}})
        self.assertEqual(tui.band, 236)

    @needs_curses
    def test_mono_keeps_reverse(self):
        tui, _, _ = styled("mono", terminal=GUIMARD)
        self.assertIsNone(tui.band)
        self.assertTrue(tui.selected() & andy.curses.A_REVERSE)


class AskingTheTerminal(unittest.TestCase):
    def test_parsing_a_real_reply(self):
        """Exactly what herdr sent back, on Ghostty, for Paris Guimard."""
        reply = (b"\033]10;rgb:d9d9/e1e1/dbdb\033\\\033]11;rgb:1e1e/2e2e/2626\033\\"
                 b"\033]4;0;rgb:3030/4646/3b3b\033\\\033]4;15;rgb:e9e9/eeee/ecec\007"
                 b"\033[?62;22c")
        got = andy.parse_osc_replies(reply)
        self.assertEqual(got["fg"], hexrgb("#D9E1DB"))
        self.assertEqual(got["bg"], hexrgb("#1E2E26"))
        self.assertEqual(got[0], hexrgb("#30463B"))
        self.assertEqual(got[15], hexrgb("#E9EEEC"))

    def test_short_hex_components_scale(self):
        got = andy.parse_osc_replies(b"\033]11;rgb:f/8/0\033\\")
        self.assertEqual(got["bg"], (255, 136, 0))

    def test_silence_is_empty(self):
        self.assertEqual(andy.parse_osc_replies(b""), {})
        self.assertEqual(andy.parse_osc_replies(b"\033[?1;2c"), {})

    def test_no_terminal_to_ask(self):
        with mock.patch.object(andy.os, "open", side_effect=OSError("no tty")):
            self.assertEqual(andy.query_terminal(), {})

    @needs_curses
    def test_only_asked_when_the_theme_wants_a_band(self):
        with mock.patch.object(andy, "query_terminal", return_value={}) as ask, \
             mock.patch.object(andy.curses, "wrapper", lambda fn: None):
            andy.run_tui(andy.Model(), None, theme=andy.THEMES["mono"])
            ask.assert_not_called()
            andy.run_tui(andy.Model(), None, theme=andy.THEMES["terminal"])
            ask.assert_called_once()


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

    def test_a_background_is_kept_for_the_cursor(self):
        table, problems = andy.resolve_theme(
            "mine", {"mine": {"heading": "on red bold", "selected": "on blue"}})
        self.assertEqual(andy.style_background(table["heading"]), None)
        self.assertIn("bold", table["heading"])
        self.assertEqual(andy.style_background(table["selected"]), 4)
        self.assertTrue(any("only the cursor may have a background" in p
                            for p in problems))

    def test_style_background(self):
        self.assertEqual(andy.style_background("on surface bold"), "surface")
        self.assertEqual(andy.style_background("bold on bright-black"), 8)
        self.assertEqual(andy.style_background("on color236"), 236)
        self.assertIsNone(andy.style_background("bold"))
        self.assertIsNone(andy.style_background("on"))

    def test_on_is_not_mistaken_for_a_colour(self):
        colour, attrs, problems = andy.parse_style("on surface bold")
        self.assertEqual((colour, attrs, problems), (None, frozenset({"bold"}), []))

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
