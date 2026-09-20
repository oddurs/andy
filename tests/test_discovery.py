"""Finding project artifacts on a real filesystem.

These build actual trees rather than mocking `find`, because the thing most
likely to be wrong is the `find` expression itself.
"""

import os
import shutil
import tempfile
import unittest
from unittest import mock

from andymod import andy


class Tree(unittest.TestCase):
    def setUp(self):
        self.root = os.path.realpath(tempfile.mkdtemp(prefix="andy-test-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def mkdir(self, *parts):
        path = os.path.join(self.root, *parts)
        os.makedirs(path, exist_ok=True)
        return path

    def touch(self, *parts):
        path = os.path.join(self.root, *parts)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w").close()
        return path


class HasMarker(Tree):
    def test_a_known_manifest(self):
        self.touch("proj", "package.json")
        self.assertTrue(andy.has_marker(os.path.join(self.root, "proj")))

    def test_an_extension_marker(self):
        self.touch("proj", "Thing.csproj")
        self.assertTrue(andy.has_marker(os.path.join(self.root, "proj")))

    def test_nothing(self):
        self.mkdir("proj")
        self.assertFalse(andy.has_marker(os.path.join(self.root, "proj")))

    def test_a_directory_that_is_not_there(self):
        self.assertFalse(andy.has_marker(os.path.join(self.root, "nope")))


class FindArtifacts(Tree):
    def found(self):
        return {os.path.relpath(p, self.root): kind
                for p, kind in andy.find_artifacts([self.root])}

    def test_strict_names_count_anywhere(self):
        self.mkdir("anything", "node_modules")
        self.mkdir("anything", ".venv")
        self.assertEqual(self.found(), {
            "anything/node_modules": "node_modules",
            "anything/.venv": "python venv",
        })

    def test_ambiguous_names_need_a_build_marker(self):
        self.touch("proj", "Cargo.toml")
        self.mkdir("proj", "target")
        self.mkdir("plain", "target")
        found = self.found()
        self.assertEqual(found.get("proj/target"), "cargo/maven target")
        self.assertNotIn("plain/target", found,
                         "a `target` with no manifest beside it is somebody's data")

    def test_git_repositories(self):
        self.mkdir("repo", ".git")
        self.assertEqual(self.found().get("repo/.git"), ".git")

    def test_nested_artifacts_are_pruned(self):
        self.mkdir("proj", "node_modules", "pkg", "node_modules")
        found = self.found()
        self.assertIn("proj/node_modules", found)
        self.assertEqual(len(found), 1,
                         "an inner node_modules is already inside the outer one")

    def test_symlinks_are_never_followed_or_reported(self):
        real = self.mkdir("real", "node_modules")
        os.symlink(os.path.join(self.root, "real"), os.path.join(self.root, "link"))
        found = self.found()
        self.assertIn("real/node_modules", found)
        self.assertNotIn("link/node_modules", found)

    def test_no_roots(self):
        self.assertEqual(andy.find_artifacts([]), [])

    def test_ambiguous_names_added_in_1_1(self):
        self.touch("swift", "Package.swift")
        self.mkdir("swift", ".build")
        self.touch("web", "package.json")
        self.mkdir("web", ".cache")
        self.mkdir("plain", ".cache")       # no manifest: somebody's own data
        found = self.found()
        self.assertEqual(found.get("swift/.build"), "swift build")
        self.assertEqual(found.get("web/.cache"), "cache (project)")
        self.assertNotIn("plain/.cache", found)

    def test_strict_names_added_in_1_1(self):
        for name, kind in ((".wrangler", "wrangler"), ("storybook-static", "storybook"),
                           (".idea", "jetbrains (project)"), ("cmake-build-debug", "cmake")):
            self.mkdir("proj", name)
        found = self.found()
        self.assertEqual(found.get("proj/.wrangler"), "wrangler")
        self.assertEqual(found.get("proj/storybook-static"), "storybook")
        self.assertEqual(found.get("proj/.idea"), "jetbrains (project)")
        self.assertEqual(found.get("proj/cmake-build-debug"), "cmake")

    def test_depth_is_bounded(self):
        deep = os.path.join(*(["x"] * 12), "node_modules")
        self.mkdir(*deep.split(os.sep))
        self.assertEqual(andy.find_artifacts([self.root], depth=4), [])


class DedupeDirs(Tree):
    def test_repeats_are_dropped(self):
        a = self.mkdir("a")
        self.assertEqual(andy.dedupe_dirs([a, a]), [a])

    def test_a_directory_inside_another_is_dropped(self):
        a = self.mkdir("a")
        self.mkdir("a", "b")
        self.assertEqual(andy.dedupe_dirs([a, os.path.join(a, "b")]), [a])

    def test_a_symlink_resolves_to_its_target(self):
        a = self.mkdir("a")
        link = os.path.join(self.root, "alias")
        os.symlink(a, link)
        self.assertEqual(andy.dedupe_dirs([a, link]), [a])

    def test_missing_directories_are_skipped(self):
        self.assertEqual(andy.dedupe_dirs([os.path.join(self.root, "nope")]), [])

    def test_files_are_not_roots(self):
        f = self.touch("a-file")
        self.assertEqual(andy.dedupe_dirs([f]), [])


class Labels(Tree):
    def test_a_project_label_is_relative_to_its_root(self):
        self.assertEqual(
            andy.project_label("/r/repo/node_modules", ["/r"]), "repo/node_modules")

    def test_a_long_path_is_elided_in_the_middle(self):
        label = andy.project_label("/r/a/b/c/d/e/node_modules", ["/r"])
        self.assertIn(andy.ELLIPSIS, label)
        self.assertTrue(label.startswith("a/b"))
        self.assertTrue(label.endswith("node_modules"))

    def test_a_path_outside_every_root_falls_back_to_tilde(self):
        self.assertEqual(andy.project_label("/elsewhere/x", ["/r"]), "/elsewhere/x")

    def test_the_longest_matching_root_wins(self):
        self.assertEqual(
            andy.project_label("/r/sub/p/target", ["/r", "/r/sub"]), "p/target")

    def test_name_for_without_a_namer_is_the_basename(self):
        self.assertEqual(andy.name_for("/a/b/c", None), "c")

    def test_name_for_a_simulator_without_a_plist_degrades(self):
        d = self.mkdir("DEAD-BEEF")
        self.assertEqual(andy.name_for(d, "simulator"), "DEAD-BEEF")

    def test_name_for_a_simulator_reads_the_plist(self):
        import plistlib
        d = self.mkdir("DEAD-BEEF")
        with open(os.path.join(d, "device.plist"), "wb") as fh:
            plistlib.dump({"name": "iPhone 17",
                           "runtime": "com.apple.CoreSimulator.SimRuntime.iOS-26-0"}, fh)
        self.assertEqual(andy.name_for(d, "simulator"),
                         f"iPhone 17 {andy.DOT} iOS 26 0")


class Parsing(unittest.TestCase):
    def test_docker_sizes(self):
        self.assertEqual(andy.parse_docker_size("0B"), 0)
        self.assertEqual(andy.parse_docker_size("1.5GB"), 1500000000)
        self.assertEqual(andy.parse_docker_size("2GiB"), 2 * 2 ** 30)
        self.assertEqual(andy.parse_docker_size("512MB"), 512000000)

    def test_docker_nonsense(self):
        self.assertEqual(andy.parse_docker_size(""), 0)
        self.assertEqual(andy.parse_docker_size("N/A"), 0)


if __name__ == "__main__":
    unittest.main()


class Catalog(unittest.TestCase):
    """The catalog is data, and the rules about that data are what matter."""

    def test_every_entry_has_a_note(self):
        for spec in andy.CATALOG:
            self.assertTrue(spec.note.strip(), f"{spec.label} says nothing about itself")

    def test_every_entry_has_a_known_category_and_safety(self):
        categories = {andy.CONTAINERS, andy.PROJECTS, andy.PACKAGES, andy.APPLE,
                      andy.TOOLCHAINS, andy.BUILD, andy.MODELS, andy.APPS, andy.REPOS}
        for spec in andy.CATALOG:
            self.assertIn(spec.cat, categories, spec.label)
            self.assertIn(spec.safety, (andy.SAFE, andy.REBUILD, andy.REVIEW), spec.label)

    def test_labels_are_unique(self):
        labels = [s.label for s in andy.CATALOG]
        self.assertEqual(len(labels), len(set(labels)),
                         sorted(l for l in labels if labels.count(l) > 1))

    def test_paths_are_unique(self):
        paths = [s.path for s in andy.CATALOG]
        self.assertEqual(len(paths), len(set(paths)),
                         sorted(p for p in paths if paths.count(p) > 1))

    def test_expand_globs_are_expanded(self):
        """cairn 0016. glob.glob does not expand `~`, so 20 of the 21 specs
        using `expand` matched nothing and itemisation never once ran."""
        for spec in andy.CATALOG:
            if spec.expand:
                self.assertFalse(spec.expand.startswith("~"),
                                 f"{spec.label}: {spec.expand} will match nothing")
                self.assertTrue(spec.expand.startswith("/"), spec.label)

    def test_an_expand_glob_sits_under_its_own_path(self):
        for spec in andy.CATALOG:
            if spec.expand:
                self.assertTrue(spec.expand.startswith(spec.path + os.sep),
                                f"{spec.label}: {spec.expand} is not under {spec.path}")

    def test_paths_are_absolute(self):
        for spec in andy.CATALOG:
            self.assertTrue(spec.path.startswith("/"), f"{spec.label}: {spec.path}")

    def test_a_reclaim_command_never_removes_a_home_directory_wholesale(self):
        for spec in andy.CATALOG:
            self.assertNotIn("rm -rf ~ ", spec.cmd, spec.label)
            self.assertNotIn("rm -rf /\n", spec.cmd + "\n", spec.label)

    def test_nothing_irreplaceable_is_rated_safe(self):
        """`safe` means it regenerates itself. Anything holding model weights,
        virtual environments or editor state does not."""
        for spec in andy.CATALOG:
            if spec.safety != andy.SAFE:
                continue
            self.assertNotEqual(spec.cat, andy.MODELS,
                                f"{spec.label}: weights are a download, not a rebuild")
            self.assertNotIn("envs", spec.path, spec.label)

    def test_artifact_kinds_all_have_a_safety(self):
        kinds = set(andy.ARTIFACTS_STRICT.values()) | set(andy.ARTIFACTS_AMBIGUOUS.values())
        for kind in andy.ARTIFACT_SAFETY:
            self.assertIn(kind, kinds, f"{kind} is rated but never produced")
        for kind in kinds:
            safety = andy.ARTIFACT_SAFETY.get(kind, andy.REBUILD)
            self.assertIn(safety, (andy.SAFE, andy.REBUILD, andy.REVIEW), kind)

    def test_itemising_actually_produces_children(self):
        """The end of 0016: build a tree the glob matches and watch it split."""
        root = os.path.realpath(tempfile.mkdtemp(prefix="andy-expand-"))
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        for name in ("stable", "nightly", "1.88"):
            os.makedirs(os.path.join(root, name))
        spec = andy.S(andy.TOOLCHAINS, "toolchains", root, "note",
                      expand=os.path.join(root, "*"))
        model = andy.Model()
        scanner = andy.Scanner(model, [], include_projects=False, use_cache=False)
        with mock.patch.object(andy, "CATALOG", [spec]):
            tasks = scanner._build_catalog({})
        labels = {n.label for n in tasks}
        self.assertEqual(labels, {"toolchains", "stable", "nightly", "1.88"})
        parent = next(n for n in tasks if n.label == "toolchains")
        self.assertEqual(len(parent.children), 3)
        self.assertTrue(all(c.detail for c in parent.children),
                        "a breakdown was not marked as one")

    def test_pruned_names_are_names_we_classify(self):
        known = set(andy.ARTIFACTS_STRICT) | set(andy.ARTIFACTS_AMBIGUOUS)
        for name in andy.AMBIGUOUS_PRUNE:
            self.assertIn(name, andy.ARTIFACTS_AMBIGUOUS,
                          f"{name} is pruned by find but never classified")
        self.assertTrue(known)
