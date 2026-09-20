"""`--delta`: what changed since last time.

This is the only part of andy that is about time rather than about now, so most
of what matters here is that it does not overstate what it knows.
"""

import io
import json
import os
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


class Signed(unittest.TestCase):
    def test_direction_is_explicit(self):
        self.assertEqual(andy.signed(2 * 2 ** 30), "+2.0G")
        self.assertEqual(andy.signed(-840 * MB), "-840M")

    def test_no_change_is_not_plus_zero(self):
        self.assertEqual(andy.signed(0), "-")


class Ago(unittest.TestCase):
    def test_units(self):
        self.assertEqual(andy.ago(5), "moments ago")
        self.assertEqual(andy.ago(90), "1 minute ago")
        self.assertEqual(andy.ago(3600 * 5), "5 hours ago")
        self.assertEqual(andy.ago(86400 * 3), "3 days ago")

    def test_singular_and_plural(self):
        self.assertEqual(andy.ago(3600), "1 hour ago")
        self.assertEqual(andy.ago(7200), "2 hours ago")

    def test_a_clock_that_moved_backwards_says_so(self):
        # better than "0 minutes ago", which reads as a fact
        self.assertEqual(andy.ago(-500), "the future")


def model_with(previous_at=None, rows=(), vanished=()):
    m = andy.Model()
    m.disk = (500 * 2 ** 30, 300 * 2 ** 30, 200 * 2 ** 30)
    m.previous_at = previous_at if previous_at is not None else time.time() - 3600
    cat = m.category(andy.PACKAGES)
    for label, now, before in rows:
        cat.children.append(Node(label=label, path=f"/h/{label}",
                                 measured=now, before=before))
    m.vanished = list(vanished)
    m.recompute()
    return m


def render(m, top=12):
    out = io.StringIO()
    andy.print_delta(m, andy.Ink(False), top, out=out)
    return out.getvalue()


class Report(unittest.TestCase):
    def test_nothing_to_compare_against_is_a_sentence(self):
        text = render(model_with(previous_at=0))
        self.assertIn("nothing to compare against", text)
        self.assertIn("first scan", text)

    def test_the_interval_is_stated(self):
        text = render(model_with(previous_at=time.time() - 86400 * 2,
                                 rows=[("a", 3 * MB, 1 * MB)]))
        self.assertIn("2 days ago", text)

    def test_growth_and_shrinkage(self):
        text = render(model_with(rows=[("grew", 3 * MB, 1 * MB),
                                       ("shrank", 1 * MB, 5 * MB)]))
        self.assertIn("+2.0M", text)
        self.assertIn("-4.0M", text)
        self.assertIn("1.0M", text)         # the before/after pair

    def test_a_location_with_no_previous_figure_is_new_not_growth(self):
        text = render(model_with(rows=[("fresh", 9 * MB, None)]))
        self.assertIn("new", text)
        self.assertIn("not measured before", text)
        self.assertNotIn("+9.0M", text,
                         "a location andy had never seen was reported as growth")
        self.assertIn("9.0M", text)

    def test_a_location_that_disappeared_is_reported(self):
        text = render(model_with(rows=[("stays", MB, MB)],
                                 vanished=[("/h/gone", 7 * MB)]))
        self.assertIn("gone", text)
        self.assertIn("/h/gone", text)
        self.assertIn("-7.0M", text)

    def test_unchanged_locations_are_left_out(self):
        text = render(model_with(rows=[("same", 4 * MB, 4 * MB)]))
        self.assertIn("nothing has changed size", text)
        self.assertNotIn("same", text)

    def test_the_three_totals_are_kept_apart(self):
        """Growth andy can vouch for, and two kinds it cannot."""
        text = render(model_with(rows=[("grew", 5 * MB, 1 * MB),
                                       ("fresh", 2 * MB, None)],
                                 vanished=[("/h/gone", 1 * MB)]))
        self.assertIn("net", text)
        self.assertIn("+4.0M", text)                   # the comparable change
        self.assertIn("andy could compare", text)
        self.assertIn("2.0M in 1 location", text)      # new, counted apart
        self.assertIn("1.0M in 1 location", text)      # gone, counted apart

    def test_new_locations_are_not_folded_into_the_net(self):
        """A catalog entry added since the last release makes bytes that were
        always there look like growth, so they are reported separately."""
        text = render(model_with(rows=[("fresh", 9 * MB, None)]))
        self.assertIn("may mean created or merely recognised", text)
        self.assertIn("net  -", text, "a never-measured location moved the net")

    def test_sorted_by_size_of_change_not_by_size(self):
        m = model_with(rows=[("huge but steady", 100 * MB, 99 * MB),
                             ("small but doubled", 4 * MB, 1 * MB)])
        body = render(m)
        self.assertLess(body.index("small but doubled"), body.index("huge but steady"))

    def test_the_list_is_capped_and_says_so(self):
        rows = [(f"n{i}", (i + 2) * MB, MB) for i in range(30)]
        text = render(model_with(rows=rows), top=5)
        self.assertIn("and 25 more", text)

    def test_it_survives_every_width(self):
        m = model_with(rows=[("a" * 60, 5 * MB, MB), ("b", 2 * MB, None)],
                       vanished=[("/very/long/" + "x" * 80, MB)])
        for width in (20, 40, 80, 200):
            with mock.patch.object(andy.shutil, "get_terminal_size",
                                   return_value=os.terminal_size((width, 24))):
                render(m)

    def test_breakdowns_are_not_listed_as_their_own_change(self):
        m = andy.Model()
        m.previous_at = time.time() - 60
        cat = m.category(andy.TOOLCHAINS)
        parent = Node(label="rustup toolchains", path="/h/r", measured=1000, before=600)
        parent.children.append(Node(label="stable", path="/h/r/stable",
                                    measured=1000, before=600, detail=True))
        cat.children.append(parent)
        m.recompute()
        text = render(m)
        self.assertIn("rustup toolchains", text)
        self.assertNotIn("stable", text)


class Json(unittest.TestCase):
    def test_the_previous_figures_are_carried(self):
        m = model_with(rows=[("a", 3 * MB, MB)], vanished=[("/h/gone", 2 * MB)])
        doc = json.loads(json.dumps(andy.to_json(m)))
        row = doc["categories"][0]["children"][0]
        self.assertEqual(row["previous_bytes"], MB)
        self.assertEqual(row["change_bytes"], 2 * MB)
        self.assertEqual(doc["vanished"], [{"path": "/h/gone", "previous_bytes": 2 * MB}])
        self.assertTrue(doc["previous_scan_at"])

    def test_a_first_scan_says_there_is_no_previous_one(self):
        doc = andy.to_json(model_with(previous_at=0))
        self.assertIsNone(doc["previous_scan_at"])


class EndToEnd(unittest.TestCase):
    """Two real scans of a tree that changed in between."""

    def setUp(self):
        self.dir = os.path.realpath(tempfile.mkdtemp(prefix="andy-delta-"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        self.home = os.path.join(self.dir, "home")
        self.tree = os.path.join(self.dir, "work")
        os.makedirs(self.home)
        self.write("app/node_modules/a.bin", 20)
        self.write("app/package.json", 0)
        self.write("svc/target/b.bin", 10)
        self.write("svc/Cargo.toml", 0)

    def write(self, rel, mb):
        path = os.path.join(self.tree, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(b"\0" * (mb * MB))

    def run_andy(self, *args):
        env = dict(os.environ, HOME=self.home,
                   XDG_CACHE_HOME=os.path.join(self.home, ".cache"),
                   XDG_DATA_HOME=os.path.join(self.home, ".local", "share"),
                   XDG_CONFIG_HOME=os.path.join(self.home, ".config"),
                   XDG_STATE_HOME=os.path.join(self.home, ".local", "state"),
                   DOCKER_HOST="unix:///nonexistent/andy.sock", NO_COLOR="1")
        return subprocess.run([sys.executable, ANDY, *args, self.tree],
                              capture_output=True, text=True, timeout=180, env=env)

    def test_the_whole_cycle(self):
        first = self.run_andy("--json")
        self.assertEqual(first.returncode, 0, first.stderr[-400:])

        self.write("app/node_modules/grew.bin", 35)       # +35M
        shutil.rmtree(os.path.join(self.tree, "svc", "target"))   # -10M
        self.write("new/node_modules/c.bin", 8)           # new
        self.write("new/package.json", 0)

        p = self.run_andy("--delta")
        self.assertEqual(p.returncode, 0, p.stderr[-400:])
        text = p.stdout
        self.assertIn("+35.0M", text)
        self.assertIn("app/node_modules", text)
        self.assertIn("new/node_modules", text)
        self.assertIn("gone", text)
        self.assertIn("svc/target", text)

    def test_a_first_run_has_nothing_to_compare(self):
        p = self.run_andy("--delta")
        self.assertEqual(p.returncode, 0, p.stderr[-400:])
        self.assertIn("nothing to compare against", p.stdout)

    def test_delta_with_fresh_is_refused(self):
        """--fresh ignores the cache, so there would be nothing to subtract."""
        p = self.run_andy("--delta", "--fresh")
        self.assertEqual(p.returncode, 2)
        self.assertIn("--fresh", p.stderr)


if __name__ == "__main__":
    unittest.main()
