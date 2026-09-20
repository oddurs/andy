"""Every output format, against a model with known numbers.

The point is not the exact layout -- that is allowed to change -- but that each
format renders without raising at any terminal width, and that the numbers it
prints are the numbers in the model.
"""

import io
import json
import os
import unittest
from unittest import mock

from andymod import andy

Node = andy.Node


def sample_model():
    m = andy.Model()
    m.disk = (500 * 2 ** 30, 300 * 2 ** 30, 200 * 2 ** 30)
    m.roots = ["/r"]
    m.elapsed = 1.25

    caches = m.category(andy.PACKAGES)
    caches.children.append(Node(
        label="pnpm store", path="/h/pnpm", measured=3 * 2 ** 30,
        note="Content-addressed package store.", cmd="pnpm store prune",
        safety=andy.SAFE, kind=andy.PACKAGES))

    projects = m.category(andy.PROJECTS)
    group = Node(label="node_modules", kind="node_modules", safety=andy.REBUILD,
                 cmd="rm -rf node_modules", note="Dependency trees.")
    group.children.append(Node(label="app/node_modules", path="/r/app/node_modules",
                               measured=2 * 2 ** 30, kind="node_modules",
                               safety=andy.REBUILD))
    projects.children.append(group)

    containers = m.category(andy.CONTAINERS)
    vm = Node(label="OrbStack", path="/h/orb", measured=10 * 2 ** 30,
              safety=andy.REBUILD, kind=andy.CONTAINERS)
    live = Node(label="docker · live breakdown", informational=True, kind="docker")
    live.children.append(Node(label="images", measured=4 * 2 ** 30, size=4 * 2 ** 30,
                              informational=True, kind="docker"))
    containers.children += [vm, live]

    caches.children.append(Node(label="stuck", path="/h/stuck", measured=None,
                                blocked=True, kind=andy.PACKAGES))
    # counted for a while, then the budget expired: the figure is a floor
    caches.children.append(Node(label="slow vm", path="/h/slow", measured=2 ** 30,
                                blocked=True, partial=True, kind=andy.PACKAGES))

    m.recompute()
    return m


class Rendering(unittest.TestCase):
    def setUp(self):
        self.m = sample_model()

    def render(self, fn, *args):
        out = io.StringIO()
        fn(self.m, andy.Ink(False), *args, out=out)
        return out.getvalue()

    def test_the_model_adds_up(self):
        self.assertEqual(self.m.total, 16 * 2 ** 30,
                         "the informational docker rows must not be counted")

    def test_report_names_the_big_things(self):
        text = self.render(andy.print_report, 12)
        self.assertIn("pnpm store", text)
        self.assertIn("OrbStack", text)
        self.assertIn("16.0G", text)

    def test_report_flags_what_it_did_not_finish(self):
        text = self.render(andy.print_report, 12)
        self.assertIn("still counting when time ran out", text)
        self.assertIn("stuck", text)
        self.assertIn("nothing counted", text)

    def test_report_gives_a_floor_for_a_partial_measurement(self):
        text = self.render(andy.print_report, 12)
        self.assertIn("slow vm", text)
        self.assertIn("at least 1.0G so far", text)

    def test_report_with_no_largest_list(self):
        self.assertNotIn("largest items", self.render(andy.print_report, 0))

    def test_report_survives_an_empty_model(self):
        out = io.StringIO()
        andy.print_report(andy.Model(), andy.Ink(False), 12, out=out)
        self.assertIn("nothing found", out.getvalue())

    def test_every_format_survives_every_terminal_width(self):
        for width in (20, 40, 80, 200):
            with mock.patch.object(andy.shutil, "get_terminal_size",
                                   return_value=os.terminal_size((width, 24))):
                self.render(andy.print_report, 12)
                self.render(andy.print_tree, 0)
                self.render(andy.print_commands, 0)

    def test_tree_hides_what_is_below_the_floor(self):
        text = self.render(andy.print_tree, 5 * 2 ** 30)
        self.assertIn("OrbStack", text)
        self.assertNotIn("app/node_modules", text)

    def test_commands_is_a_shell_script_that_runs_nothing(self):
        text = self.render(andy.print_commands, 0)
        self.assertTrue(text.startswith("#!/bin/sh"))
        self.assertIn("pnpm store prune", text)
        for line in text.splitlines()[1:]:
            self.assertTrue(line == "" or line.startswith("#"),
                            f"an uncommented line would be executable: {line!r}")

    def test_commands_does_not_repeat_itself(self):
        text = self.render(andy.print_commands, 0)
        self.assertEqual(text.count("pnpm store prune"), 1)


class Json(unittest.TestCase):
    def setUp(self):
        self.doc = json.loads(json.dumps(andy.to_json(sample_model())))

    def test_shape(self):
        self.assertEqual(self.doc["version"], andy.VERSION)
        self.assertEqual(self.doc["mapped_bytes"], 16 * 2 ** 30)
        self.assertEqual(self.doc["roots"], ["/r"])
        self.assertIn("volume", self.doc)

    def test_categories_sum_to_the_total(self):
        self.assertEqual(sum(c["bytes"] for c in self.doc["categories"]),
                         self.doc["mapped_bytes"])

    def test_informational_rows_are_marked(self):
        containers = next(c for c in self.doc["categories"]
                          if c["label"] == andy.CONTAINERS)
        live = next(c for c in containers["children"] if "live" in c["label"])
        self.assertTrue(live["informational"])

    def test_unmeasured_rows_are_marked(self):
        flat = []

        def visit(node):
            flat.append(node)
            for child in node.get("children", ()):
                visit(child)

        for cat in self.doc["categories"]:
            visit(cat)
        stuck = next(n for n in flat if n["label"] == "stuck")
        self.assertIs(stuck["complete"], False)
        self.assertIs(stuck["measured"], False)
        slow = next(n for n in flat if n["label"] == "slow vm")
        self.assertIs(slow["complete"], False)
        self.assertIs(slow["measured"], True, "a floor is still a measurement")
        self.assertEqual(slow["bytes"], 2 ** 30)

    def test_reclaim_commands_carry_a_safety_rating(self):
        def visit(node):
            if "reclaim" in node:
                self.assertIn(node["safety"], (andy.SAFE, andy.REBUILD, andy.REVIEW))
            for child in node.get("children", ()):
                visit(child)

        for cat in self.doc["categories"]:
            visit(cat)


if __name__ == "__main__":
    unittest.main()
