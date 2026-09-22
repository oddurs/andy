"""Every output format, against a model with known numbers.

The point is not the exact layout -- that is allowed to change -- but that each
format renders without raising at any terminal width, and that the numbers it
prints are the numbers in the model.
"""

import io
import json
import shlex
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


class Reclaimable(unittest.TestCase):
    """cairn 0028. The rating was decision support printed everywhere except
    where the decision gets made."""

    def setUp(self):
        self.m = sample_model()

    def test_the_split_adds_up_to_what_was_mapped(self):
        split = self.m.by_safety()
        self.assertEqual(sum(split.values()), self.m.total)

    def test_groups_and_breakdowns_are_not_counted_twice(self):
        m = andy.Model()
        cat = m.category(andy.TOOLCHAINS)
        parent = Node(label="rustup", path="/h/r", measured=1000, safety=andy.REVIEW)
        parent.children.append(Node(label="stable", path="/h/r/s", measured=1000,
                                    safety=andy.REVIEW, detail=True))
        cat.children.append(parent)
        m.recompute()
        self.assertEqual(m.by_safety()[andy.REVIEW], 1000)
        self.assertEqual(sum(m.by_safety().values()), m.total)

    def test_the_report_states_it(self):
        out = io.StringIO()
        andy.print_report(self.m, andy.Ink(False), 12, out=out)
        text = out.getvalue()
        self.assertIn("of which", text)
        self.assertIn("regenerates itself", text)
        self.assertIn("costs you a rebuild", text)
        self.assertIn("wants a look first", text)

    def test_every_largest_item_carries_its_rating(self):
        out = io.StringIO()
        andy.print_report(self.m, andy.Ink(False), 12, out=out)
        text = out.getvalue()
        self.assertIn("s regenerates itself", text)     # the legend
        body = text[text.index("largest items"):]
        for line in body.splitlines():
            if "OrbStack" in line or "pnpm store" in line:
                self.assertRegex(line, r"\s[sr!]\s", line)

    def test_the_marks_are_distinct(self):
        """safe, rebuild and review: two of them start with the same letter."""
        self.assertEqual(len(set(andy.MARK.values())), 3)

    def test_nothing_promises_a_deletion(self):
        out = io.StringIO()
        andy.print_report(self.m, andy.Ink(False), 12, out=out)
        text = out.getvalue().lower()
        for word in ("will delete", "deleting", "freed", "reclaimed "):
            self.assertNotIn(word, text)

    def test_an_empty_model_has_an_empty_split(self):
        self.assertEqual(sum(andy.Model().by_safety().values()), 0)


class Json(unittest.TestCase):
    def setUp(self):
        self.doc = json.loads(json.dumps(andy.to_json(sample_model())))

    def test_shape(self):
        self.assertEqual(self.doc["version"], andy.VERSION)
        self.assertEqual(sum(self.doc["reclaimable_bytes"].values()),
                         self.doc["mapped_bytes"])
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


class ReclaimCommands(unittest.TestCase):
    """cairn 0029. andy knew every path and printed `<project>` anyway."""

    def model(self):
        m = andy.Model()
        m.roots = ["/r"]
        projects = m.category(andy.PROJECTS)
        group = Node(label="cargo/maven target", kind="cargo/maven target",
                     note="Compiled Rust output.", cmd="rm -rf <path>",
                     safety=andy.REBUILD)
        for name, size in (("big", 5 * 2 ** 30), ("small", 2 * 2 ** 30),
                           ("with space", 2 ** 30)):
            group.children.append(Node(label=f"{name}/target",
                                       path=f"/r/{name}/target", measured=size,
                                       note=group.note, cmd=group.cmd,
                                       safety=andy.REBUILD))
        projects.children.append(group)

        tools = m.category(andy.TOOLCHAINS)
        rustup = Node(label="rustup toolchains", path="/h/rustup",
                      measured=3 * 2 ** 30, safety=andy.REVIEW,
                      note="One per channel.",
                      cmd="rustup toolchain uninstall <name>")
        for name, size in (("stable", 2 * 2 ** 30), ("nightly", 2 ** 30)):
            rustup.children.append(Node(label=name, path=f"/h/rustup/{name}",
                                        measured=size, detail=True,
                                        safety=andy.REVIEW,
                                        cmd=rustup.cmd, note=rustup.note))
        tools.children.append(rustup)

        caches = m.category(andy.PACKAGES)
        caches.children.append(Node(label="pnpm store", path="/h/pnpm",
                                    measured=2 ** 30, cmd="pnpm store prune",
                                    note="Shared store.", safety=andy.SAFE))
        m.recompute()
        return m

    def render(self, m, min_bytes=0):
        out = io.StringIO()
        andy.print_commands(m, andy.Ink(False), min_bytes, out=out)
        return out.getvalue()

    def test_a_group_becomes_its_members(self):
        text = self.render(self.model())
        self.assertIn("/r/big/target", text)
        self.assertIn("/r/small/target", text)
        self.assertNotIn("<path>", text)

    def test_members_are_largest_first(self):
        text = self.render(self.model())
        self.assertLess(text.index("/r/big/target"), text.index("/r/small/target"))

    def test_a_name_placeholder_becomes_the_itemised_children(self):
        text = self.render(self.model())
        self.assertIn("rustup toolchain uninstall stable", text)
        self.assertIn("rustup toolchain uninstall nightly", text)
        self.assertNotIn("<name>", text)

    def test_a_path_with_a_space_is_quoted(self):
        text = self.render(self.model())
        self.assertIn("'/r/with space/target'", text,
                      "an unquoted space would split the rm into two arguments")

    def test_a_global_command_is_said_once(self):
        text = self.render(self.model())
        self.assertEqual(text.count("pnpm store prune"), 1)

    def test_a_shared_note_is_said_once(self):
        text = self.render(self.model())
        self.assertEqual(text.count("Compiled Rust output."), 1,
                         "the explanation buried the paths it was explaining")

    def test_the_totals_are_printed(self):
        text = self.render(self.model())
        self.assertIn("would reclaim about", text)
        self.assertRegex(text, r"# ---- project artifacts\s+8\.0G")

    def test_every_line_is_still_inert(self):
        for line in self.render(self.model()).splitlines():
            self.assertTrue(line == "" or line.startswith("#"), line)

    def test_a_floor_above_everything_says_so(self):
        text = self.render(self.model(), min_bytes=100 * 2 ** 40)
        self.assertIn("nothing here is over the size floor", text)

    def test_a_placeholder_andy_cannot_fill_is_left_standing(self):
        m = andy.Model()
        m.category(andy.TOOLCHAINS).children.append(
            Node(label="asdf", path="/h/asdf", measured=2 ** 30,
                 cmd="asdf uninstall <plugin> <version>"))
        m.recompute()
        text = self.render(m)
        self.assertIn("<plugin>", text, "a value andy does not have was invented")


class FillCommand(unittest.TestCase):
    def node(self, path):
        return Node(label="x", path=path, measured=1)

    def test_the_measured_directory(self):
        self.assertEqual(andy.fill_command("rm -rf <path>", self.node("/a/b"), []),
                         "rm -rf /a/b")

    def test_the_directory_holding_it(self):
        self.assertEqual(
            andy.fill_command("rm -rf <project>/.next", self.node("/a/b/.next"), []),
            "rm -rf /a/b/.next")

    def test_the_scan_root(self):
        self.assertEqual(
            andy.fill_command("find <root>", self.node("/r/p/node_modules"), ["/r"]),
            "find /r")

    def test_the_name(self):
        self.assertEqual(
            andy.fill_command("nvm uninstall <version>", self.node("/h/.nvm/v20"), []),
            "nvm uninstall v20")

    def test_a_command_with_nothing_to_fill(self):
        self.assertEqual(andy.fill_command("pnpm store prune", self.node("/a"), []),
                         "pnpm store prune")

    def test_a_node_with_no_path_is_left_alone(self):
        self.assertEqual(andy.fill_command("rm -rf <path>", Node(label="x"), []),
                         "rm -rf <path>")

    def test_quoting_covers_the_characters_that_break_a_command(self):
        for awkward in ("/a/with space/t", "/a/semi;colon/t", "/a/new\nline/t",
                        "/a/dollar$sign/t"):
            out = andy.fill_command("rm -rf <path>", self.node(awkward), [])
            self.assertEqual(shlex.split(out), ["rm", "-rf", awkward], out)


class NothingFound(unittest.TestCase):
    """cairn 0032. One dead end covered four situations, three of which have
    something useful to say and the first of which is good news."""

    def render(self, m, fn=None, arg=12):
        out = io.StringIO()
        (fn or andy.print_report)(m, andy.Ink(False), arg, out=out)
        return out.getvalue()

    def test_a_clean_machine_with_no_project_directories(self):
        m = andy.Model()
        text = self.render(m)
        self.assertIn("no project directories to look in", text)
        self.assertIn("andy ~/src", text)

    def test_roots_that_hold_nothing_are_named(self):
        m = andy.Model()
        m.roots = ["/home/someone/src", "/home/someone/work"]
        text = self.render(m)
        self.assertIn("/home/someone/src", text)
        self.assertIn("/home/someone/work", text)
        self.assertIn("name the directory", text)

    def test_a_failed_scan_is_not_reported_as_an_empty_one(self):
        m = andy.Model()
        m.phase = "scan error: permission denied"
        text = self.render(m)
        self.assertIn("did not finish", text)
        self.assertIn("permission denied", text)
        self.assertNotIn("nothing found", text)

    def test_a_tree_hidden_entirely_by_the_floor_says_so(self):
        m = andy.Model()
        m.category(andy.PACKAGES).children.append(
            Node(label="small", path="/h/s", measured=40 * 1024))
        m.recompute()
        text = self.render(m, andy.print_tree, 10 * 2 ** 20)
        self.assertIn("none of them over 10.0M", text)
        self.assertIn("40.0K", text)
        self.assertIn("-m 0", text)

    def test_one_location_is_singular(self):
        m = andy.Model()
        m.category(andy.PACKAGES).children.append(
            Node(label="small", path="/h/s", measured=1024))
        m.recompute()
        self.assertIn("1 location found", self.render(m, andy.print_tree, 2 ** 20))

    def test_an_empty_tree_with_nothing_at_all_explains_that_instead(self):
        text = self.render(andy.Model(), andy.print_tree, 2 ** 20)
        self.assertIn("nothing found", text)
