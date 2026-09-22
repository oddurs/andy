---
id: 34
title: The bar draws a 637M row the same as a 7.5G row
type: bug
status: done
milestone: v1.5
assignee: Oddur Sigurdsson
created: 2026-09-21
updated: 2026-09-21
priority: p0
effort: m
area: tui
---

## What happens

## What should happen

## Reproduction

1.

## 2026-09-21

Every bar is drawn against the largest item at its own level. The README defends it -- "so every tier of the tree stays readable" -- and the cost is that the most prominent element on each row means something different on each row.

Measured on the author disk:

    rsst/target              7.5G  ████████████████████  100% of its level
    traintime/node_modules   637M  ████████████████████  100% of its level

Two full bars, twelve times apart, four lines from each other. The display is
not compressing the truth, it is inverting it: 637M of a 79.9G disk is
negligible and the bar says it is everything. Worse, it hides the actual
finding, which is that no single node_modules matters and the 8.6G group does.

Proposal. One denominator per subtree: a row is drawn against the total of the
top-level category containing it, and a category against everything mapped.
That is one rule -- share of the thing you are inside -- and it makes every row
within a category directly comparable, which is the comparison you are making
when you decide what to remove.

    rsst/target              7.5G  ████                  19.9% of its category
    traintime/node_modules   637M  ▍                      1.7% of its category

What this costs, stated plainly: 229 project artifacts each under 2% will draw
near-empty bars. That is the honest picture and the rows are already sorted by
size, so "which is biggest" was never the bar job. Proportion was, and
proportion is what it will now show. It also matches the area map, where a
rectangle has always been its share of the whole.

Acceptance criteria
- [x] A bar means share of the enclosing category, at every depth
- [x] A category bar means share of everything mapped
- [x] Two rows of the same size draw the same bar wherever they sit
- [x] The README stops promising per-level normalisation and says what it does
- [x] A test pins the denominator, so the rule cannot drift back

## 2026-09-21

Implemented as one denominator carried down the recursion rather than recomputed per level: emit() takes what this row is drawn against and what its children will be drawn against, which is the category for everything inside one. The first attempt appended rows and then rewrote them afterwards to patch in the category size, which worked and read like an apology.

The cost is real and worth stating: 229 project artifacts each under 2% of their category now draw near-empty bars where the largest used to draw full. That is the honest picture, and the rows were already sorted by size, so the bar was never how you found the biggest one. What it can now tell you -- that no single node_modules matters and the 8.6G group does -- is a thing the old scale actively hid.
