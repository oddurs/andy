---
id: 4
title: A test suite, and a file that can be imported to run it
type: chore
status: done
milestone: v1.1
assignee: Oddur Sigurdsson
created: 2026-09-20
updated: 2026-09-20
priority: p0
effort: m
area: tests
---

## Problem

There are no tests. andy is 2,300 lines of arithmetic about other people's
disks: size roll-up, nested subtraction, treemap geometry, `find` output
classification, size parsing, the cache round-trip. Every one of those is a pure
function with an obvious right answer, and none of them is checked. The double
counting bug (0003) sat there unnoticed for exactly that reason.

Testing it is also awkward on purpose. The program is a single executable named
`andy`, with no `.py` extension, so `import andy` does not work and every test
has to hand-roll a `SourceFileLoader` — and get it right, because the obvious
version fails with a confusing `dataclasses` error unless the module is put in
`sys.modules` before it is executed.

## Proposal

Keep the one-file, zero-dependency install exactly as it is. It is the best
thing about the program and no test layout is worth trading for it.

Add `tests/` with a `conftest.py` that does the `SourceFileLoader` dance once
and exposes the module as a fixture. Plain `pytest`, no plugins, no packaging,
nothing the installed tool depends on.

Cover the parts where being wrong is silent:

- `human`, `parse_size`, `shorten`, `clip_end`, `bar` — boundaries, zero,
  negatives, widths narrower than the text
- `Model.recompute` — nesting, informational rows excluded from totals,
  sort order, the invariant in 0003
- `squarify` / `map_cells` — every rectangle inside the canvas, areas
  proportional to values, no overlap, degenerate sizes
- `find_artifacts` classification — strict names always count, ambiguous names
  only beside a build marker, symlinks skipped
- `parse_docker_size`, `_parse_du` — the formats they actually receive
- `dedupe_dirs` — nested roots dropped, `~/Code` and `~/code` seen as one
- cache round-trip through `save_cache` / `load_cache`, and a corrupt cache file
  producing an empty dict rather than a traceback

Plus one integration test that builds a fake tree in `tmp_path` with known
sizes, runs a scan against it, and checks the JSON output adds up.

## Acceptance criteria

- [x] `tests/andymod.py` imports the extensionless `andy` as a module
- [x] Unit tests for every pure helper listed above
- [x] An end-to-end test over a synthetic tree with known byte totals
- [x] `python3 -m unittest discover -s tests` passes from a clean checkout with
      no dependencies at all
- [x] Installing andy still means copying one file

## 2026-09-20

Written against stdlib unittest, not pytest as originally proposed.

pytest is not installed on the author's machine, which made the question
concrete: a contributor cloning andy would have to install a dependency before
they could check that a zero-dependency program still works. That is the wrong
shape for this project. unittest costs a little expressiveness -- no
parametrise, no fixtures -- and buys 'git clone && python3 -m unittest discover
-s tests' on any Python since 3.9, and a CI job with no install step.

Where parametrisation was genuinely wanted (the property tests in
test_model.py, the width sweeps in test_format.py) a seeded random.Random and a
for loop did the job, and the seed makes failures reproducible in a way a
generative framework would not by default.
