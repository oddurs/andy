"""The design language, checked.

A language nobody can check is a style guide, and style guides rot. The rules
are mechanical enough to test, so they are: a future change that quietly
recolours a size by magnitude, or reaches past a role for a raw attribute,
fails here rather than shipping.

Each test names the rule it enforces, so a failure teaches it.
"""

import ast
import os
import re
import unittest

from andymod import andy, ANDY

needs_curses = unittest.skipIf(andy.curses is None, "this Python has no curses")

# Where a curses attribute may legitimately be named: the palette, and the
# roles that hand it out.
PALETTE = {"styles"}
ROLES = {"heading", "content", "supporting", "interactive", "selected",
         "consequence",
         # the theme's middle tone, for furniture: rules, outlines, bar tracks
         "muted",
         # consequence at field strength, for a bar rather than a mark
         "tint",
         # the cursor's band lent to another role, so a mark on the cursor row
         # keeps its own colour rather than turning into a solid block
         "lift"}


def source():
    with open(ANDY, encoding="utf-8") as fh:
        return fh.read()


def functions():
    """Every function in andy, with its enclosing class."""
    tree = ast.parse(source())
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    yield node.name, item
        elif isinstance(node, ast.Module):
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    yield "", item


class OneWayToReachAnAttribute(unittest.TestCase):
    """Rule: nothing outside the palette names a curses attribute. Every
    drawing call asks for a role, so a hue can only mean what its role means."""

    def test_curses_attributes_are_named_only_in_the_palette_and_the_roles(self):
        offenders = []
        for cls, fn in functions():
            if fn.name in PALETTE | ROLES:
                continue
            for node in ast.walk(fn):
                if (isinstance(node, ast.Attribute)
                        and isinstance(node.value, ast.Name)
                        and node.value.id == "curses"
                        and (node.attr.startswith("A_") or node.attr == "color_pair")):
                    offenders.append(f"{cls}.{fn.name} line {node.lineno}: "
                                     f"curses.{node.attr}")
        self.assertEqual(offenders, [],
                         "ask for a role -- heading, content, supporting, "
                         "interactive, selected, consequence")

    def test_the_palette_is_private_and_reached_only_through_roles(self):
        offenders = []
        for cls, fn in functions():
            if fn.name in PALETTE | ROLES:
                continue
            for node in ast.walk(fn):
                if isinstance(node, ast.Attribute) and node.attr == "_roles":
                    offenders.append(f"{cls}.{fn.name} line {node.lineno}: "
                                     f"{node.attr}")
        self.assertEqual(offenders, [], "the palette is reached through a role")

    @needs_curses
    def test_the_old_public_names_are_gone(self):
        """They were the way a caller used to pick a colour for itself."""
        for name in ("ACCENT", "RED", "YELLOW", "GREEN", "DIM"):
            self.assertFalse(hasattr(andy.Tui, name), name)

    @needs_curses
    def test_every_role_exists_and_returns_an_attribute(self):
        screen = type("S", (), {"getmaxyx": lambda self: (24, 80)})()
        tui = andy.Tui(screen, andy.Model(), None, use_mouse=False)
        tui.styles()
        for role in sorted(ROLES - {"consequence", "tint", "lift"}):
            self.assertIsInstance(getattr(tui, role)(), int, role)
        self.assertIsInstance(tui.consequence(andy.SAFE), int)
        self.assertIsInstance(tui.tint(andy.SAFE), int)
        for role in andy.ROLE_NAMES:
            self.assertIsInstance(tui.lift(role), int, f"lift({role})")


class OneMeaningPerChannel(unittest.TestCase):
    """Rule: hue is consequence or interaction. Never data, never magnitude."""

    @needs_curses
    def setUp(self):
        screen = type("S", (), {"getmaxyx": lambda self: (24, 80)})()
        self.tui = andy.Tui(screen, andy.Model(), None, use_mouse=False)
        self.tui.styles()

    def test_the_warm_scale_is_reachable_only_through_consequence(self):
        # Without colour every hue collapses to plain text, which is correct:
        # the rating is carried by its character and colour is only emphasis.
        if not self.tui.colour:
            self.skipTest("this terminal has no colour to overload")
        warm = {self.tui.consequence(r) for r in (andy.SAFE, andy.REBUILD,
                                                  andy.REVIEW)}
        for role in ("heading", "content", "interactive", "selected"):
            self.assertNotIn(getattr(self.tui, role)(), warm, role)

    def test_each_rating_is_its_own_colour(self):
        seen = [self.tui.consequence(r)
                for r in (andy.SAFE, andy.REBUILD, andy.REVIEW)]
        if self.tui.colour:
            self.assertEqual(len(set(seen)), 3, "two ratings share a colour")

    def test_reverse_is_the_cursor_and_nothing_else(self):
        for role in ("heading", "content", "supporting"):
            self.assertNotEqual(getattr(self.tui, role)(), self.tui.selected(), role)

    def test_magnitude_is_never_coloured(self):
        """The figure states it and the bar shows it. A third telling would
        spend the channel consequence needs."""
        self.assertFalse(hasattr(self.tui, "magnitude"))
        self.assertFalse(hasattr(andy.Ink(True), "magnitude"))
        self.assertNotIn("magnitude(", source().split("# The design language")[0])


class ThePlainTextHalfAgrees(unittest.TestCase):
    """Rule: the reports speak the same language as the browser. The delta
    report was colouring growth red and shrinkage green -- a fourth meaning for
    the warm scale, and one that said a 4G jump in something you can delete
    freely was as alarming as one in something you cannot."""

    def function_source(self, name):
        tree = ast.parse(source())
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == name)
        return ast.get_source_segment(source(), fn)

    def test_change_is_carried_by_the_sign_not_the_hue(self):
        body = self.function_source("print_delta")
        for hue in ("ink.safe(", "ink.rebuild(", "ink.review("):
            self.assertNotIn(hue, body, f"{hue} in print_delta means direction again")

    def test_a_change_is_coloured_by_what_removing_it_would_cost(self):
        self.assertIn("safety_colour", self.function_source("print_delta"))

    def test_magnitude_is_not_coloured_in_the_reports_either(self):
        for name in ("print_report", "print_tree", "print_delta"):
            self.assertNotIn("magnitude", self.function_source(name), name)

    def test_the_accent_is_not_spent_on_data(self):
        """Cyan means something you can press. The report drew its category
        bars in it, which made the loudest colour on the page mean nothing."""
        for name in ("print_report", "print_tree", "print_delta", "print_commands"):
            self.assertNotIn("ink.accent", self.function_source(name), name)

    def test_every_bar_sits_in_a_track(self):
        for name in ("print_report",):
            body = self.function_source(name)
            self.assertIn("bar_parts", body, f"{name} draws a bar with no track")

    def test_plenty_of_free_space_does_not_borrow_the_ratings_green(self):
        self.assertNotIn("else ink.safe", self.function_source("print_report"))


class TwoFormsForALabelAndAValue(unittest.TestCase):
    """Rule: a fact is a field, something you can press is a hint. There is no
    third way, and there used to be four."""

    @needs_curses
    def render(self, height=24, width=90):
        from test_tui import FakeScreen, sample_model, draw
        screen = FakeScreen(height, width)
        tui = andy.Tui(screen, sample_model(), None, use_mouse=False)
        tui.styles()
        tui.build_rows()
        draw(tui)
        return tui, screen

    def test_a_field_puts_its_value_in_the_same_column_every_time(self):
        tui, screen = self.render()
        starts = {x for y, x, text in screen.written
                  if text and x == 1 + tui.GUTTER}
        self.assertTrue(starts, "no field values were drawn")

    def test_field_keys_are_right_aligned_against_the_gutter(self):
        tui, screen = self.render()
        keys = [(y, x, text) for y, x, text in screen.written
                if x == 1 and text.strip() in ("volume", "where", "what",
                                               "reclaim", "holds")]
        for y, x, text in keys:
            self.assertEqual(len(text), tui.GUTTER - 1,
                             f"{text!r} is not padded to the gutter")

    def test_the_header_and_the_detail_pane_share_one_gutter(self):
        tui, screen = self.render()
        columns = {x for y, x, text in screen.written
                   if text.strip() in ("volume", "where", "what", "reclaim")}
        self.assertLessEqual(len(columns), 1,
                             "two label-and-value styles are back")


class PaneGeometry(unittest.TestCase):
    """Rule: a rule separates panes. One per boundary, never decoration."""

    @needs_curses
    def rules_at(self, height=24, width=90, detail=True):
        from test_tui import FakeScreen, sample_model, draw
        screen = FakeScreen(height, width)
        tui = andy.Tui(screen, sample_model(), None, use_mouse=False)
        tui.styles()
        tui.detail = detail
        tui.build_rows()
        draw(tui)
        return sorted({y for y, x, text in screen.written
                       if text.startswith(andy.RULE * 4)})

    def test_the_header_is_three_lines(self):
        """Title, the two facts, the rule that ends it. It was five, two of
        them rules with nothing between them needing separation."""
        self.assertEqual(self.rules_at()[0], 2)

    def test_there_are_exactly_two_rules_with_a_detail_pane(self):
        self.assertEqual(len(self.rules_at(detail=True)), 2)

    def test_there_is_one_rule_without_a_detail_pane(self):
        self.assertEqual(len(self.rules_at(detail=False)), 1)

    def test_no_two_rules_sit_within_three_lines_of_each_other(self):
        rows = self.rules_at()
        for a, b in zip(rows, rows[1:]):
            self.assertGreater(b - a, 3, f"rules at {a} and {b} are decoration")


class OneRowSkeleton(unittest.TestCase):
    """Rule: state . name . context . consequence . quantity . proportion,
    in that order, in every list."""

    @needs_curses
    def test_the_columns_run_in_the_stated_order(self):
        from test_tui import FakeScreen, sample_model, draw
        screen = FakeScreen(24, 110)
        tui = andy.Tui(screen, sample_model(), None, use_mouse=False)
        tui.styles()
        tui.set_expanded(tui.m.categories, True)
        tui.build_rows()
        draw(tui)
        row = next(y for y in range(screen.height)
                   if "pnpm store" in screen.row(y))
        pieces = sorted(((x, text) for y, x, text in screen.written if y == row),
                        key=lambda pair: pair[0])
        columns = {}
        for x, text in pieces:
            if "pnpm store" in text:
                columns["name"] = x
            elif text.strip() == andy.MARK[andy.SAFE]:
                columns["consequence"] = x
            elif text.strip().endswith(("G", "M", "K")):
                columns["quantity"] = x
            elif text.strip(" ") and set(text.strip()) <= set(andy.FULL_CELL +
                                                              andy.PARTIAL_CELLS):
                columns["proportion"] = x
        for earlier, later in (("name", "consequence"), ("consequence", "quantity"),
                               ("quantity", "proportion")):
            self.assertIn(earlier, columns)
            self.assertIn(later, columns)
            self.assertLess(columns[earlier], columns[later],
                            f"{earlier} should come before {later}")


class WrittenDown(unittest.TestCase):
    """Rule: the language lives where the drawing code is, and in the README.
    One that lives only in a commit message is not one."""

    def test_the_rules_are_stated_above_the_drawing_code(self):
        text = source()
        self.assertIn("# The design language", text)
        block = text.split("# The design language")[1][:2000]
        for channel in ("position", "length", "weight", "hue", "reverse", "glyph"):
            self.assertIn(channel, block, f"{channel} is not given a job")

    def test_the_readme_shows_the_reader_the_same_rules(self):
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(here, "README.md"), encoding="utf-8") as fh:
            readme = fh.read()
        self.assertIn("design language", readme.lower())


if __name__ == "__main__":
    unittest.main()
