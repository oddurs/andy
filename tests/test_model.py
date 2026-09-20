"""Size roll-up: the arithmetic the whole program exists to get right.

The invariant, from the README: when one measured location sits inside another,
the inner one is subtracted from the outer, so no byte is reported twice.
"""

import os
import random
import unittest

from andymod import andy

Node = andy.Node


def model_of(*nodes, category="test"):
    m = andy.Model()
    m.category(category).children.extend(nodes)
    m.recompute()
    return m


def measured(label, path, size):
    return Node(label=label, path=path, measured=size)


class Rollup(unittest.TestCase):
    def test_a_category_sums_its_children(self):
        m = model_of(measured("a", "/x/a", 300), measured("b", "/x/b", 200))
        self.assertEqual(m.categories[0].size, 500)
        self.assertEqual(m.total, 500)

    def test_children_are_sorted_largest_first(self):
        m = model_of(measured("small", "/x/a", 1), measured("big", "/x/b", 9))
        self.assertEqual([c.label for c in m.categories[0].children], ["big", "small"])

    def test_an_unmeasured_parent_takes_its_children(self):
        group = Node(label="node_modules")
        group.children += [measured("one", "/x/1", 10), measured("two", "/x/2", 20)]
        m = model_of(group)
        self.assertEqual(group.size, 30)

    def test_count_ignores_empty_and_informational_nodes(self):
        live = measured("live", "/x/a", 10)
        empty = measured("empty", "/x/b", 0)
        info = Node(label="info", path="/x/c", measured=99, informational=True)
        m = model_of(live, empty, info)
        self.assertEqual(m.count, 1)


class Nesting(unittest.TestCase):
    def test_an_inner_measurement_is_subtracted_from_its_container(self):
        outer = measured("cache", "/x/.cache", 1000)
        inner = measured("uv", "/x/.cache/uv", 400)
        m = model_of(outer, inner)
        self.assertEqual(outer.inner, 400)
        self.assertEqual(outer.size, 600)
        self.assertEqual(m.total, 1000)

    def test_sibling_sorting_between_parent_and_child(self):
        """Regression, cairn 0003.

        Lexicographically `/x/.cache-v2` falls between `/x/.cache` and
        `/x/.cache/uv`, because `-` sorts below `/`. Sorting on raw paths let
        the sibling pop the parent off the containment stack, so the child was
        attributed to nothing and its bytes were counted twice.
        """
        outer = measured("cache", "/x/.cache", 1000)
        inner = measured("uv", "/x/.cache/uv", 400)
        sibling = measured("v2", "/x/.cache-v2", 50)
        self.assertEqual(
            sorted(n.path for n in (outer, inner, sibling)),
            ["/x/.cache", "/x/.cache-v2", "/x/.cache/uv"],
            "the ordering this test exists for has changed",
        )
        m = model_of(outer, inner, sibling)
        self.assertEqual(outer.inner, 400)
        self.assertEqual(outer.size, 600)
        self.assertEqual(m.total, 1050)

    def test_every_character_that_sorts_below_the_separator(self):
        for ch in " !\"#$%&'()*+,-.":
            outer = measured("outer", "/x/c", 1000)
            inner = measured("inner", "/x/c/in", 400)
            sibling = measured("sib", "/x/c" + ch + "z", 50)
            model_of(outer, inner, sibling)
            self.assertEqual(outer.inner, 400, f"broken by sibling /x/c{ch}z")

    def test_three_deep(self):
        a = measured("a", "/x/a", 1000)
        b = measured("b", "/x/a/b", 600)
        c = measured("c", "/x/a/b/c", 200)
        m = model_of(a, b, c)
        self.assertEqual((a.size, b.size, c.size), (400, 400, 200))
        self.assertEqual(m.total, 1000)

    def test_a_partial_prefix_is_not_containment(self):
        # /x/abc is not inside /x/ab even though the string starts with it.
        outer = measured("ab", "/x/ab", 100)
        other = measured("abc", "/x/abc", 50)
        m = model_of(outer, other)
        self.assertEqual(outer.inner, 0)
        self.assertEqual(m.total, 150)

    def test_informational_rows_do_not_contribute(self):
        real = measured("vm disk", "/x/vm", 1000)
        live = Node(label="docker · live", informational=True)
        live.children.append(
            Node(label="images", measured=700, size=700, informational=True))
        m = model_of(real, live)
        self.assertEqual(m.total, 1000, "docker's view of the same bytes was added")
        self.assertEqual(live.size, 700, "the informational row still shows its own figure")

    def test_informational_rows_sort_last(self):
        real = measured("small real", "/x/a", 1)
        live = Node(label="huge informational", measured=10 ** 9, informational=True)
        m = model_of(real, live)
        self.assertEqual([c.label for c in m.categories[0].children][-1],
                         "huge informational")


class Itemised(unittest.TestCase):
    """A location whose children itemise it -- each rustup toolchain, each
    simulator, each browser build. cairn 0017: the children's bytes used to
    fall out of the category entirely."""

    def tree(self, parent_size, *child_sizes):
        parent = measured("rustup toolchains", "/h/.rustup/toolchains", parent_size)
        for i, size in enumerate(child_sizes):
            parent.children.append(
                Node(label=f"toolchain-{i}", path=f"/h/.rustup/toolchains/t{i}",
                     measured=size, detail=True))
        return parent, model_of(parent)

    def test_the_parent_row_shows_everything_underneath_it(self):
        parent, m = self.tree(1000, 600, 300)
        self.assertEqual(parent.inner, 900)
        self.assertEqual(parent.size, 1000, "the itemised children were dropped")
        self.assertEqual(m.total, 1000)

    def test_fully_itemised_is_not_zero(self):
        # every byte accounted for by children; the parent's own remainder is 0
        parent, m = self.tree(1000, 700, 300)
        self.assertEqual(parent.size, 1000)
        self.assertEqual(m.categories[0].size, 1000,
                         "a category lost a location whose children covered it")

    def test_a_remainder_is_kept(self):
        parent, m = self.tree(1000, 600)
        self.assertEqual(parent.size, 1000)
        self.assertEqual([c.size for c in parent.children], [600])

    def test_itemising_does_not_change_the_total(self):
        plain = model_of(measured("x", "/h/x", 1000))
        _, itemised = self.tree(1000, 250, 250, 500)
        self.assertEqual(plain.total, itemised.total)

    def test_a_breakdown_is_not_counted_as_a_location(self):
        parent, m = self.tree(1000, 600, 300)
        self.assertEqual(m.count, 1, "each toolchain was counted as its own location")
        self.assertTrue(m.is_location(parent))
        self.assertFalse(any(m.is_location(c) for c in parent.children))

    def test_children_still_sort_largest_first(self):
        parent, _ = self.tree(1000, 100, 700, 200)
        self.assertEqual([c.size for c in parent.children], [700, 200, 100])


class Invariant(unittest.TestCase):
    """The property directly, over random trees: for every measured node,
    `inner` is the sum of the measurements of the paths nested under it."""

    def test_random_trees(self):
        rng = random.Random(0xA11D)
        names = ["a", "b", "c", "a-1", "a.2", "a b", "c+d", "a-", "b.c"]
        for trial in range(300):
            paths = set()
            for _ in range(rng.randint(2, 12)):
                depth = rng.randint(1, 4)
                paths.add("/" + "/".join(rng.choice(names) for _ in range(depth)))
            nodes = [measured(p, p, rng.randint(1, 1000)) for p in sorted(paths)]
            model_of(*nodes)
            by_path = {n.path: n for n in nodes}
            for node in nodes:
                expected = sum(
                    other.measured for other in nodes
                    if other is not node
                    and other.path.startswith(node.path + os.sep)
                    and self._nearest(other.path, by_path) == node.path
                )
                self.assertEqual(node.inner, expected,
                                 f"trial {trial}: {node.path} in {sorted(paths)}")

    @staticmethod
    def _nearest(path, by_path):
        parent = os.path.dirname(path)
        while parent and parent != "/":
            if parent in by_path:
                return parent
            parent = os.path.dirname(parent)
        return None

    def test_total_never_exceeds_the_outermost_measurements(self):
        rng = random.Random(7)
        for _ in range(200):
            kids = [measured(f"k{i}", f"/r/k{i}", rng.randint(1, 200))
                    for i in range(rng.randint(0, 6))]
            # a real parent is at least as big as what it contains
            root_size = sum(k.measured for k in kids) + rng.randint(0, 500)
            root = measured("root", "/r", root_size)
            m = model_of(root, *kids)
            self.assertEqual(m.total, root_size,
                             "children of a measured root must not add to it")


class Category(unittest.TestCase):
    def test_lookup_is_stable(self):
        m = andy.Model()
        self.assertIs(m.category("x"), m.category("x"))

    def test_walk_yields_every_node(self):
        parent = Node(label="p")
        parent.children.append(Node(label="c"))
        m = model_of(parent)
        self.assertEqual({n.label for n in m.walk()}, {"test", "p", "c"})


if __name__ == "__main__":
    unittest.main()
