"""macOS and Linux.

The catalog is chosen at import time from `sys.platform`, so the Linux half is
tested by importing the file a second time with the platform swapped. That is
worth doing from a Mac: most of what could break on Linux breaks at import.
"""

import importlib.machinery
import importlib.util
import os
import sys
import unittest
from unittest import mock

from andymod import andy, ANDY


def load_as(platform):
    """Import andy again, as if running on `platform`."""
    name = f"andy_as_{platform}"
    loader = importlib.machinery.SourceFileLoader(name, ANDY)
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    real = sys.platform
    try:
        sys.platform = platform
        loader.exec_module(module)
    finally:
        sys.platform = real
    return module


LINUX = load_as("linux")
MAC = load_as("darwin")


class Tagging(unittest.TestCase):
    def test_apple_paths_are_tagged_without_being_told(self):
        spec = andy.S(andy.APPS, "x", "~/Library/Caches/whatever", "note")
        self.assertEqual(spec.only, "darwin")

    def test_portable_paths_are_untagged(self):
        self.assertIsNone(andy.S(andy.PACKAGES, "x", "~/.cache/whatever", "note").only)

    def test_an_explicit_tag_is_not_overridden(self):
        spec = andy.S(andy.APPS, "x", "~/Library/Caches/x", "note", only="linux")
        self.assertEqual(spec.only, "linux")


class Catalogs(unittest.TestCase):
    def test_each_platform_gets_only_its_own_entries(self):
        for module, platform in ((LINUX, "linux"), (MAC, "darwin")):
            for spec in module.CATALOG:
                self.assertIn(spec.only, (None, platform),
                              f"{platform}: {spec.label} is tagged {spec.only}")

    def test_linux_has_no_apple_paths(self):
        self.assertEqual([s.label for s in LINUX.CATALOG if "/Library/" in s.path], [])

    def test_linux_has_no_xcode_category(self):
        self.assertEqual([s.label for s in LINUX.CATALOG if s.cat == LINUX.APPLE], [])

    def test_both_platforms_cover_the_same_ground(self):
        """Every category that means anything off a Mac exists on both."""
        portable = {LINUX.PACKAGES, LINUX.TOOLCHAINS, LINUX.BUILD,
                    LINUX.MODELS, LINUX.APPS, LINUX.CONTAINERS}
        for category in portable:
            self.assertTrue([s for s in LINUX.CATALOG if s.cat == category],
                            f"Linux knows nothing about {category}")

    def test_linux_does_not_list_var_lib_docker(self):
        """It needs root to measure; `docker system df` is used instead."""
        self.assertEqual([s.label for s in LINUX.CATALOG
                          if s.path.startswith("/var/lib/docker")], [])

    def test_the_shared_entries_really_are_shared(self):
        linux = {s.path for s in LINUX.CATALOG}
        mac = {s.path for s in MAC.CATALOG}
        self.assertTrue(len(linux & mac) > 80,
                        "the portable half of the catalog has come apart")

    def test_labels_stay_unique_on_each_platform(self):
        for module, name in ((LINUX, "linux"), (MAC, "darwin")):
            labels = [s.label for s in module.CATALOG]
            duplicated = sorted({x for x in labels if labels.count(x) > 1})
            self.assertEqual(duplicated, [], f"{name}: {duplicated}")


    def test_no_untagged_entry_uses_an_apple_only_path(self):
        """The auto-tag keys off /Library/. Paths like ~/Applications or
        /private/var are just as Apple-only and have to be tagged by hand --
        an untagged one turns up on Linux, where it cannot exist."""
        apple = ("/Applications/", "/private/", "/System/", "/Library/")
        for spec in MAC.CATALOG:
            if spec.only is not None:
                continue
            # a path under HOME is portable by construction; ~ expands
            # differently on each platform and that is the point
            tail = (spec.path[len(andy.HOME):] if spec.path.startswith(andy.HOME)
                    else spec.path)
            for shape in apple:
                self.assertNotIn(shape, tail,
                                 f"{spec.label} ({spec.path}) is untagged")


class Wording(unittest.TestCase):
    def test_no_apple_wording_reaches_a_linux_screen(self):
        text = repr(LINUX.HELP) + " ".join(
            s.note + s.cmd + s.label for s in LINUX.CATALOG)
        for word in ("Finder", "Xcode", "simulator", "Simulator", "CoreSimulator"):
            self.assertNotIn(word, text, f"{word} on a Linux screen")

    def test_mac_still_says_finder(self):
        self.assertEqual(MAC.FILE_MANAGER, "Finder")
        self.assertIn("Finder", repr(MAC.HELP))


class Clipboard(unittest.TestCase):
    def test_macos_uses_pbcopy(self):
        self.assertEqual([c[0] for c in MAC.CLIPBOARDS], ["pbcopy"])

    def test_linux_tries_wayland_before_x11(self):
        self.assertEqual([c[0] for c in LINUX.CLIPBOARDS], ["wl-copy", "xclip", "xsel"])

    def test_nothing_installed_is_a_failure_not_a_crash(self):
        with mock.patch.object(LINUX.shutil, "which", return_value=None):
            self.assertIs(LINUX.clip("text"), False)

    def test_the_first_tool_that_works_wins(self):
        calls = []

        def which(name):
            return None if name == "wl-copy" else "/usr/bin/" + name

        def run(argv, **kw):
            calls.append(argv[0])
            return mock.Mock(returncode=0)

        with mock.patch.object(LINUX.shutil, "which", which), \
             mock.patch.object(LINUX.subprocess, "run", run):
            self.assertIs(LINUX.clip("text"), True)
        self.assertEqual(calls, ["xclip"], "wl-copy was absent and should be skipped")

    def test_a_tool_that_fails_falls_through_to_the_next(self):
        results = {"xclip": 1, "xsel": 0}
        tried = []

        def run(argv, **kw):
            tried.append(argv[0])
            return mock.Mock(returncode=results[argv[0]])

        with mock.patch.object(LINUX.shutil, "which",
                               lambda n: None if n == "wl-copy" else "/usr/bin/" + n), \
             mock.patch.object(LINUX.subprocess, "run", run):
            self.assertIs(LINUX.clip("text"), True)
        self.assertEqual(tried, ["xclip", "xsel"])


class Docker(unittest.TestCase):
    """On macOS the daemon's own numbers duplicate the VM disk. On Linux they
    are the only numbers there are."""

    ROWS = [("images", 4 * 2 ** 30, "docker image prune -a", andy.REBUILD, "3 total")]

    def scan(self, module, tmp):
        import shutil as _shutil
        import tempfile
        model = module.Model()
        scanner = module.Scanner(model, [], include_projects=False, use_cache=False)
        cache = tempfile.mkdtemp(prefix="andy-platcache-")
        self.addCleanup(_shutil.rmtree, cache, ignore_errors=True)
        with mock.patch.object(module, "CATALOG", []), \
             mock.patch.object(module, "CACHE_DIR", cache), \
             mock.patch.object(module, "CACHE_FILE",
                               os.path.join(cache, "scan.json")), \
             mock.patch.object(module, "docker_breakdown", lambda: self.ROWS):
            scanner.start()
            scanner.join(60)
        return model

    def test_macos_treats_the_breakdown_as_a_duplicate_view(self):
        model = self.scan(MAC, None)
        self.assertEqual(model.total, 0, "docker's view of the VM disk was counted")
        live = next(n for n in model.walk() if n.kind == "docker" and n.children)
        self.assertTrue(live.informational)
        self.assertIn("live breakdown", live.label)

    def test_linux_counts_it(self):
        model = self.scan(LINUX, None)
        self.assertEqual(model.total, 4 * 2 ** 30,
                         "on Linux this is the only figure available")
        live = next(n for n in model.walk() if n.kind == "docker" and n.children)
        self.assertFalse(live.informational)
        self.assertNotIn("live breakdown", live.label)


class JsonHonesty(unittest.TestCase):
    def test_the_platform_is_recorded(self):
        doc = andy.to_json(andy.Model())
        self.assertEqual(doc["platform"], andy.PLATFORM)
        self.assertGreater(doc["locations_known"], 50)


if __name__ == "__main__":
    unittest.main()
