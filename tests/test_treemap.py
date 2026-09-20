"""The area map. Its whole claim is that area is proportional to size, so that
is what gets checked -- along with staying inside the canvas, because a cell
drawn one column too wide corrupts the row beside it."""

import random
import unittest

from andymod import andy

Node = andy.Node


def scaled(values, dx, dy):
    """squarify's contract: descending, and summing to the canvas area."""
    values = sorted(values, reverse=True)
    total = sum(values)
    return [v / total * (dx * dy) for v in values]


class Squarify(unittest.TestCase):
    def test_one_value_takes_the_whole_canvas(self):
        self.assertEqual(andy.squarify([12.0], 0, 0, 3, 4), [(0, 0, 3, 4)])

    def test_every_value_gets_a_rectangle(self):
        vals = scaled([5, 3, 2, 1], 10, 10)
        self.assertEqual(len(andy.squarify(vals, 0, 0, 10, 10)), 4)

    def test_areas_are_proportional(self):
        vals = scaled([50, 30, 15, 4, 1], 20, 12)
        for value, (_, _, w, h) in zip(vals, andy.squarify(vals, 0, 0, 20, 12)):
            self.assertAlmostEqual(w * h, value, places=6)

    def test_rectangles_stay_inside_the_canvas(self):
        rng = random.Random(11)
        for _ in range(200):
            dx, dy = rng.uniform(1, 40), rng.uniform(1, 40)
            vals = scaled([rng.uniform(0.1, 100) for _ in range(rng.randint(1, 12))], dx, dy)
            for x, y, w, h in andy.squarify(vals, 0.0, 0.0, dx, dy):
                self.assertGreaterEqual(x, -1e-9)
                self.assertGreaterEqual(y, -1e-9)
                self.assertLessEqual(x + w, dx + 1e-9)
                self.assertLessEqual(y + h, dy + 1e-9)

    def test_rectangles_do_not_overlap(self):
        vals = scaled([40, 25, 20, 10, 5], 24, 16)
        rects = andy.squarify(vals, 0.0, 0.0, 24, 16)
        for i, (ax, ay, aw, ah) in enumerate(rects):
            for bx, by, bw, bh in rects[i + 1:]:
                overlap_x = min(ax + aw, bx + bw) - max(ax, bx)
                overlap_y = min(ay + ah, by + bh) - max(ay, by)
                self.assertLessEqual(min(overlap_x, overlap_y), 1e-9)

    def test_a_zero_sized_canvas_does_not_raise(self):
        self.assertEqual(len(andy.squarify([0.0, 0.0], 0, 0, 0, 0)), 2)

    def test_aspect_ratios_are_squarish(self):
        # the point of squarifying rather than slicing
        vals = scaled([30, 25, 20, 15, 10], 20, 20)
        for _, _, w, h in andy.squarify(vals, 0.0, 0.0, 20, 20):
            self.assertLess(max(w / h, h / w), 4.0)


class MapCells(unittest.TestCase):
    @staticmethod
    def nodes(*sizes):
        return [Node(label=f"n{i}", size=s) for i, s in enumerate(sizes)]

    def test_cells_fit_the_given_box(self):
        cells, _ = andy.map_cells(self.nodes(50, 30, 20), 2, 3, 40, 12)
        for _, x, y, w, h in cells:
            self.assertGreaterEqual(x, 2)
            self.assertGreaterEqual(y, 3)
            self.assertLessEqual(x + w, 2 + 40)
            self.assertLessEqual(y + h, 3 + 12)

    def test_every_drawn_cell_is_big_enough_to_label(self):
        cells, skipped = andy.map_cells(self.nodes(1000, 500, 200, 40, 3, 1), 0, 0, 60, 16)
        if len(cells) > 1:
            for _, _, _, w, h in cells:
                self.assertGreaterEqual(w, 5)
                self.assertGreaterEqual(h, 2)
        self.assertEqual(len(cells) + len(skipped), 6)

    def test_the_largest_is_never_the_one_dropped(self):
        cells, skipped = andy.map_cells(self.nodes(10 ** 9, 10, 5, 2, 1), 0, 0, 30, 8)
        self.assertTrue(cells)
        self.assertEqual(cells[0][0].size, 10 ** 9)
        for node in skipped:
            self.assertLess(node.size, 10 ** 9)

    def test_informational_and_empty_nodes_are_not_drawn(self):
        nodes = [Node(label="real", size=100),
                 Node(label="info", size=100, informational=True),
                 Node(label="empty", size=0)]
        cells, skipped = andy.map_cells(nodes, 0, 0, 20, 8)
        drawn = {n.label for n, *_ in cells} | {n.label for n in skipped}
        self.assertEqual(drawn, {"real"})

    def test_a_canvas_with_no_room(self):
        self.assertEqual(andy.map_cells(self.nodes(5, 5), 0, 0, 0, 0), ([], []))

    def test_nothing_to_draw(self):
        self.assertEqual(andy.map_cells([], 0, 0, 20, 10), ([], []))


if __name__ == "__main__":
    unittest.main()
