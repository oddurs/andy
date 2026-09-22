"""The config file. Something a person wrote, so nothing in it can stop andy
starting: whatever is wrong is named, with its line, and the default stands."""

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from andymod import andy, ANDY


class Files(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="andy-config-")
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

    def write(self, text, name="config"):
        path = os.path.join(self.dir, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path

    def load(self, text):
        return andy.load_config(self.write(text))


class Reading(Files):
    def test_no_file_is_the_defaults_and_no_complaint(self):
        s = andy.load_config(os.path.join(self.dir, "absent"))
        # asked for explicitly, so its absence is worth a word
        self.assertEqual(len(s.problems), 1)
        for name, (default, _, _) in andy.SETTINGS.items():
            self.assertEqual(s[name], default)

    def test_the_default_path_follows_xdg(self):
        self.assertEqual(andy.CONFIG_FILE,
                         os.path.join(andy.XDG_CONFIG, "andy", "config"))

    def test_flat_keys_at_the_top_like_ghostty(self):
        s = self.load("theme = mono\ntop = 5\n")
        self.assertEqual((s["theme"], s["top"]), ("mono", 5))
        self.assertEqual(s.problems, [])

    def test_an_explicit_andy_section_works_too(self):
        s = self.load("[andy]\ntop = 7\n")
        self.assertEqual(s["top"], 7)

    def test_comments_whole_line_and_trailing(self):
        s = self.load("# a note\nmin = 50M   # the small stuff\n; another\n")
        self.assertEqual(s["min"], "50M")
        self.assertEqual(s.problems, [])

    def test_every_kind_of_value(self):
        s = self.load('mouse = no\ndetail = off\nprojects = yes\ntop = 20\n'
                      'min = 1.5G\nengine = walk\nroots = ~/src "~/My Projects"\n')
        self.assertEqual(s["mouse"], False)
        self.assertEqual(s["detail"], False)
        self.assertEqual(s["projects"], True)
        self.assertEqual(s["top"], 20)
        self.assertEqual(s["min"], "1.5G")
        self.assertEqual(s["engine"], "walk")
        self.assertEqual(s["roots"], [os.path.expanduser("~/src"),
                                      os.path.expanduser("~/My Projects")])
        self.assertEqual(s.problems, [])

    def test_where_each_value_came_from(self):
        s = self.load("top = 3\n")
        self.assertEqual(s.sources["top"], "config")
        self.assertEqual(s.sources["min"], "default")

    def test_colour_is_accepted_for_color(self):
        s = self.load("colour = no\n")
        self.assertEqual(s["color"], False)
        self.assertEqual(s.problems, [])


class Mistakes(Files):
    """Every one of these warns, names where, and carries on."""

    def test_a_bad_value_keeps_the_default_and_names_the_line(self):
        s = self.load("theme = mono\ntop = lots\n")
        self.assertEqual(s["top"], 12)
        self.assertEqual(s["theme"], "mono", "one bad line cost the good ones")
        self.assertTrue(any("line 2" in p and "whole number" in p for p in s.problems),
                        s.problems)

    def test_each_kind_of_bad_value(self):
        for text, fragment in (("mouse = maybe", "yes or no"),
                               ("top = -1", "negative"),
                               ("min = huge", "a size"),
                               ("engine = rust", "du or walk"),
                               ('roots = "unclosed', "roots")):
            s = self.load(text + "\n")
            self.assertTrue(any(fragment in p for p in s.problems), (text, s.problems))

    def test_an_unknown_setting_lists_the_real_ones(self):
        s = self.load("colours = no\n")
        self.assertTrue(any("'colours' is not a setting" in p and "color" in p
                            for p in s.problems), s.problems)

    def test_an_unknown_section(self):
        s = self.load("[display]\nx = 1\n")
        self.assertTrue(any("[display]" in p for p in s.problems))

    def test_a_file_that_does_not_parse_names_its_line(self):
        s = self.load("top = 3\n[unclosed\n")
        self.assertTrue(any("line 2" in p for p in s.problems), s.problems)
        self.assertEqual(s["top"], 12, "a file that did not parse half-applied")

    def test_a_custom_theme_may_not_replace_a_builtin(self):
        s = self.load("[theme terminal]\ninteractive = red\n")
        self.assertNotIn("terminal", s.themes)
        self.assertTrue(any("built-in" in p for p in s.problems))

    def test_a_broken_theme_is_reported_even_when_not_in_use(self):
        s = self.load("theme = terminal\n[theme mine]\nsafe = chartreuse\n")
        self.assertTrue(any("chartreuse" in p for p in s.problems), s.problems)

    def test_an_unreadable_file(self):
        path = self.write("top = 3\n")
        os.chmod(path, 0)
        self.addCleanup(os.chmod, path, 0o644)
        if os.access(path, os.R_OK):
            self.skipTest("running as a user who can read anything")
        s = andy.load_config(path)
        self.assertTrue(s.problems)
        self.assertEqual(s["top"], 12)


class Themes(Files):
    def test_a_theme_section_is_captured(self):
        s = self.load("[theme mine]\ninherit = classic\nreview = magenta\n")
        self.assertEqual(s.themes["mine"], {"inherit": "classic", "review": "magenta"})
        table, problems = andy.resolve_theme("mine", s.themes)
        self.assertEqual((table["review"], table["map"]), ("magenta", "shade"))


class Precedence(Files):
    """A flag beats the file; the file beats the default; a flag you did not
    pass changes nothing."""

    def settle(self, text, argv):
        return andy.apply_flags(self.load(text), andy.parse_args(argv))

    def test_a_flag_beats_the_file(self):
        s = self.settle("theme = mono\ntop = 5\n", ["--theme", "classic", "-n", "2"])
        self.assertEqual((s["theme"], s["top"]), ("classic", 2))
        self.assertEqual(s.sources["theme"], "flag")

    def test_an_unpassed_flag_leaves_the_file_alone(self):
        s = self.settle("theme = mono\nmouse = no\nengine = walk\n", [])
        self.assertEqual((s["theme"], s["mouse"], s["engine"]), ("mono", False, "walk"))
        self.assertEqual(s.sources["mouse"], "config")

    def test_roots_on_the_command_line_replace_the_files(self):
        s = self.settle("roots = ~/src\n", ["/tmp"])
        self.assertEqual(s["roots"], ["/tmp"])

    def test_the_negative_flags(self):
        s = self.settle("", ["--no-mouse", "--no-projects", "--no-color", "--walk"])
        self.assertEqual((s["mouse"], s["projects"], s["color"], s["engine"]),
                         (False, False, False, "walk"))


class ShowConfig(Files):
    def render(self, text, argv=()):
        s = andy.apply_flags(self.load(text), andy.parse_args(list(argv)))
        out = io.StringIO()
        andy.print_settings(s, [], out=out)
        return out.getvalue()

    def test_every_setting_is_listed_with_its_source(self):
        text = self.render("top = 5\n", ["--theme", "mono"])
        for name in andy.SETTINGS:
            self.assertIn(name, text)
        self.assertRegex(text, r"(?m)^top\s+= 5 .*\(config\)")
        self.assertRegex(text, r"(?m)^theme\s+= mono .*\(flag\)")

    def test_defaults_are_commented_out(self):
        text = self.render("top = 5\n")
        self.assertRegex(text, r"(?m)^# min\s+= 10M")
        self.assertRegex(text, r"(?m)^top\s+= 5")

    def test_it_is_a_config_file_that_reads_back_the_same(self):
        """So `andy --show-config > ~/.config/andy/config` is a starting point."""
        original = ('theme = mine\ntop = 5\nroots = ~/src "~/My Projects"\n'
                    '[theme mine]\ninherit = classic\nreview = magenta\n')
        again = andy.load_config(self.write(self.render(original), "round"))
        first = self.load(original)
        self.assertEqual(again.problems, [])
        for name in andy.SETTINGS:
            self.assertEqual(again[name], first[name], name)
        self.assertEqual(again.themes, first.themes)

    def test_it_lists_the_themes_there_are(self):
        text = self.render("[theme mine]\nsafe = blue\n")
        self.assertIn("terminal, mono, classic, mine", text)


class EndToEnd(Files):
    def run_andy(self, *args):
        env = dict(os.environ, HOME=self.dir, NO_COLOR="1",
                   XDG_CACHE_HOME=os.path.join(self.dir, "cache"),
                   XDG_CONFIG_HOME=os.path.join(self.dir, "xdg"),
                   DOCKER_HOST="unix:///nonexistent/andy.sock")
        return subprocess.run([sys.executable, ANDY, *args], capture_output=True,
                              text=True, timeout=180, env=env)

    def test_the_file_is_found_where_xdg_says(self):
        os.makedirs(os.path.join(self.dir, "xdg", "andy"))
        with open(os.path.join(self.dir, "xdg", "andy", "config"), "w") as fh:
            fh.write("top = 4\n")
        p = self.run_andy("--show-config")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertRegex(p.stdout, r"(?m)^top\s+= 4")

    def test_a_broken_config_cannot_stop_andy_starting(self):
        path = self.write("theme = nope\ntop = lots\n[unclosed\n")
        p = self.run_andy("--config", path, "--json", "--fresh", "--no-projects")
        self.assertEqual(p.returncode, 0, p.stderr)
        json.loads(p.stdout)
        self.assertIn("andy: config:", p.stderr)

    def test_a_setting_actually_takes_effect(self):
        path = self.write("top = 0\n")
        p = self.run_andy("--config", path, "--fresh", "--no-projects")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertNotIn("largest items", p.stdout)


if __name__ == "__main__":
    unittest.main()
