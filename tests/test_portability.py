"""The things that differ between one machine and another: where XDG puts the
caches, whether curses exists, and what the terminal can encode.

Each of these was a real failure. None of them is visible on the author's Mac,
which is the point of testing them here rather than noticing them later.
"""

import importlib.machinery
import importlib.util
import io
import os
import subprocess
import sys
import unittest
from unittest import mock

from andymod import andy, ANDY


def load(env=None, block_curses=False, stdout_encoding=None):
    """Import andy again under a different environment."""
    name = f"andy_env_{len(sys.modules)}"
    loader = importlib.machinery.SourceFileLoader(name, ANDY)
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module

    saved_env = dict(os.environ)
    saved_stdout = sys.stdout
    saved_curses = sys.modules.get("curses")
    try:
        if env is not None:
            os.environ.clear()
            os.environ.update(env)
        if stdout_encoding is not None:
            stream = io.TextIOWrapper(io.BytesIO(), encoding=stdout_encoding)
            sys.stdout = stream
        if block_curses:
            sys.modules["curses"] = None        # import curses -> ImportError
        loader.exec_module(module)
    finally:
        os.environ.clear()
        os.environ.update(saved_env)
        sys.stdout = saved_stdout
        if block_curses:
            if saved_curses is None:
                sys.modules.pop("curses", None)
            else:
                sys.modules["curses"] = saved_curses
    return module


class Xdg(unittest.TestCase):
    """cairn 0010. The three directories XDG exists to move were hardcoded."""

    def env(self, **extra):
        base = {"HOME": andy.HOME, "PATH": os.environ.get("PATH", "")}
        base.update(extra)
        return base

    def test_the_defaults_when_nothing_is_set(self):
        m = load(env=self.env())
        self.assertEqual(m.XDG_CACHE, os.path.join(m.HOME, ".cache"))
        self.assertEqual(m.XDG_CONFIG, os.path.join(m.HOME, ".config"))
        self.assertEqual(m.XDG_DATA, os.path.join(m.HOME, ".local", "share"))
        self.assertEqual(m.XDG_STATE, os.path.join(m.HOME, ".local", "state"))

    def test_each_variable_is_honoured(self):
        m = load(env=self.env(XDG_CACHE_HOME="/mnt/c", XDG_CONFIG_HOME="/mnt/g",
                              XDG_DATA_HOME="/mnt/d", XDG_STATE_HOME="/mnt/s"))
        self.assertEqual((m.XDG_CACHE, m.XDG_CONFIG, m.XDG_DATA, m.XDG_STATE),
                         ("/mnt/c", "/mnt/g", "/mnt/d", "/mnt/s"))

    def test_a_relative_or_empty_value_is_ignored(self):
        # the spec says a relative value is invalid; an empty one is a shell
        # leaving a variable set to nothing
        for bad in ("", "relative/cache", "./cache"):
            m = load(env=self.env(XDG_CACHE_HOME=bad))
            self.assertEqual(m.XDG_CACHE, os.path.join(m.HOME, ".cache"), repr(bad))

    def test_a_trailing_slash_does_not_double_up(self):
        m = load(env=self.env(XDG_CACHE_HOME="/mnt/c/"))
        self.assertEqual(m.XDG_CACHE, "/mnt/c")

    def test_catalog_paths_move_with_the_variables(self):
        m = load(env=self.env(XDG_CACHE_HOME="/mnt/c", XDG_DATA_HOME="/mnt/d"))
        paths = {s.label: s.path for s in m.CATALOG}
        self.assertEqual(paths["other in ~/.cache"], "/mnt/c")
        self.assertTrue(paths["Zig cache"].startswith("/mnt/c/"), paths["Zig cache"])
        self.assertTrue(any(p.startswith("/mnt/d/") for p in paths.values()),
                        "XDG_DATA_HOME moved nothing")

    def test_expand_globs_move_too(self):
        m = load(env=self.env(XDG_CACHE_HOME="/mnt/c"))
        for spec in m.CATALOG:
            if spec.expand and spec.path.startswith("/mnt/c"):
                self.assertTrue(spec.expand.startswith("/mnt/c"), spec.label)

    def test_the_scan_cache_moves_with_it(self):
        m = load(env=self.env(XDG_CACHE_HOME="/mnt/c"))
        self.assertEqual(m.CACHE_DIR, "/mnt/c/andy")

    def test_the_longest_prefix_wins(self):
        # ~/.local/share must not be rewritten as ~/.local plus a suffix
        m = load(env=self.env(XDG_DATA_HOME="/mnt/d", XDG_STATE_HOME="/mnt/s"))
        self.assertEqual(m.xdg_path(os.path.join(m.HOME, ".local", "share", "pnpm")),
                         "/mnt/d/pnpm")
        self.assertEqual(m.xdg_path(os.path.join(m.HOME, ".local", "state", "nvim")),
                         "/mnt/s/nvim")

    def test_a_path_outside_the_xdg_roots_is_untouched(self):
        m = load(env=self.env(XDG_CACHE_HOME="/mnt/c"))
        self.assertEqual(m.xdg_path("/usr/lib/thing"), "/usr/lib/thing")
        self.assertEqual(m.xdg_path(os.path.join(m.HOME, ".rustup")),
                         os.path.join(m.HOME, ".rustup"))


class NoCurses(unittest.TestCase):
    """cairn 0011. Importing curses at module scope made --json need a terminal."""

    def test_the_module_imports_without_curses(self):
        m = load(block_curses=True)
        self.assertIsNone(m.curses)
        self.assertTrue(m.CATALOG, "the catalog did not survive the missing import")

    def test_every_non_interactive_mode_still_works(self):
        m = load(block_curses=True)
        model = m.Model()
        model.category("x").children.append(
            m.Node(label="a", path="/a", measured=5 * 2 ** 20))
        model.recompute()
        for fn, args in ((m.print_report, (12,)), (m.print_tree, (0,)),
                         (m.print_commands, (0,))):
            out = io.StringIO()
            fn(model, m.Ink(False), *args, out=out)
            self.assertTrue(out.getvalue())
        self.assertEqual(m.to_json(model)["mapped_bytes"], 5 * 2 ** 20)

    def test_interactive_mode_says_so_instead_of_crashing(self):
        m = load(block_curses=True)
        err = io.StringIO()
        with mock.patch.object(m.sys, "stderr", err):
            code = m.main(["-i"])
        self.assertEqual(code, 2)
        self.assertIn("curses", err.getvalue())

    @unittest.skipIf(andy.curses is None, "this Python has no curses either")
    def test_with_curses_present_nothing_changes(self):
        self.assertIsNotNone(andy.curses)

    def test_the_mouse_constants_moved_off_the_class_body(self):
        # they are what forced curses to be imported before anything could run
        for name in ("WHEEL_DOWN", "CLICK", "RIGHT_CLICK"):
            self.assertFalse(hasattr(andy.Tui, name),
                             f"Tui.{name} is evaluated at import time again")


class Glyphs(unittest.TestCase):
    """cairn 0012. A C locale with PEP 538 coercion off crashed the report."""

    def test_utf8_keeps_the_drawing_characters(self):
        m = load(stdout_encoding="utf-8")
        self.assertTrue(m.UNICODE)
        self.assertEqual(m.FULL_CELL, "█")
        self.assertEqual(m.ELLIPSIS, "…")

    def test_ascii_falls_back(self):
        m = load(stdout_encoding="ascii")
        self.assertFalse(m.UNICODE)
        self.assertEqual(m.FULL_CELL, "#")
        self.assertEqual(m.ELLIPSIS, "...")

    def test_latin_1_also_falls_back(self):
        # · encodes in latin-1 but the block characters do not, so the
        # whole set has to be decided together
        self.assertFalse(load(stdout_encoding="latin-1").UNICODE)

    def test_a_stream_with_no_encoding_is_assumed_hostile(self):
        self.assertFalse(andy.encodable("█", io.StringIO()))

    def test_an_unknown_encoding_does_not_raise(self):
        stream = mock.Mock(encoding="not-a-real-codec")
        self.assertFalse(andy.encodable("x", stream))

    def test_the_ascii_report_is_pure_ascii(self):
        m = load(stdout_encoding="ascii")
        model = m.Model()
        model.disk = (500 * 2 ** 30, 300 * 2 ** 30, 200 * 2 ** 30)
        cat = model.category(m.PACKAGES)
        cat.children.append(m.Node(label="pnpm store", path="/h/p",
                                   measured=3 * 2 ** 30, cmd="pnpm store prune"))
        cat.children.append(m.Node(label="stuck", path="/h/s", measured=2 ** 30,
                                   blocked=True, partial=True))
        model.recompute()
        for fn, args in ((m.print_report, (12,)), (m.print_tree, (0,)),
                         (m.print_commands, (0,))):
            out = io.StringIO()
            fn(model, m.Ink(False), *args, out=out)
            text = out.getvalue()
            self.assertTrue(text.isascii(),
                            [c for c in text if not c.isascii()])

    def test_trimming_still_fits_the_width_in_ascii(self):
        m = load(stdout_encoding="ascii")
        text = "~/Code/some/deeply/nested/project/node_modules"
        for width in range(0, 40):
            self.assertLessEqual(len(m.shorten(text, width)), width, width)
            self.assertLessEqual(len(m.clip_end(text, width)), width, width)

    def test_the_bar_still_fills_its_width_in_ascii(self):
        m = load(stdout_encoding="ascii")
        for fraction in (0.0, 0.1, 0.5, 0.99, 1.0):
            self.assertEqual(len(m.bar(fraction, 12)), 12, fraction)

    def test_no_drawing_character_is_written_inline(self):
        """Every glyph goes through the table, so both sets stay in step."""
        with open(ANDY, encoding="utf-8") as fh:
            source = fh.read()
        table_end = source.index("def human(")
        body = source[table_end:]
        stray = sorted({c for c in body if ord(c) > 0x2000})
        self.assertEqual(stray, [], f"glyphs written inline: {stray}")


class RealProcess(unittest.TestCase):
    """The same three, end to end, because import-time behaviour is the point."""

    def setUp(self):
        import shutil as _shutil
        import tempfile
        self.home = tempfile.mkdtemp(prefix="andy-home-")
        self.addCleanup(_shutil.rmtree, self.home, ignore_errors=True)

    def run_andy(self, *args, env_extra=None):
        env = dict(os.environ, HOME=self.home,
                   DOCKER_HOST="unix:///nonexistent/andy.sock", NO_COLOR="1")
        # the parent's XDG settings would otherwise point the child back at the
        # real home and make these assertions depend on the developer's machine
        for name in ("XDG_CACHE_HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME",
                     "XDG_STATE_HOME"):
            env.pop(name, None)
        env.update(env_extra or {})
        return subprocess.run([sys.executable, ANDY, "--fresh", "--no-projects",
                               *args], capture_output=True, text=True,
                              timeout=180, env=env)

    def test_a_c_locale_with_coercion_defeated(self):
        env = {"PYTHONCOERCECLOCALE": "0", "PYTHONUTF8": "0",
               "LC_ALL": "C", "LANG": "C"}
        for args in (("-n", "3"), ("--tree",), ("--commands",), ("--json",)):
            p = self.run_andy(*args, env_extra=env)
            self.assertEqual(p.returncode, 0, f"{args}: {p.stderr[-400:]}")
            self.assertNotIn("UnicodeEncodeError", p.stderr)

    def test_relocated_xdg_directories_are_looked_in(self):
        cache = os.path.join(self.home, "elsewhere")
        os.makedirs(os.path.join(cache, "go-build"), exist_ok=True)
        with open(os.path.join(cache, "go-build", "blob"), "wb") as fh:
            fh.write(b"\0" * (12 << 20))
        p = self.run_andy("--json", env_extra={"XDG_CACHE_HOME": cache})
        self.assertEqual(p.returncode, 0, p.stderr[-400:])
        self.assertIn(cache, p.stdout,
                      "a 12M cache in a relocated XDG_CACHE_HOME was not found")
        self.assertNotIn(os.path.join(self.home, ".cache"), p.stdout,
                         "andy looked in ~/.cache anyway")

    def test_a_home_that_does_not_exist(self):
        """cairn 0018. Containers and systemd units hand over homes that were
        never created; andy used to die on the first statvfs."""
        missing = os.path.join(self.home, "never-created")
        for args in (("-n", "3"), ("--json",)):
            p = self.run_andy(*args, env_extra={"HOME": missing})
            self.assertEqual(p.returncode, 0, f"{args}: {p.stderr[-400:]}")
            self.assertNotIn("Traceback", p.stderr)


if __name__ == "__main__":
    unittest.main()
