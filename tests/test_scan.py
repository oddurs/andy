"""The cache, and one end-to-end run of the real program over a real tree."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from andymod import andy, ANDY

Node = andy.Node

MB = 2 ** 20


def fill(path, megabytes):
    """A file of real blocks -- sizes here come from du, not from st_size."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(b"\0" * (megabytes * MB))


class Cache(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="andy-cache-")
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        patch = mock.patch.multiple(
            andy,
            CACHE_DIR=os.path.join(self.dir, "andy"),
            CACHE_FILE=os.path.join(self.dir, "andy", "scan.json"))
        patch.start()
        self.addCleanup(patch.stop)

    def test_round_trip(self):
        m = andy.Model()
        m.roots = ["/r"]
        m.category("x").children.append(Node(label="a", path="/a", measured=123))
        m.recompute()
        andy.save_cache(m, [("/r/p/node_modules", "node_modules")])

        data = andy.load_cache()
        self.assertEqual(data["sizes"]["/a"], 123)
        self.assertEqual(data["roots"], ["/r"])
        self.assertEqual(data["found"], [["/r/p/node_modules", "node_modules"]])
        self.assertEqual(data["version"], andy.VERSION)

    def test_unmeasured_nodes_are_not_cached(self):
        m = andy.Model()
        m.category("x").children.append(Node(label="a", path="/a", measured=None))
        m.recompute()
        andy.save_cache(m, [])
        self.assertEqual(andy.load_cache()["sizes"], {})

    def test_a_missing_cache_is_empty_not_an_error(self):
        self.assertEqual(andy.load_cache(), {})

    def test_a_corrupt_cache_is_empty_not_a_traceback(self):
        os.makedirs(andy.CACHE_DIR, exist_ok=True)
        with open(andy.CACHE_FILE, "w") as fh:
            fh.write("{not json at all")
        self.assertEqual(andy.load_cache(), {})

    def test_a_cache_of_the_wrong_shape_is_rejected(self):
        os.makedirs(andy.CACHE_DIR, exist_ok=True)
        with open(andy.CACHE_FILE, "w") as fh:
            json.dump(["not", "a", "dict"], fh)
        self.assertEqual(andy.load_cache(), {})

    def test_writing_is_atomic(self):
        m = andy.Model()
        m.category("x").children.append(Node(label="a", path="/a", measured=1))
        m.recompute()
        andy.save_cache(m, [])
        self.assertFalse(os.path.exists(andy.CACHE_FILE + ".tmp"),
                         "the temporary file should have been renamed away")

    def test_an_unwritable_cache_directory_is_survived(self):
        with mock.patch.object(andy.os, "makedirs", side_effect=OSError("read-only")):
            andy.save_cache(andy.Model(), [])       # must not raise


class Scan(unittest.TestCase):
    """A Scanner over a synthetic project tree, with the real catalog stubbed
    out so the result depends only on what the test created."""

    def setUp(self):
        self.root = os.path.realpath(tempfile.mkdtemp(prefix="andy-scan-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        fill(os.path.join(self.root, "app", "package.json"), 0)
        fill(os.path.join(self.root, "app", "node_modules", "big.bin"), 6)
        fill(os.path.join(self.root, "app", "src", "main.js"), 1)
        fill(os.path.join(self.root, "svc", "Cargo.toml"), 0)
        fill(os.path.join(self.root, "svc", "target", "debug.bin"), 4)
        os.makedirs(os.path.join(self.root, "svc", ".git"), exist_ok=True)
        fill(os.path.join(self.root, "svc", ".git", "pack.bin"), 2)

        # CATALOG out, and the docker daemon with it. On Linux andy counts what
        # `docker system df` reports -- there is no VM disk there for it to
        # duplicate -- so on any machine with a running daemon this scan would
        # otherwise pick up its images and measure the runner, not the tree.
        patches = mock.patch.multiple(andy, CATALOG=[], docker_breakdown=lambda: [])
        patches.start()
        self.addCleanup(patches.stop)

        self.model = andy.Model()
        self.model.roots = [self.root]
        scanner = andy.Scanner(self.model, [self.root], use_cache=False)
        scanner.start()
        scanner.join(120)
        self.assertTrue(self.model.finished, self.model.phase)

    def node(self, label):
        return next(n for n in self.model.walk() if n.label == label)

    def test_it_finished_without_an_error(self):
        self.assertEqual(self.model.phase, "done")

    def test_artifacts_were_found_and_grouped(self):
        labels = {n.label for n in self.model.walk()}
        self.assertIn("node_modules", labels)
        self.assertIn("cargo/maven target", labels)
        self.assertIn("app/node_modules", labels)
        self.assertIn("svc/target", labels)

    def test_git_repositories_are_their_own_category(self):
        repos = self.model.category(andy.REPOS)
        self.assertEqual([c.label for c in repos.children], ["svc/.git"])

    def test_sizes_are_at_least_what_was_written(self):
        self.assertGreaterEqual(self.node("app/node_modules").size, 6 * MB)
        self.assertGreaterEqual(self.node("svc/target").size, 4 * MB)
        self.assertGreaterEqual(self.node("svc/.git").size, 2 * MB)

    def test_source_files_are_not_counted(self):
        # andy maps disposable output; src/main.js is not disposable.
        self.assertLess(self.model.total, 20 * MB)

    def test_the_total_is_the_sum_of_the_categories(self):
        self.assertEqual(self.model.total,
                         sum(c.size for c in self.model.categories))

    def test_nothing_was_left_unmeasured(self):
        self.assertEqual([n.label for n in self.model.walk() if n.blocked], [])

    def test_the_tree_was_not_modified(self):
        self.assertTrue(os.path.exists(os.path.join(self.root, "app", "node_modules", "big.bin")))
        self.assertTrue(os.path.exists(os.path.join(self.root, "svc", "target", "debug.bin")))


class LiveDocker(unittest.TestCase):
    """What a running daemon contributes, which differs by platform.

    On macOS the daemon lives in a VM whose disk andy measures directly, so its
    own report is the same bytes seen from inside. On Linux there is no VM.
    A scan of one directory still reports it either way -- the catalog is about
    the machine, not about the roots -- and CI found this the hard way, on a
    runner that had images loaded."""

    ROWS = [("images", 1892595200, "docker image prune -a", andy.REBUILD, "9 total")]

    def scan(self):
        model = andy.Model()
        scanner = andy.Scanner(model, [], include_projects=False, use_cache=False)
        with mock.patch.object(andy, "CATALOG", []), \
             mock.patch.object(andy, "docker_breakdown", lambda: self.ROWS):
            scanner.start()
            scanner.join(60)
        self.assertTrue(model.finished, model.phase)
        return model

    def test_the_daemons_figures_are_counted_only_where_they_are_not_a_duplicate(self):
        total = self.scan().total
        if andy.MACOS:
            self.assertEqual(total, 0, "the VM disk was counted twice")
        else:
            self.assertEqual(total, 1892595200, "the only figure available was dropped")


class EndToEnd(unittest.TestCase):
    """The installed program, as a user runs it.

    HOME points at an empty directory, so every catalog path resolves to
    somewhere that does not exist and the run depends only on the tree below.
    """

    def setUp(self):
        self.dir = os.path.realpath(tempfile.mkdtemp(prefix="andy-e2e-"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        self.home = os.path.join(self.dir, "home")
        os.makedirs(self.home)
        self.project = os.path.join(self.dir, "work")
        fill(os.path.join(self.project, "app", "package.json"), 0)
        fill(os.path.join(self.project, "app", "node_modules", "big.bin"), 5)

    def run_andy(self, *args):
        env = dict(os.environ,
                   HOME=self.home,
                   XDG_CACHE_HOME=os.path.join(self.dir, "cache"),
                   # point docker at nothing, so the run describes the tree below
                   # and not whatever the machine happens to have running
                   DOCKER_HOST="unix:///nonexistent/andy-test.sock",
                   NO_COLOR="1")
        return subprocess.run([sys.executable, ANDY, *args, self.project],
                              capture_output=True, text=True, timeout=180, env=env)

    def test_json_output_is_valid_and_adds_up(self):
        p = self.run_andy("--json", "--fresh")
        self.assertEqual(p.returncode, 0, p.stderr)
        doc = json.loads(p.stdout)
        self.assertEqual(doc["roots"], [self.project])
        self.assertGreaterEqual(doc["mapped_bytes"], 5 * MB)
        self.assertEqual(sum(c["bytes"] for c in doc["categories"]),
                         doc["mapped_bytes"])

    def test_the_default_report_mentions_what_it_found(self):
        p = self.run_andy("--fresh", "-n", "5")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("node_modules", p.stdout)

    def test_commands_output_is_inert(self):
        p = self.run_andy("--commands", "--fresh", "-m", "1M")
        self.assertEqual(p.returncode, 0, p.stderr)
        for line in p.stdout.splitlines():
            self.assertTrue(line == "" or line.startswith("#"), line)

    def test_the_cache_is_written_and_then_reused(self):
        cache = os.path.join(self.dir, "cache", "andy", "scan.json")
        self.assertEqual(self.run_andy("--json", "--fresh").returncode, 0)
        self.assertTrue(os.path.exists(cache))
        second = self.run_andy("--json")
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertGreaterEqual(json.loads(second.stdout)["mapped_bytes"], 5 * MB)

    def test_interactive_refuses_without_a_terminal(self):
        p = self.run_andy("-i")
        self.assertEqual(p.returncode, 2)
        # on a Python with no curses the refusal says that instead, which is
        # the more useful answer and still a refusal
        self.assertIn("needs curses" if andy.curses is None else "needs a terminal",
                      p.stderr)

    def test_version(self):
        env = dict(os.environ, HOME=self.home)
        p = subprocess.run([sys.executable, ANDY, "--version"],
                           capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(p.returncode, 0)
        self.assertIn(andy.VERSION, p.stdout)

    def test_nothing_under_the_project_was_touched(self):
        before = {}
        for dirpath, _, names in os.walk(self.project):
            for name in names:
                full = os.path.join(dirpath, name)
                before[full] = os.stat(full).st_mtime_ns
        self.assertEqual(self.run_andy("--json", "--fresh").returncode, 0)
        after = {}
        for dirpath, _, names in os.walk(self.project):
            for name in names:
                full = os.path.join(dirpath, name)
                after[full] = os.stat(full).st_mtime_ns
        self.assertEqual(before, after, "andy is supposed to be read-only")


if __name__ == "__main__":
    unittest.main()
