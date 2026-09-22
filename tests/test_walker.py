"""The in-process walker, against du(1) and against the awkward cases.

du is the oracle here: it is the tool the numbers used to come from, it ships
with both platforms CI runs on, and if the two ever disagree the walker is the
one that is wrong.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

from andymod import andy

MB = 2 ** 20


def du(path):
    """The oracle: what `du -skx` says, straight from the system's own tool.

    Bytes, then os.fsdecode, for the same reason andy does it: in a C locale
    text mode would decode a path as ASCII and raise on the first one that
    is not.
    """
    out = subprocess.run(["du", "-skx", path], capture_output=True,
                         timeout=120).stdout
    return int(out.split(b"\t")[0]) * 1024


ENGINES = (andy.DuMeasurer, andy.Walker)


def measure(path, engine=andy.DuMeasurer, workers=4, budget=120.0):
    """Measure one path, returning (bytes, status) and the climbing updates."""
    settled = {}
    running = []

    def publish(updates):
        for target, size, status in updates:
            if status == "running":
                running.append((target, size))
            else:
                settled[target] = (size, status)

    engine(workers).run([path], publish, budget=budget)
    return settled.get(path), running


def walk(path, workers=4, budget=120.0):
    return measure(path, andy.Walker, workers, budget)


class Tree(unittest.TestCase):
    def setUp(self):
        self.root = os.path.realpath(tempfile.mkdtemp(prefix="andy-walk-"))
        self.addCleanup(self.cleanup)

    def cleanup(self):
        for dirpath, dirnames, _ in os.walk(self.root):
            for name in dirnames:
                try:
                    os.chmod(os.path.join(dirpath, name), 0o755)
                except OSError:
                    pass
        shutil.rmtree(self.root, ignore_errors=True)

    def fill(self, rel, megabytes):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(b"\0" * int(megabytes * MB))
        return path


class AgreesWithDu(Tree):
    def assertMatchesDu(self, why=""):
        for engine in ENGINES:
            (size, status), _ = measure(self.root, engine)
            self.assertEqual(status, "done", engine.__name__)
            self.assertEqual(size, du(self.root), f"{engine.__name__}: {why}")

    def test_a_plain_tree(self):
        self.fill("a/one.bin", 3)
        self.fill("a/b/two.bin", 2)
        self.fill("three.bin", 1)
        self.assertMatchesDu()

    def test_an_empty_directory(self):
        self.assertMatchesDu("a directory still costs its own blocks")

    def test_a_sparse_file_costs_its_blocks_not_its_length(self):
        path = os.path.join(self.root, "disk.img")
        with open(path, "wb") as fh:
            fh.truncate(8 * 2 ** 30)        # 8G of nothing
            fh.seek(2 * MB)
            fh.write(b"x")
        for engine in ENGINES:
            (size, _), _ = measure(self.root, engine)
            self.assertEqual(size, du(self.root), engine.__name__)
        self.assertLess(size, 64 * MB,
                        "st_size was used instead of st_blocks; a container "
                        "disk would be reported at its apparent size")

    def test_hard_links_are_counted_once(self):
        target = self.fill("data.bin", 4)
        os.link(target, os.path.join(self.root, "same.bin"))
        os.makedirs(os.path.join(self.root, "sub"))
        os.link(target, os.path.join(self.root, "sub", "same-again.bin"))
        for engine in ENGINES:
            (size, _), _ = measure(self.root, engine)
            self.assertEqual(size, du(self.root), engine.__name__)
        self.assertLess(size, 8 * MB, "one inode was counted three times")

    def test_symlinks_are_counted_but_not_followed(self):
        self.fill("real/big.bin", 6)
        os.symlink(os.path.join(self.root, "real"), os.path.join(self.root, "alias"))
        os.symlink("/etc", os.path.join(self.root, "outside"))
        os.symlink("/nowhere-at-all", os.path.join(self.root, "dangling"))
        for engine in ENGINES:
            (size, _), _ = measure(self.root, engine)
            self.assertEqual(size, du(self.root), engine.__name__)
        self.assertLess(size, 12 * MB, "a symlinked directory was walked twice")

    def test_an_unreadable_directory_is_skipped_not_fatal(self):
        self.fill("open/file.bin", 2)
        closed = os.path.join(self.root, "closed")
        os.makedirs(os.path.join(closed, "inside"))
        os.chmod(closed, 0o000)
        for engine in ENGINES:
            (size, status), _ = measure(self.root, engine)
            self.assertEqual(status, "done", engine.__name__)
            self.assertEqual(size, du(self.root), engine.__name__)

    def test_many_small_files(self):
        for i in range(400):
            self.fill(f"n{i % 20}/f{i}.bin", 0.01)
        self.assertMatchesDu()

    def test_a_deep_tree(self):
        self.fill(os.path.join(*[f"d{i}" for i in range(20)], "deep.bin"), 1)
        self.assertMatchesDu()


class OneFilesystem(Tree):
    def test_entries_on_another_device_are_not_counted(self):
        """`du -x`. Verified against a real nested mount by hand; here the
        device is forced, so the branch is covered without privileges."""
        self.fill("top.bin", 4)         # a file, because on APFS a directory
        self.fill("a/below.bin", 1)     # entry reports st_blocks == 0
        walker = andy.Walker(1)
        w = andy.Walk(self.root)
        w.dev = os.lstat(self.root).st_dev
        total, subdirs = walker._scan(w, self.root)
        self.assertGreaterEqual(total, 4 * MB)
        self.assertEqual(subdirs, [os.path.join(self.root, "a")])

        other = andy.Walk(self.root)
        other.dev = w.dev + 1           # pretend everything below is a mount
        total, subdirs = walker._scan(other, self.root)
        self.assertEqual((total, subdirs), (0, []))


class Progress(Tree):
    def test_the_total_climbs_while_the_walk_runs(self):
        """A walk that outlasts a tick publishes floors that only ever rise.

        It used to rely on sixty small files taking longer than one 0.12s tick
        to measure. Alone on a fast machine they do not, so it failed eight
        times out of eight in a clean container and passed only when the rest
        of the suite happened to slow the machine down. The property is about
        long walks, so each engine is made to take a long one.
        """
        for i in range(60):
            self.fill(f"d{i}/f.bin", 1)
        real_popen, real_scan = subprocess.Popen, andy.scan_dir

        class SlowDu:
            """du, reading its lines back no faster than 100 a second."""
            def __init__(self, *args, **kwargs):
                self._proc = real_popen(*args, **kwargs)
                self.stdout = self._lines()

            def _lines(self):
                for line in self._proc.stdout:
                    time.sleep(0.01)
                    yield line

            def __getattr__(self, name):
                return getattr(self._proc, name)

        def slow_scan(*args, **kwargs):
            time.sleep(0.01)
            return real_scan(*args, **kwargs)

        for engine in ENGINES:
            with mock.patch.object(andy.subprocess, "Popen", SlowDu), \
                 mock.patch.object(andy, "scan_dir", slow_scan):
                (size, status), running = measure(self.root, engine, workers=2)
            self.assertEqual(status, "done", engine.__name__)
            self.assertTrue(running,
                            f"{engine.__name__} published no partial figures at all")
            climbs = [s for _, s in running]
            self.assertEqual(climbs, sorted(climbs),
                             f"{engine.__name__}: a published floor went down")
            self.assertLessEqual(max(climbs), size)

    def test_a_missing_path_is_zero_rather_than_a_mystery(self):
        for engine in ENGINES:
            (size, status), _ = measure(os.path.join(self.root, "gone"), engine)
            self.assertEqual((size, status), (0, "done"), engine.__name__)


class Budget(Tree):
    def setUp(self):
        super().setUp()
        for i in range(40):
            self.fill(f"d{i}/f.bin", 1)

    def test_running_out_of_time_yields_a_floor_not_a_zero(self):
        gate = threading.Event()
        real_scan = andy.Walker._scan

        def slow(self, w, path):
            if path != w.root:
                gate.wait(30)           # every subdirectory hangs
            return real_scan(self, w, path)

        with mock.patch.object(andy.Walker, "_scan", slow):
            started = time.time()
            (size, status), _ = walk(self.root, workers=2, budget=0.6)
        gate.set()
        self.assertEqual(status, "partial")
        self.assertGreaterEqual(size, 0)
        self.assertLess(time.time() - started, 15,
                        "a wedged worker delayed the answer")

    def test_a_wedged_worker_does_not_delay_the_caller(self):
        forever = threading.Event()
        self.addCleanup(forever.set)

        with mock.patch.object(andy.Walker, "_scan",
                               lambda self, w, p: (forever.wait(60), (0, []))[1]):
            started = time.time()
            walk(self.root, workers=2, budget=0.4)
            elapsed = time.time() - started
        self.assertLess(elapsed, 10, "run() waited for a thread it should abandon")

    def test_cancelling_returns_at_once(self):
        for engine in ENGINES:
            cancel = threading.Event()
            cancel.set()
            started = time.time()
            engine(2, cancel).run([self.root], lambda updates: None, budget=60)
            self.assertLess(time.time() - started, 5, engine.__name__)


class DuProcesses(Tree):
    """du runs as a child process, so andy owns its lifetime."""

    def setUp(self):
        super().setUp()
        for i in range(30):
            self.fill(f"d{i}/f.bin", 0.5)

    def test_no_du_process_outlives_the_measurement(self):
        engine = andy.DuMeasurer(4)
        engine.run([self.root], lambda updates: None, budget=60)
        self.assertEqual(engine._procs, set())

    def test_stopping_kills_what_is_still_running(self):
        engine = andy.DuMeasurer(2)
        started = threading.Event()
        real = andy.DuMeasurer._step

        def slow(self, walk):
            started.set()
            time.sleep(5)
            return real(self, walk)

        with mock.patch.object(andy.DuMeasurer, "_step", slow):
            thread = threading.Thread(
                target=engine.run, args=([self.root], lambda u: None), daemon=True)
            thread.start()
            started.wait(5)
            engine.stop()
            thread.join(5)
        self.assertFalse(thread.is_alive(), "run() did not return after stop()")
        self.assertEqual(engine._procs, set())

    def test_running_out_of_time_still_reports_a_floor(self):
        # hold du open past the budget rather than racing it with a short one
        gate = threading.Event()
        self.addCleanup(gate.set)
        real = andy.DuMeasurer._step

        def slow(self, walk):
            gate.wait(20)
            return real(self, walk)

        with mock.patch.object(andy.DuMeasurer, "_step", slow):
            (size, status), _ = measure(self.root, andy.DuMeasurer,
                                        workers=1, budget=0.5)
        self.assertEqual(status, "partial")
        self.assertGreaterEqual(size, 0)
        self.assertLessEqual(size, du(self.root))


class Threads(unittest.TestCase):
    def test_task_returns_a_value(self):
        self.assertEqual(andy.Task(lambda a, b: a + b, 2, 3).result(5), 5)

    def test_task_swallows_an_exception(self):
        def boom():
            raise RuntimeError("no")
        self.assertEqual(andy.Task(boom).result(5, default="fallback"), "fallback")

    def test_task_that_is_still_running_gives_the_default(self):
        gate = threading.Event()
        self.addCleanup(gate.set)
        task = andy.Task(lambda: gate.wait(30))
        self.assertEqual(task.result(0.1, default="not yet"), "not yet")

    def test_task_threads_are_daemons(self):
        gate = threading.Event()
        self.addCleanup(gate.set)
        before = {t for t in threading.enumerate()}
        andy.Task(lambda: gate.wait(30))
        time.sleep(0.05)
        new = [t for t in threading.enumerate() if t not in before]
        self.assertTrue(new and all(t.daemon for t in new),
                        "a non-daemon thread would hold up interpreter exit")


class ApplyStatus(unittest.TestCase):
    """How a measurement folds into a node -- the rules the display depends on."""

    def node(self, **kw):
        return andy.Node(label="n", path="/p", **kw)

    def test_a_finished_walk_is_exact(self):
        n = self.node(measured=5, stale=True, partial=True, blocked=True)
        andy.Scanner._apply(n, 100, "done")
        self.assertEqual((n.measured, n.stale, n.partial, n.blocked),
                         (100, False, False, False))

    def test_a_climbing_figure_is_marked_as_a_floor(self):
        n = self.node()
        andy.Scanner._apply(n, 40, "running")
        self.assertEqual((n.measured, n.partial), (40, True))

    def test_a_climbing_figure_does_not_undercut_a_cached_one(self):
        # the scan opens showing 100 from last time; the floor starts near zero
        n = self.node(measured=100, stale=True)
        andy.Scanner._apply(n, 5, "running")
        self.assertEqual((n.measured, n.stale), (100, True), "the display jumped down")
        andy.Scanner._apply(n, 120, "running")
        self.assertEqual((n.measured, n.stale, n.partial), (120, False, True))
        andy.Scanner._apply(n, 130, "running")
        self.assertEqual(n.measured, 130, "later floors must apply once live")

    def test_a_floor_beats_a_stale_figure_it_has_overtaken(self):
        n = self.node(measured=100, stale=True)
        andy.Scanner._apply(n, 500, "partial")
        self.assertEqual((n.measured, n.partial, n.blocked), (500, True, True))

    def test_a_stale_figure_survives_a_smaller_floor(self):
        n = self.node(measured=500, stale=True)
        andy.Scanner._apply(n, 100, "partial")
        self.assertEqual((n.measured, n.partial, n.blocked), (500, False, True))

    def test_nothing_counted_and_nothing_known(self):
        n = self.node()
        andy.Scanner._apply(n, 0, "partial")
        self.assertEqual((n.measured, n.partial, n.blocked), (None, False, True))


if __name__ == "__main__":
    unittest.main()


class OddPaths(Tree):
    """du's output is `size<TAB>path`, one record per line, and a path may
    contain both. cairn 0020: a newline turned 7.0M into 17.0M."""

    def build(self, name):
        base = os.path.join(self.root, name)
        os.makedirs(os.path.join(base, "a", "b"), exist_ok=True)
        for rel, mb in (("top.bin", 1), (os.path.join("a", "mid.bin"), 2),
                        (os.path.join("a", "b", "deep.bin"), 4)):
            path = os.path.join(base, rel)
            with open(path, "wb") as fh:
                fh.write(b"\0" * (mb * MB))
        return base

    def assertBothEngines(self, base):
        for engine in ENGINES:
            (size, status), _ = measure(base, engine)
            self.assertEqual(status, "done", engine.__name__)
            self.assertEqual(size, du(base), engine.__name__)

    def test_a_newline_in_a_directory_name(self):
        self.assertBothEngines(self.build("we\nird"))

    def test_a_newline_deeper_in_the_tree(self):
        base = self.build("plain")
        inner = os.path.join(base, "a", "sub\ndir")
        os.makedirs(inner)
        with open(os.path.join(inner, "x.bin"), "wb") as fh:
            fh.write(b"\0" * (3 * MB))
        self.assertBothEngines(base)

    def test_a_tab_in_a_directory_name(self):
        self.assertBothEngines(self.build("ta\tbbed"))

    def test_spaces(self):
        self.assertBothEngines(self.build("with space"))

    @unittest.skipUnless(
        andy.encodable("\u043f\u0440\u043e\u0435\u043a\u0442-\u65e5\u672c",
                       type("S", (), {"encoding": sys.getfilesystemencoding()})),
        "this filesystem encoding cannot name such a directory")
    def test_non_ascii(self):
        """cairn 0026. On macOS the filesystem stays UTF-8 whatever the locale
        says, so this runs under LC_ALL=C and used to under-report in silence.
        Where the filesystem encoding really is ASCII the name cannot exist at
        all, and there is nothing to measure or to claim."""
        self.assertBothEngines(self.build("\u043f\u0440\u043e\u0435\u043a\u0442-\u65e5\u672c"))

    def test_the_fallback_is_what_ran(self):
        """Not merely available: the mangled path must go through walk_tree."""
        base = self.build("we\nird")
        with mock.patch.object(andy, "walk_tree", wraps=andy.walk_tree) as spy:
            measure(base, andy.DuMeasurer)
        self.assertTrue(spy.called, "du's output was trusted for a path it cannot name")

    def test_a_clean_tree_does_not_use_the_fallback(self):
        base = self.build("plain")
        with mock.patch.object(andy, "walk_tree", wraps=andy.walk_tree) as spy:
            measure(base, andy.DuMeasurer)
        self.assertFalse(spy.called, "du's output was fine and was thrown away")


class SharedWalks(Tree):
    """cairn 0021. A walk of an outer directory already reads everything
    inside it, so a requested path within it need not be walked again."""

    def setUp(self):
        super().setUp()
        self.fill("outer/top.bin", 1)
        self.fill("outer/inner/a.bin", 4)
        self.fill("outer/inner/deep/b.bin", 2)
        self.fill("outer/other/c.bin", 3)
        self.fill("alone/d.bin", 5)
        self.paths = [os.path.join(self.root, p) for p in
                      ("outer", "outer/inner", "outer/other", "alone")]

    def measure_all(self, engine):
        settled = {}
        engine(4).run(list(self.paths),
                      lambda u: [settled.__setitem__(p, (s, k))
                                 for p, s, k in u if k != "running"],
                      budget=120)
        return settled

    def test_only_the_outermost_are_walked(self):
        outer, covered = andy.DuMeasurer.outermost(self.paths)
        self.assertEqual(sorted(outer),
                         sorted([os.path.join(self.root, "alone"),
                                 os.path.join(self.root, "outer")]))
        self.assertEqual(sorted(covered),
                         sorted([os.path.join(self.root, "outer", "inner"),
                                 os.path.join(self.root, "outer", "other")]))

    def test_an_inner_total_matches_measuring_it_alone(self):
        for engine in ENGINES:
            got = self.measure_all(engine)
            for path in self.paths:
                self.assertEqual(got[path][0], du(path),
                                 f"{engine.__name__}: {os.path.relpath(path, self.root)}")
                self.assertEqual(got[path][1], "done")

    def test_du_spawns_one_process_per_outer_path(self):
        seen = []
        real = subprocess.Popen

        def spy(argv, **kw):
            if argv[:2] == ["du", "-kx"]:
                seen.append(argv[2])
            return real(argv, **kw)

        with mock.patch.object(andy.subprocess, "Popen", spy):
            self.measure_all(andy.DuMeasurer)
        self.assertEqual(sorted(seen),
                         sorted([os.path.join(self.root, "alone"),
                                 os.path.join(self.root, "outer")]),
                         "a path inside another was walked again")

    def test_a_sibling_prefix_is_not_containment(self):
        # outer-2 starts with the same characters as outer but is not inside it
        self.fill("outer-2/e.bin", 2)
        paths = self.paths + [os.path.join(self.root, "outer-2")]
        outer, covered = andy.DuMeasurer.outermost(paths)
        self.assertIn(os.path.join(self.root, "outer-2"), outer)
        self.assertNotIn(os.path.join(self.root, "outer-2"), covered)

    def test_duplicates_are_asked_for_once(self):
        outer, covered = andy.DuMeasurer.outermost(
            [os.path.join(self.root, "alone")] * 3)
        self.assertEqual(len(outer), 1)
        self.assertEqual(covered, {})

    def test_the_walker_does_not_share_walks(self):
        """It accumulates one total per walk and cannot pick a subtree out of
        it, so it measures each path on its own. The numbers still agree."""
        self.assertFalse(andy.Walker.SHARES_WALKS)
        self.assertTrue(andy.DuMeasurer.SHARES_WALKS)

    def test_an_outer_path_that_vanished_settles_what_it_covered(self):
        gone = os.path.join(self.root, "gone")
        paths = [gone, os.path.join(gone, "inner")]
        got = {}
        andy.DuMeasurer(2).run(paths, lambda u: [got.__setitem__(p, (s, k))
                                                 for p, s, k in u], budget=30)
        self.assertEqual(got.get(gone), (0, "done"))
        self.assertEqual(got.get(os.path.join(gone, "inner")), (0, "done"))
