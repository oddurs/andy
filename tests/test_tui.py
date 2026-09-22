"""The interactive browser, driven without a person.

Two layers. Most of the browser is arithmetic over a Model -- which rows are
visible, what the filter selects, where the cursor lands, what a click at (x, y)
resolves to -- and none of that needs a terminal; it needs a screen object that
records what it was told. The rest genuinely needs a pty, and gets one.

Everything here skips cleanly where curses is missing, because cairn 0011 made
that a supported way to run andy.
"""

import os
import re
import select
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

from andymod import andy, ANDY

Node = andy.Node
MB = 2 ** 20

needs_curses = unittest.skipIf(andy.curses is None, "this Python has no curses")


class FakeScreen:
    """Enough curses window for the drawing code to talk to.

    It records rather than renders, so a test can ask what ended up on a row.
    """

    def __init__(self, height=40, width=120):
        self.height, self.width = height, width
        self.written: list[tuple[int, int, str]] = []
        self.keys: list[int] = []

    # -- what Tui calls --------------------------------------------------- #
    def getmaxyx(self):
        return self.height, self.width

    def erase(self):
        self.written.clear()

    def addnstr(self, y, x, text, n, attr=0):
        self.written.append((y, x, text[:n]))

    def noutrefresh(self):
        pass

    def nodelay(self, flag):
        pass

    def keypad(self, flag):
        pass

    def getch(self):
        return self.keys.pop(0) if self.keys else -1

    # -- what a test asks ------------------------------------------------- #
    def row(self, y):
        return " ".join(text for ry, _, text in self.written if ry == y)

    def text(self):
        return "\n".join(self.row(y) for y in range(self.height))


def sample_model(project_count=6):
    """A model with a category, a group, itemised children and a blocked row."""
    m = andy.Model()
    m.disk = (500 * 2 ** 30, 300 * 2 ** 30, 200 * 2 ** 30)
    m.finished = True

    caches = m.category(andy.PACKAGES)
    caches.children.append(Node(label="pnpm store", path="/h/pnpm",
                                measured=3 * 2 ** 30, cmd="pnpm store prune",
                                safety=andy.SAFE,
                                note="Content-addressed store."))
    caches.children.append(Node(label="tiny", path="/h/tiny", measured=2 * MB))
    caches.children.append(Node(label="stuck", path="/h/stuck", measured=None,
                                blocked=True))

    tools = m.category(andy.TOOLCHAINS)
    rustup = Node(label="rustup toolchains", path="/h/rustup", safety=andy.REVIEW,
                  measured=8 * 2 ** 30, cmd="rustup toolchain uninstall <name>")
    for name, size in (("stable", 4 * 2 ** 30), ("nightly", 3 * 2 ** 30)):
        rustup.children.append(Node(label=name, path=f"/h/rustup/{name}",
                                    measured=size, detail=True))
    tools.children.append(rustup)

    projects = m.category(andy.PROJECTS)
    group = Node(label="node_modules", kind="node_modules")
    for i in range(project_count):
        group.children.append(Node(label=f"proj{i}/node_modules",
                                   path=f"/r/proj{i}/node_modules",
                                   cmd="rm -rf <path>", safety=andy.REBUILD,
                                   measured=(i + 1) * 200 * MB))
    projects.children.append(group)

    m.recompute()
    return m


def draw(tui):
    """Draw once. doupdate() pushes to a real screen and there is not one."""
    with mock.patch.object(andy.curses, "doupdate"):
        tui.draw()


def make_tui(model=None, height=40, width=120, **attrs):
    screen = FakeScreen(height, width)
    tui = andy.Tui(screen, model or sample_model(), mock.Mock(), use_mouse=False)
    tui.styles()          # attributes and mouse masks; no terminal involved
    for name, value in attrs.items():
        setattr(tui, name, value)
    tui.build_rows()
    return tui, screen


@needs_curses
class Rows(unittest.TestCase):
    def test_categories_are_the_top_level(self):
        tui, _ = make_tui()
        self.assertEqual([n.label for n, depth, _ in tui.rows if depth == 0],
                         [andy.TOOLCHAINS, andy.PROJECTS, andy.PACKAGES])

    def test_a_collapsed_category_hides_its_children(self):
        tui, _ = make_tui()
        self.assertNotIn("pnpm store", [n.label for n, _, _ in tui.rows])

    def test_expanding_reveals_them(self):
        tui, _ = make_tui()
        tui.m.category(andy.PACKAGES).expanded = True
        tui.build_rows()
        self.assertIn("pnpm store", [n.label for n, _, _ in tui.rows])

    def test_small_rows_are_hidden_until_asked_for(self):
        tui, _ = make_tui()
        tui.m.category(andy.PACKAGES).expanded = True
        tui.build_rows()
        self.assertNotIn("tiny", [n.label for n, _, _ in tui.rows])
        tui.show_small = True
        tui.build_rows()
        self.assertIn("tiny", [n.label for n, _, _ in tui.rows])

    def test_depth_tracks_nesting(self):
        tui, _ = make_tui()
        tools = tui.m.category(andy.TOOLCHAINS)
        tools.expanded = True
        tools.children[0].expanded = True
        tui.build_rows()
        depths = {n.label: d for n, d, _ in tui.rows}
        self.assertEqual(depths[andy.TOOLCHAINS], 0)
        self.assertEqual(depths["rustup toolchains"], 1)
        self.assertEqual(depths["stable"], 2)

    def test_expand_all_and_collapse_all(self):
        tui, _ = make_tui()
        tui.set_expanded(tui.m.categories, True)
        tui.build_rows()
        self.assertIn("stable", [n.label for n, _, _ in tui.rows])
        tui.set_expanded(tui.m.categories, False)
        tui.build_rows()
        self.assertEqual([n.label for n, d, _ in tui.rows if d > 0], [])


@needs_curses
class Filtering(unittest.TestCase):
    def test_a_filter_matches_labels(self):
        tui, _ = make_tui(filter="rustup")
        labels = [n.label for n, _, _ in tui.rows]
        self.assertIn("rustup toolchains", labels)
        self.assertNotIn("pnpm store", labels)

    def test_a_filter_matches_paths(self):
        tui, _ = make_tui(filter="/h/pnpm")
        self.assertIn("pnpm store", [n.label for n, _, _ in tui.rows])

    def test_a_filter_keeps_the_parents_of_a_match(self):
        """Otherwise a match would have nothing to hang from."""
        tui, _ = make_tui(filter="stable")
        labels = [n.label for n, _, _ in tui.rows]
        self.assertIn(andy.TOOLCHAINS, labels)
        self.assertIn("rustup toolchains", labels)
        self.assertIn("stable", labels)

    def test_a_filter_shows_small_rows_that_match(self):
        tui, _ = make_tui(filter="tiny")
        self.assertIn("tiny", [n.label for n, _, _ in tui.rows])

    def test_a_filter_matching_nothing_leaves_no_rows(self):
        tui, _ = make_tui(filter="zzzz-nothing")
        self.assertEqual(tui.rows, [])

    def test_the_filter_is_case_insensitive(self):
        self.assertTrue(make_tui(filter="RUSTUP")[0].rows)


@needs_curses
class Sorting(unittest.TestCase):
    def test_size_order_by_default(self):
        tui, _ = make_tui()
        tui.set_expanded(tui.m.categories, True)
        tui.build_rows()
        group = [n.size for n, d, _ in tui.rows if d == 2 and "proj" in n.label]
        self.assertEqual(group, sorted(group, reverse=True))

    def test_name_order_when_asked(self):
        tui, _ = make_tui(sort_by_name=True)
        tui.set_expanded(tui.m.categories, True)
        tui.build_rows()
        labels = [n.label for n, d, _ in tui.rows if d == 2 and "proj" in n.label]
        self.assertEqual(labels, sorted(labels))


@needs_curses
class Cursor(unittest.TestCase):
    def test_movement_is_clamped_at_both_ends(self):
        tui, _ = make_tui()
        tui.move(-5)
        self.assertEqual(tui.cursor, 0)
        tui.move(10_000)
        self.assertEqual(tui.cursor, len(tui.rows) - 1)

    def test_the_view_follows_the_cursor(self):
        tui, screen = make_tui(height=12)
        tui.set_expanded(tui.m.categories, True)
        tui.build_rows()
        tui.cursor = len(tui.rows) - 1
        draw(tui)
        self.assertGreater(tui.top, 0, "the view did not scroll to the cursor")
        self.assertLessEqual(tui.top, tui.cursor)

    def test_scrolling_does_not_run_past_the_end(self):
        tui, _ = make_tui(height=12)
        tui.set_expanded(tui.m.categories, True)
        tui.build_rows()
        draw(tui)
        tui.scroll(10_000)
        draw(tui)
        self.assertLessEqual(tui.top, max(0, len(tui.rows) - 1))

    def test_current_is_the_row_under_the_cursor(self):
        tui, _ = make_tui()
        tui.cursor = 1
        self.assertIs(tui.current(), tui.rows[1][0])

    def test_current_is_none_with_no_rows(self):
        tui, _ = make_tui(filter="zzzz-nothing")
        self.assertIsNone(tui.current())


@needs_curses
class Drawing(unittest.TestCase):
    def test_a_full_draw_puts_the_headline_figures_up(self):
        tui, screen = make_tui()
        draw(tui)
        text = screen.text()
        self.assertIn("andy", text)
        self.assertIn("mapped", text)
        self.assertIn(andy.TOOLCHAINS.upper(), text.upper())

    def test_every_size_survives(self):
        for height, width in ((6, 30), (12, 60), (24, 80), (60, 200)):
            tui, _ = make_tui(height=height, width=width)
            tui.set_expanded(tui.m.categories, True)
            tui.build_rows()
            draw(tui)          # must not raise at any size

    def test_every_width_down_to_one_column(self):
        """cairn 0024: the footer dropped hints until it fell off the end."""
        for width in range(1, 60):
            tui, _ = make_tui(height=24, width=width)
            draw(tui)

    def test_every_height_down_to_one_row(self):
        for height in range(1, 24):
            tui, _ = make_tui(height=height, width=80)
            draw(tui)

    def test_the_help_overlay_draws(self):
        tui, screen = make_tui()
        tui.help = True
        draw(tui)
        self.assertIn("keys", screen.text())

    def test_the_detail_pane_describes_the_selection(self):
        tui, screen = make_tui()
        tui.m.category(andy.PACKAGES).expanded = True
        tui.build_rows()
        tui.cursor = next(i for i, (n, _, _) in enumerate(tui.rows)
                          if n.label == "pnpm store")
        draw(tui)
        text = screen.text()
        self.assertIn("pnpm store prune", text)
        self.assertIn("Content-addressed", text)

    def test_an_unfinished_measurement_is_shown_and_marked(self):
        """cairn 0025: the browser used to drop exactly these rows."""
        tui, screen = make_tui()
        tui.m.category(andy.PACKAGES).expanded = True
        tui.build_rows()
        self.assertIn("stuck", [n.label for n, _, _ in tui.rows])
        tui.cursor = next(i for i, (n, _, _) in enumerate(tui.rows)
                          if n.label == "stuck")
        draw(tui)
        text = screen.text()
        self.assertIn("incomplete", text)
        self.assertIn("?", text, "an unmeasured location was drawn as a number")

    def test_an_unfinished_measurement_still_obeys_the_filter(self):
        tui, _ = make_tui(filter="pnpm")
        self.assertNotIn("stuck", [n.label for n, _, _ in tui.rows])

    def test_a_model_with_nothing_in_it(self):
        tui, screen = make_tui(model=andy.Model(), height=24)
        draw(tui)
        self.assertIn("scanning", screen.text())


@needs_curses
class Zones(unittest.TestCase):
    """Mouse hit-testing: which row or control a click at (x, y) resolves to."""

    def test_a_click_on_a_row_selects_it(self):
        tui, _ = make_tui()
        draw(tui)
        row_zones = [(y, payload) for y, x0, x1, kind, payload in tui.zones
                     if kind == "row"]
        self.assertTrue(row_zones)
        y, idx = row_zones[2]
        kind, payload = tui.zone_at(y, 40)
        self.assertEqual((kind, payload), ("row", idx))

    def test_a_narrow_target_wins_over_the_wide_one_beneath_it(self):
        """The toggle arrow sits on top of the row that spans the width."""
        tui, _ = make_tui()
        draw(tui)
        toggles = [(y, x0, payload) for y, x0, x1, kind, payload in tui.zones
                   if kind == "toggle"]
        self.assertTrue(toggles, "no expander was registered")
        y, x0, idx = toggles[0]
        self.assertEqual(tui.zone_at(y, x0), ("toggle", idx))

    def test_a_click_outside_every_zone_resolves_to_nothing(self):
        tui, _ = make_tui()
        draw(tui)
        self.assertEqual(tui.zone_at(-1, 0), (None, None))

    def test_toggling_a_branch_opens_and_closes_it(self):
        tui, _ = make_tui()
        node = tui.rows[0][0]
        self.assertFalse(node.expanded)
        tui.toggle(0)
        self.assertTrue(node.expanded)
        tui.toggle(0)
        self.assertFalse(node.expanded)


@needs_curses
class Bars(unittest.TestCase):
    """cairn 0034. The bar was drawn against the largest item at each level, so
    a 637M row and a 7.5G row both drew full, four lines apart."""

    def whole_for(self, tui, label):
        return next(whole for n, _, whole in tui.rows if n.label == label)

    def test_a_category_is_drawn_against_everything_mapped(self):
        tui, _ = make_tui()
        for node, depth, whole in tui.rows:
            if depth == 0:
                self.assertEqual(whole, tui.m.total)

    def test_everything_below_is_drawn_against_its_category(self):
        tui, _ = make_tui()
        tui.set_expanded(tui.m.categories, True)
        tui.build_rows()
        projects = tui.m.category(andy.PROJECTS)
        for node, depth, whole in tui.rows:
            if depth > 0 and any(node is n for n in tui.m.walk([projects])):
                self.assertEqual(whole, projects.size, node.label)

    def test_the_denominator_does_not_reset_with_depth(self):
        """The bug: every level restarting made depth change the meaning."""
        tui, _ = make_tui()
        tui.set_expanded(tui.m.categories, True)
        tui.build_rows()
        group = self.whole_for(tui, "node_modules")
        member = self.whole_for(tui, "proj5/node_modules")
        self.assertEqual(group, member)

    def test_two_rows_of_the_same_size_draw_the_same_bar(self):
        m = sample_model()
        cat = m.category(andy.PACKAGES)
        group = Node(label="group", kind="g")
        group.children.append(Node(label="deep", path="/h/deep", measured=2 ** 30))
        cat.children.append(group)
        cat.children.append(Node(label="shallow", path="/h/shallow",
                                 measured=2 ** 30))
        m.recompute()
        tui, _ = make_tui(model=m)
        tui.set_expanded(m.categories, True)
        tui.build_rows()
        bars = {}
        for node, _, whole in tui.rows:
            if node.label in ("deep", "shallow"):
                bars[node.label] = andy.bar(node.size / whole, 20)
        self.assertEqual(bars["deep"], bars["shallow"],
                         "the same size drew differently at different depths")

    def test_a_full_bar_means_it_is_the_whole_category(self):
        m = andy.Model()
        cat = m.category(andy.PACKAGES)
        cat.children.append(Node(label="only", path="/h/o", measured=2 ** 30))
        m.recompute()
        tui, _ = make_tui(model=m)
        tui.set_expanded(m.categories, True)
        tui.build_rows()
        node, _, whole = next(r for r in tui.rows if r[0].label == "only")
        self.assertEqual(andy.bar(node.size / whole, 10), andy.FULL_CELL * 10)


@needs_curses
class PathColumn(unittest.TestCase):
    """cairn 0035. It printed `rsst/target   ~/Code/rsst/target`."""

    def test_a_label_that_is_the_tail_leaves_only_the_prefix(self):
        node = Node(label="rsst/target", path="/r/rsst/target", measured=1)
        self.assertEqual(andy.Tui.path_text(node), "/r")

    def test_a_catalog_location_still_shows_its_whole_path(self):
        node = Node(label="pnpm store", path="/h/Library/pnpm/store", measured=1)
        self.assertEqual(andy.Tui.path_text(node), "/h/Library/pnpm/store")

    def test_a_breakdown_has_nothing_left_to_add(self):
        node = Node(label="stable", path="/h/rustup/stable", detail=True, measured=1)
        self.assertEqual(andy.Tui.path_text(node), "")

    def test_a_row_with_no_path(self):
        self.assertEqual(andy.Tui.path_text(Node(label="node_modules")), "")

    def test_a_path_that_is_entirely_the_label(self):
        node = Node(label="Code/target", path="/Code/target", measured=1)
        self.assertEqual(andy.Tui.path_text(node), os.sep)

    def test_the_column_is_only_as_wide_as_what_it_holds(self):
        tui, screen = make_tui(width=140)
        tui.set_expanded(tui.m.categories, True)
        tui.build_rows()
        draw(tui)
        rows = [screen.row(y) for y in range(screen.height)]
        line = next(r for r in rows if "proj5/node_modules" in r)
        self.assertIn("/r", line)
        self.assertNotIn("/r/proj5/node_modules", line,
                         "the path column restated the label")


@needs_curses
class SafetyColumn(unittest.TestCase):
    """cairn 0036. The rating reached the summary in 1.4 and not the browser."""

    def test_each_rating_has_its_own_character(self):
        for rating, mark in andy.MARK.items():
            node = Node(label="x", path="/x", measured=1, safety=rating)
            self.assertEqual(andy.Tui.safety_text(node), mark)

    def test_the_marks_match_the_report(self):
        self.assertEqual(set(andy.MARK.values()), {"s", "r", "!"})

    def test_a_row_that_is_not_a_place_shows_nothing(self):
        self.assertEqual(andy.Tui.safety_text(Node(label="node_modules")), " ")

    def test_it_reaches_the_screen(self):
        tui, screen = make_tui()
        tui.set_expanded(tui.m.categories, True)
        tui.build_rows()
        draw(tui)
        line = next(screen.row(y) for y in range(screen.height)
                    if "pnpm store" in screen.row(y))
        self.assertIn("s", line)

    def test_it_is_a_character_and_not_only_a_colour(self):
        """A colour-only signal says nothing on a monochrome terminal."""
        tui, screen = make_tui()
        tui.colour = False
        tui.set_expanded(tui.m.categories, True)
        tui.build_rows()
        draw(tui)
        self.assertRegex(screen.text(), r"[sr!]")


@needs_curses
class Marking(unittest.TestCase):
    """cairn 0031. Reclaiming a disk is four or five directories across three
    categories, and the browser could only hand over one at a time."""

    def rows(self, tui):
        return [n.label for n, _, _ in tui.rows]

    def open_all(self, tui):
        tui.set_expanded(tui.m.categories, True)
        tui.build_rows()
        return tui

    def mark(self, tui, label):
        idx = next(i for i, (n, _, _) in enumerate(tui.rows) if n.label == label)
        tui.cursor = idx
        tui.handle(ord(" "))
        tui.build_rows()

    def test_space_marks_and_unmarks(self):
        tui, _ = make_tui()
        self.open_all(tui)
        self.mark(tui, "pnpm store")
        self.assertEqual(len(tui.marked), 1)
        self.mark(tui, "pnpm store")
        self.assertEqual(tui.marked, set())

    def test_space_no_longer_expands(self):
        """It opened branches once; enter, tab and right still do."""
        tui, _ = make_tui()
        node = tui.rows[0][0]
        tui.cursor = 0
        tui.handle(ord(" "))
        self.assertFalse(node.expanded, "space both marked and expanded")
        tui.handle(ord("\n"))
        self.assertTrue(node.expanded)

    def test_a_mark_is_visible(self):
        tui, screen = make_tui()
        self.open_all(tui)
        self.mark(tui, "pnpm store")
        draw(tui)
        line = next(screen.row(y) for y in range(screen.height)
                    if "pnpm store" in screen.row(y))
        self.assertIn("*", line)

    def test_marks_survive_filtering_and_sorting(self):
        tui, _ = make_tui()
        self.open_all(tui)
        self.mark(tui, "pnpm store")
        tui.filter = "rustup"
        tui.build_rows()
        self.assertNotIn("pnpm store", self.rows(tui))
        tui.filter = ""
        tui.sort_by_name = True
        tui.build_rows()
        self.assertEqual(len(tui.marked), 1)
        self.assertEqual([n.label for n in tui.marked_nodes()], ["pnpm store"])

    def test_marks_are_remembered_by_path_so_a_rescan_keeps_them(self):
        tui, _ = make_tui()
        self.open_all(tui)
        self.mark(tui, "pnpm store")
        fresh = sample_model()          # as a rescan rebuilds it
        tui.m = fresh
        tui.build_rows()
        self.assertEqual([n.label for n in tui.marked_nodes()], ["pnpm store"])

    def test_marking_confirms_with_the_size_so_far(self):
        tui, screen = make_tui()
        self.open_all(tui)
        self.mark(tui, "pnpm store")
        draw(tui)
        self.assertIn("marked pnpm store", screen.text())
        self.assertIn("3.0G in 1", screen.text())

    def test_the_footer_shows_what_is_marked_once_the_toast_clears(self):
        tui, screen = make_tui()
        self.open_all(tui)
        self.mark(tui, "pnpm store")
        tui.message_until = 0           # as it would be a couple of seconds on
        draw(tui)
        text = screen.text()
        self.assertIn("copy 1", text)
        self.assertIn("3.0G", text)

    def test_marking_a_group_means_its_members(self):
        tui, _ = make_tui()
        self.open_all(tui)
        self.mark(tui, "node_modules")
        rows = andy.selected_rows(tui.m, tui.marked_nodes())
        labels = [n.label for _, n, _ in rows]
        self.assertTrue(labels, "a group marked nothing")
        self.assertNotIn("node_modules", labels)
        self.assertTrue(all("proj" in label for label in labels), labels)

    def test_a_group_and_a_child_are_not_counted_twice(self):
        tui, _ = make_tui()
        self.open_all(tui)
        self.mark(tui, "node_modules")
        group = next(n for n, _, _ in tui.rows if n.label == "node_modules")
        self.mark(tui, group.children[0].label)
        self.assertEqual(tui.marked_size(), group.size)

    def test_copying_builds_one_script(self):
        tui, _ = make_tui()
        self.open_all(tui)
        self.mark(tui, "pnpm store")
        self.mark(tui, "rustup toolchains")
        with mock.patch.object(andy, "clip", return_value=True) as clip:
            tui.handle(ord("C"))
        text = clip.call_args[0][0]
        self.assertTrue(text.startswith("#!/bin/sh"))
        self.assertIn("pnpm store prune", text)
        self.assertIn("rustup toolchain uninstall stable", text)
        self.assertIn("would reclaim about", text)
        for line in text.splitlines():
            self.assertTrue(line == "" or line.startswith("#"), line)
        self.assertIn("copied", tui.message)

    def test_copying_nothing_says_so(self):
        tui, _ = make_tui()
        with mock.patch.object(andy, "clip") as clip:
            tui.handle(ord("C"))
        clip.assert_not_called()
        self.assertIn("nothing marked", tui.message)

    def test_marking_something_with_no_command(self):
        tui, _ = make_tui()
        self.open_all(tui)
        self.mark(tui, "stuck")             # blocked, no command
        with mock.patch.object(andy, "clip") as clip:
            tui.handle(ord("C"))
        clip.assert_not_called()
        self.assertIn("no", tui.message)

    def test_the_browser_copies_a_filled_command_not_a_template(self):
        """cairn 0029 reached --commands; the clipboard is the same consumer."""
        tui, _ = make_tui()
        self.open_all(tui)
        node = next(n for n, _, _ in tui.rows if n.label.startswith("proj0"))
        tui.cursor = next(i for i, (n, _, _) in enumerate(tui.rows) if n is node)
        node.cmd = "rm -rf <path>"
        with mock.patch.object(andy, "clip", return_value=True) as clip:
            tui.handle(ord("c"))
        self.assertEqual(clip.call_args[0][0], f"rm -rf {node.path}")


@needs_curses
class Map(unittest.TestCase):
    def test_cells_are_laid_out_inside_the_canvas(self):
        tui, screen = make_tui()
        tui.view = "map"
        draw(tui)
        self.assertTrue(tui.map_cells, "the map drew nothing")
        for _, x, y, w, h in tui.map_cells:
            self.assertGreaterEqual(x, 0)
            self.assertLessEqual(x + w, screen.width)

    def test_drilling_in_and_backing_out(self):
        tui, _ = make_tui()
        tui.view = "map"
        draw(tui)
        top = tui.map_level()
        tui.map_sel = 0
        tui.map_drill()
        self.assertTrue(tui.map_stack, "drilling in did not descend")
        self.assertNotEqual(tui.map_level(), top)
        tui.map_up()
        self.assertEqual(tui.map_level(), top)

    def test_backing_out_from_the_top_says_so(self):
        tui, _ = make_tui()
        tui.view = "map"
        tui.map_up()
        self.assertIn("already at the top", tui.message)

    def test_a_canvas_too_small_for_cells(self):
        tui, _ = make_tui(height=8, width=24)
        tui.view = "map"
        draw(tui)          # must not raise; may legitimately draw nothing


@needs_curses
class Keys(unittest.TestCase):
    def press(self, tui, *keys):
        """As the real loop does it: handle the key, then redraw."""
        alive = True
        for key in keys:
            alive = tui.handle(ord(key) if isinstance(key, str) else key)
            tui.build_rows()
        return alive

    def test_q_quits(self):
        tui, _ = make_tui()
        self.assertFalse(self.press(tui, "q"))

    def test_movement_keys(self):
        tui, _ = make_tui()
        self.press(tui, "j", "j")
        self.assertEqual(tui.cursor, 2)
        self.press(tui, "k")
        self.assertEqual(tui.cursor, 1)
        self.press(tui, "G")
        self.assertEqual(tui.cursor, len(tui.rows) - 1)
        self.press(tui, "g")
        self.assertEqual(tui.cursor, 0)

    def test_expanding_with_the_keyboard(self):
        tui, _ = make_tui()
        self.press(tui, "\n")
        self.assertTrue(tui.rows[0][0].expanded)

    def test_e_expands_everything_and_E_collapses_it(self):
        tui, _ = make_tui()
        self.press(tui, "e")
        self.assertIn("stable", [n.label for n, _, _ in tui.rows])
        self.press(tui, "E")
        self.assertEqual([n.label for n, d, _ in tui.rows if d > 0], [])

    def test_typing_a_filter_and_clearing_it(self):
        tui, _ = make_tui()
        self.press(tui, "/")
        self.assertTrue(tui.typing)
        self.press(tui, "t", "i", "n", "y")
        self.assertEqual(tui.filter, "tiny")
        self.press(tui, 27)                       # esc
        self.assertEqual(tui.filter, "")

    def test_s_toggles_sorting_and_a_toggles_small_rows(self):
        tui, _ = make_tui()
        self.press(tui, "s")
        self.assertTrue(tui.sort_by_name)
        self.press(tui, "a")
        self.assertTrue(tui.show_small)

    def test_m_switches_to_the_map_and_back(self):
        tui, _ = make_tui()
        self.press(tui, "m")
        self.assertEqual(tui.view, "map")
        self.press(tui, "m")
        self.assertEqual(tui.view, "tree")

    def test_the_help_overlay_closes_on_any_key(self):
        tui, _ = make_tui()
        self.press(tui, "?")
        self.assertTrue(tui.help)
        self.press(tui, "j")
        self.assertFalse(tui.help)

    def test_copying_reports_what_happened(self):
        tui, _ = make_tui()
        tui.m.category(andy.PACKAGES).expanded = True
        tui.build_rows()
        tui.cursor = next(i for i, (n, _, _) in enumerate(tui.rows)
                          if n.label == "pnpm store")
        with mock.patch.object(andy, "clip", return_value=True) as clip:
            self.press(tui, "c")
        clip.assert_called_once_with("pnpm store prune")
        self.assertIn("copied", tui.message)

    def test_a_failed_copy_does_not_claim_success(self):
        tui, _ = make_tui()
        tui.m.category(andy.PACKAGES).expanded = True
        tui.build_rows()
        tui.cursor = next(i for i, (n, _, _) in enumerate(tui.rows)
                          if n.label == "pnpm store")
        with mock.patch.object(andy, "clip", return_value=False):
            self.press(tui, "c")
        self.assertNotIn("copied", tui.message)

    def test_an_unknown_key_is_ignored_rather_than_fatal(self):
        tui, _ = make_tui()
        self.assertTrue(self.press(tui, "Z"))


class RealTerminal(unittest.TestCase):
    """The program in a pty: it starts, draws, takes keys and exits cleanly."""

    @classmethod
    def setUpClass(cls):
        if andy.curses is None:
            raise unittest.SkipTest("this Python has no curses")
        cls.dir = os.path.realpath(tempfile.mkdtemp(prefix="andy-tui-"))
        cls.home = os.path.join(cls.dir, "home")
        os.makedirs(cls.home)
        tree = os.path.join(cls.dir, "work")
        for i in range(3):
            path = os.path.join(tree, f"p{i}", "node_modules", "b.bin")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as fh:
                fh.write(b"\0" * ((i + 1) * 4 * MB))
            open(os.path.join(tree, f"p{i}", "package.json"), "w").close()
        cls.tree = tree

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir, ignore_errors=True)

    def drive(self, keys, timeout=45):
        """Run `andy -i` in a pty, send `keys`, return (exit code, screen)."""
        import pty
        pid, fd = pty.fork()
        if pid == 0:                                    # pragma: no cover
            os.environ.update(TERM="xterm-256color", HOME=self.home, LINES="40",
                              COLUMNS="140", NO_COLOR="1",
                              XDG_CACHE_HOME=os.path.join(self.home, ".cache"),
                              DOCKER_HOST="unix:///nonexistent/andy.sock")
            os.execv(sys.executable, [sys.executable, ANDY, "-i", "--no-mouse",
                                      self.tree])
        out = b""
        deadline = time.time() + timeout
        sent = 0
        # Wait for the scan to report itself finished rather than guessing at a
        # sleep: the footer shows the elapsed time once it is done, and a fixed
        # delay long enough to be safe made this suite six times slower.
        ready_at = None
        while time.time() < deadline:
            ready, _, _ = select.select([fd], [], [], 0.2)
            if ready:
                try:
                    chunk = os.read(fd, 65536)
                except OSError:
                    break
                if not chunk:
                    break
                out += chunk
            if ready_at is None and b"locations" in out:
                ready_at = time.time()          # the scan has published a count
            if ready_at and time.time() > ready_at + 0.3 and sent < len(keys):
                os.write(fd, keys[sent].encode())
                sent += 1
                time.sleep(0.25)                # let it redraw before the next
                if sent == len(keys):
                    deadline = time.time() + 6
        try:
            _, status = os.waitpid(pid, 0)
            code = os.waitstatus_to_exitcode(status)
        except ChildProcessError:                       # pragma: no cover
            code = None
        screen = re.sub(r"\x1b\[[0-9;?]*[a-zA-Z]|\x1b[()][B0]|\r", "",
                        out.decode("utf-8", "replace"))
        return code, screen

    def assertClean(self, keys, timeout=45):
        code, screen = self.drive(keys, timeout=timeout)
        self.assertNotIn("Traceback", screen, screen[-800:])
        self.assertEqual(code, 0, f"keys {keys!r} exited {code}")
        return screen

    def test_it_starts_draws_and_quits(self):
        screen = self.assertClean("q")
        self.assertIn("andy", screen)

    def test_expanding_everything_then_quitting(self):
        self.assertClean("eq")

    def test_the_map_and_back(self):
        self.assertClean("mmq")

    def test_drilling_into_the_map(self):
        self.assertClean("m\nq")

    def test_the_help_overlay(self):
        self.assertClean("?jq")

    def test_filtering(self):
        self.assertClean("/node\x1bq")

    def test_the_detail_pane_and_sorting(self):
        self.assertClean("dsaq")

    def test_a_rescan(self):
        self.assertClean("rq", timeout=60)


if __name__ == "__main__":
    unittest.main()
